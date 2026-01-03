import { useEffect, useRef } from 'react';

/** Converts a base64 payload into a Blob without an intermediate data: URL. */
function base64ToBlob(base64, mimeType) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mimeType });
}

/**
 * Plays Marcus's spoken reply when the hosted provider returns one.
 *
 * The offline provider has no voice, so this stays silent in the default
 * configuration.
 */
export function AudioPlayer({ audioBase64, onFinished }) {
  const audioRef = useRef(null);

  useEffect(() => {
    if (!audioBase64 || !audioRef.current) return undefined;

    const url = URL.createObjectURL(base64ToBlob(audioBase64, 'audio/mpeg'));
    const element = audioRef.current;
    element.src = url;
    element.play().catch(() => {
      // Browsers block autoplay until the page has been interacted with.
      onFinished?.();
    });

    return () => URL.revokeObjectURL(url);
  }, [audioBase64, onFinished]);

  return <audio ref={audioRef} onEnded={onFinished} hidden />;
}
