import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createSession,
  deleteSession,
  fetchDebrief,
  fetchHealth,
  fetchSession,
  playTurn,
} from '../api/client';
import { SESSION_STORAGE_KEY, STATUS, isTerminal } from '../config';

const EMPTY_GAME = {
  sessionId: null,
  score: 0,
  threshold: 100,
  status: STATUS.IN_PROGRESS,
  turnsUsed: 0,
  turnsRemaining: 0,
  maxTurns: 0,
};

const gameFromSession = (session) => ({
  sessionId: session.session_id,
  score: session.cumulative_score,
  threshold: session.threshold,
  status: session.status,
  turnsUsed: session.turns_used,
  turnsRemaining: session.turns_remaining,
  maxTurns: session.max_turns,
});

const readStoredSessionId = () => {
  try {
    return window.localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
};

const storeSessionId = (sessionId) => {
  try {
    if (sessionId) window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    else window.localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    /* private browsing — the run simply will not survive a reload */
  }
};

/**
 * Owns one run of the game.
 *
 * Every number here arrives from the server. The hook never computes a score,
 * never decides an outcome, and never tells the backend what it thinks the
 * state is — it sends a sentence and renders the reply.
 */
export function useGame() {
  const [game, setGame] = useState(EMPTY_GAME);
  const [transcript, setTranscript] = useState([]);
  const [isBooting, setIsBooting] = useState(true);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState(null);
  const [lastTurn, setLastTurn] = useState(null);
  const [debrief, setDebrief] = useState(null);
  const [provider, setProvider] = useState(null);
  const [audio, setAudio] = useState(null);
  const inFlight = useRef(false);

  const adopt = useCallback((session) => {
    setGame(gameFromSession(session));
    setTranscript(
      (session.transcript ?? []).map((message, index) => ({ id: index, ...message })),
    );
    storeSessionId(session.session_id);
  }, []);

  const startFresh = useCallback(async () => {
    adopt(await createSession());
    setTranscript([]);
    setLastTurn(null);
    setDebrief(null);
    setError(null);
  }, [adopt]);

  useEffect(() => {
    let cancelled = false;

    const boot = async () => {
      try {
        const health = await fetchHealth();
        if (!cancelled) setProvider(health);

        const storedId = readStoredSessionId();
        if (storedId) {
          try {
            const session = await fetchSession(storedId);
            if (!cancelled) adopt(session);
            return;
          } catch {
            /* the stored run is gone — fall through and start a new one */
          }
        }
        const session = await createSession();
        if (!cancelled) adopt(session);
      } catch (caught) {
        if (!cancelled) setError(caught.message);
      } finally {
        if (!cancelled) setIsBooting(false);
      }
    };

    boot();
    return () => {
      cancelled = true;
    };
  }, [adopt]);

  const say = useCallback(
    async (text) => {
      const message = text.trim();
      if (!message || !game.sessionId || inFlight.current || isTerminal(game.status)) return;

      inFlight.current = true;
      setIsThinking(true);
      setError(null);
      setLastTurn(null);
      setTranscript((previous) => [
        ...previous,
        { id: `local-${previous.length}`, role: 'user', content: message },
      ]);

      try {
        const result = await playTurn(game.sessionId, message);
        setTranscript((previous) => [
          ...previous,
          { id: `reply-${previous.length}`, role: 'assistant', content: result.reply },
        ]);
        setGame((previous) => ({
          ...previous,
          score: result.cumulative_score,
          threshold: result.threshold,
          status: result.status,
          turnsUsed: result.turns_used,
          turnsRemaining: result.turns_remaining,
          maxTurns: result.max_turns,
        }));
        setLastTurn({ delta: result.score_delta, injectionBlocked: result.injection_blocked });
        if (result.audio_base64) setAudio(result.audio_base64);
      } catch (caught) {
        setError(caught.message);
        // The turn was refused, so drop the optimistic line rather than
        // leaving a message on screen the server never scored.
        setTranscript((previous) => previous.slice(0, -1));
      } finally {
        inFlight.current = false;
        setIsThinking(false);
      }
    },
    [game.sessionId, game.status],
  );

  useEffect(() => {
    if (!isTerminal(game.status) || !game.sessionId || debrief) return;
    let cancelled = false;
    fetchDebrief(game.sessionId)
      .then((result) => {
        if (!cancelled) setDebrief(result);
      })
      .catch(() => {
        /* the debrief is a bonus, not a requirement */
      });
    return () => {
      cancelled = true;
    };
  }, [game.status, game.sessionId, debrief]);

  const playAgain = useCallback(async () => {
    const previousId = game.sessionId;
    setIsThinking(true);
    try {
      if (previousId) await deleteSession(previousId).catch(() => {});
      await startFresh();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setIsThinking(false);
    }
  }, [game.sessionId, startFresh]);

  return {
    game,
    transcript,
    provider,
    debrief,
    lastTurn,
    audio,
    error,
    isBooting,
    isThinking,
    say,
    playAgain,
    clearLastTurn: useCallback(() => setLastTurn(null), []),
    clearAudio: useCallback(() => setAudio(null), []),
    dismissError: useCallback(() => setError(null), []),
  };
}
