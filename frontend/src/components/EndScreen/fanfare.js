/**
 * A short synthesised sting for the end of a run.
 *
 * Synthesised rather than bundled: the previous build shipped a 292 KB MP3 of
 * a commercial song, which is both dead weight in the bundle and not ours to
 * redistribute.
 */
const CHORDS = {
  granted: [523.25, 659.25, 783.99, 1046.5],
  refused: [392.0, 349.23, 293.66],
  ejected: [220.0, 207.65],
};

export function playFanfare(tone) {
  const notes = CHORDS[tone];
  const AudioCtor = window.AudioContext ?? window.webkitAudioContext;
  if (!notes || !AudioCtor) return () => {};

  let context;
  try {
    context = new AudioCtor();
  } catch {
    return () => {};
  }

  const start = context.currentTime + 0.05;
  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const at = start + index * 0.16;

    oscillator.type = tone === 'granted' ? 'triangle' : 'sine';
    oscillator.frequency.setValueAtTime(frequency, at);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.16, at + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.75);

    oscillator.connect(gain).connect(context.destination);
    oscillator.start(at);
    oscillator.stop(at + 0.8);
  });

  return () => context.close().catch(() => {});
}
