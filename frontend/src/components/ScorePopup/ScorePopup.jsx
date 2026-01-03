import { useEffect, useState } from 'react';
import './ScorePopup.css';

const VISIBLE_MS = 1800;

/** The influence a turn cost or earned, thrown up over the stage. */
export function ScorePopup({ score, injectionBlocked, onComplete }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, VISIBLE_MS);
    return () => clearTimeout(timer);
  }, [score, onComplete]);

  if (!visible) return null;

  return (
    <div className="score-popup-overlay">
      <div className={`score-popup ${score >= 0 ? 'positive' : 'negative'}`}>
        {score >= 0 ? '+' : ''}
        {score}
      </div>
      {injectionBlocked && (
        <p className="score-popup-note">
          That was an instruction, not a conversation. Marcus does not take instructions.
        </p>
      )}
    </div>
  );
}
