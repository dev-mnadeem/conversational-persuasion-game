import { AudioPlayer } from './components/AudioPlayer';
import { ChatInput } from './components/ChatInput';
import { EndScreen } from './components/EndScreen';
import { InfluenceMeter } from './components/InfluenceMeter';
import { ScorePopup } from './components/ScorePopup';
import { Stage } from './components/Stage';
import { Transcript } from './components/Transcript';
import { useGame } from './hooks/useGame';
import { STATUS, isTerminal } from './config';
import './App.css';

const lastFrom = (messages, role) =>
  [...messages].reverse().find((message) => message.role === role)?.content ?? '';

function App() {
  const {
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
    clearLastTurn,
    clearAudio,
    dismissError,
  } = useGame();

  const over = isTerminal(game.status);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">THE DOORMAN GAME</h1>
          <p className="app-subtitle">BLVD DUBAI &middot; FRIDAY, 23:40</p>
        </div>

        <div className="header-center">
          <InfluenceMeter
            score={game.score}
            threshold={game.threshold}
            turnsRemaining={game.turnsRemaining}
            maxTurns={game.maxTurns}
            status={game.status}
          />
        </div>

        <div className="header-right">
          {provider && (
            <span
              className={`provider-chip ${provider.offline ? 'offline' : 'hosted'}`}
              title={
                provider.offline
                  ? 'Deterministic local doorman — no API key in use'
                  : `Hosted model provider: ${provider.provider}`
              }
            >
              {provider.offline ? 'LOCAL' : provider.provider.toUpperCase()}
            </span>
          )}
          <button className="icon-btn" onClick={playAgain} title="Start over" type="button">
            &#8635;
          </button>
        </div>
      </header>

      <main className="app-main">
        <Stage
          playerMessage={lastFrom(transcript, 'user')}
          doormanMessage={lastFrom(transcript, 'assistant')}
          isLoading={isThinking}
          isOpen={game.status === STATUS.ACCESS_GRANTED}
        />
        <Transcript
          messages={transcript}
          isThinking={isThinking}
          turnsUsed={game.turnsUsed}
          maxTurns={game.maxTurns}
        />
      </main>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button className="error-dismiss" onClick={dismissError} type="button">
            &times;
          </button>
        </div>
      )}

      <footer className="app-footer">
        <ChatInput
          onSend={say}
          isLoading={isThinking}
          disabled={over || isBooting || !game.sessionId}
          status={game.status}
        />
      </footer>

      {lastTurn && (
        <ScorePopup
          score={lastTurn.delta}
          injectionBlocked={lastTurn.injectionBlocked}
          onComplete={clearLastTurn}
        />
      )}

      <AudioPlayer audioBase64={audio} onFinished={clearAudio} />

      {over && (
        <EndScreen
          status={game.status}
          score={game.score}
          threshold={game.threshold}
          debrief={debrief}
          onPlayAgain={playAgain}
        />
      )}
    </div>
  );
}

export default App;
