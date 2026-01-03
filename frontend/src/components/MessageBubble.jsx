import './MessageBubble.css';

/** One line in the transcript, attributed to the player or to Marcus. */
export function MessageBubble({ message }) {
  const isPlayer = message.role === 'user';

  return (
    <article className={`message-bubble ${isPlayer ? 'player' : 'doorman'}`}>
      <header className="message-sender">{isPlayer ? 'YOU' : 'MARCUS'}</header>
      <p className="message-text">{message.content}</p>
    </article>
  );
}
