import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
});

// jsdom has no Web Audio implementation. The end screen only uses it for a
// sting, so a no-op keeps the tests focused on what is rendered.
window.AudioContext = class {
  createOscillator() {
    return {
      type: '',
      frequency: { setValueAtTime() {} },
      connect: () => ({ connect() {} }),
      start() {},
      stop() {},
    };
  }
  createGain() {
    return {
      gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} },
      connect: () => ({ connect() {} }),
    };
  }
  close() {
    return Promise.resolve();
  }
  get currentTime() {
    return 0;
  }
};

window.HTMLElement.prototype.scrollIntoView = () => {};
