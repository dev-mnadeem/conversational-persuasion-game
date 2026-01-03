import { useEffect, useRef } from 'react';
import { MessageBubble } from '../MessageBubble';
import './Transcript.css';

/**
 * The running record of the conversation.
 *
 * The stage only ever shows the latest line from each side, which makes a
 * twelve-turn negotiation impossible to follow. This rail keeps the whole
 * exchange visible and scrolls itself to the newest message.
 */
export function Transcript({ messages, isThinking, turnsUsed, maxTurns }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, isThinking]);

  return (
    <aside className="transcript" aria-label="Conversation transcript">
      <header className="transcript-header">
        <h2 className="transcript-title">THE DOOR</h2>
        {maxTurns > 0 && (
          <span className="transcript-turns">
            TURN {Math.min(turnsUsed + (isThinking ? 1 : 0), maxTurns)} / {maxTurns}
          </span>
        )}
      </header>

      <div className="transcript-body">
        {messages.length === 0 && !isThinking ? (
          <div className="transcript-empty">
            <p className="transcript-empty-title">Marcus has not looked up yet.</p>
            <p className="transcript-empty-hint">
              He has run this door for eight years. Money, names and impatience have all been
              tried. Say something he has not heard tonight.
            </p>
          </div>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}

        {isThinking && (
          <div className="transcript-thinking" role="status">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
            <span className="transcript-thinking-label">Marcus is sizing you up</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </aside>
  );
}
