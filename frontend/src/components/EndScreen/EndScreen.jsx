import { useEffect } from 'react';
import { outcomeFor } from './outcomes';
import { playFanfare } from './fanfare';
import './EndScreen.css';

const sign = (value) => (value > 0 ? `+${value}` : `${value}`);

/**
 * The post-game screen, including the debrief.
 *
 * While a run is live the judge's reasoning is withheld by the server, because
 * it quotes Marcus's secret profile. It is released here, all at once, which
 * is what turns a loss into something you can learn from.
 */
export function EndScreen({ status, score, threshold, debrief, onPlayAgain }) {
  const outcome = outcomeFor(status);

  useEffect(() => {
    if (!outcome) return undefined;
    const stop = playFanfare(outcome.tone);
    return stop;
  }, [outcome]);

  if (!outcome) return null;

  return (
    <div className={`end-overlay ${outcome.tone}`} role="dialog" aria-label={outcome.title}>
      <div className="end-card">
        <p className="end-subtitle">{outcome.subtitle}</p>
        <h1 className="end-title">{outcome.title}</h1>
        <p className="end-blurb">{outcome.blurb}</p>

        <p className="end-score">
          <strong>{score}</strong> <span>/ {threshold} influence</span>
        </p>

        {debrief && (
          <section className="end-debrief">
            <h2 className="end-debrief-title">What Marcus was actually scoring</h2>
            <ol className="end-debrief-list">
              {debrief.turns.map((turn) => (
                <li
                  key={turn.index}
                  className={`end-debrief-row ${turn.score_delta >= 0 ? 'up' : 'down'}`}
                >
                  <span className="end-debrief-delta">{sign(turn.score_delta)}</span>
                  <span className="end-debrief-copy">
                    <span className="end-debrief-said">&ldquo;{turn.player_message}&rdquo;</span>
                    <span className="end-debrief-why">{turn.reasoning}</span>
                  </span>
                </li>
              ))}
            </ol>
          </section>
        )}

        <button className="end-button" onClick={onPlayAgain} type="button">
          {outcome.cta}
        </button>
      </div>
    </div>
  );
}
