import './InfluenceMeter.css';

/**
 * How close Marcus is to opening the door, and how much road is left.
 *
 * Both numbers come from the server. The bar also renders the negative side
 * of the scale, because reaching the floor now ends the run.
 */
export function InfluenceMeter({ score, threshold, turnsRemaining, maxTurns, status }) {
  const percentage = Math.max(0, Math.min(100, (score / threshold) * 100));
  const isNegative = score < 0;
  const tone = status === 'access_granted' ? 'granted' : isNegative ? 'negative' : 'positive';

  return (
    <div className="influence-meter">
      <div className="meter-labels">
        <h2 className="meter-title">INFLUENCE</h2>
        <span className="meter-value">
          {score} / {threshold}
        </span>
        {maxTurns > 0 && (
          <span className={`meter-turns ${turnsRemaining <= 3 ? 'urgent' : ''}`}>
            {turnsRemaining} {turnsRemaining === 1 ? 'TURN' : 'TURNS'} LEFT
          </span>
        )}
      </div>
      <div
        className="meter-track"
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={threshold}
      >
        <div className={`meter-fill ${tone}`} style={{ width: `${percentage}%` }} />
        {isNegative && <div className="meter-danger" />}
      </div>
    </div>
  );
}
