/**
 * Where the backend lives.
 *
 * In development this is empty: Vite proxies `/api` and `/healthz` to the
 * Python server (see vite.config.js), so the browser makes same-origin
 * requests and CORS never enters the picture. For a built bundle, set
 * VITE_API_BASE at build time.
 *
 * No model credentials are read here, or anywhere else in the frontend. The
 * browser talks to this backend and nothing else.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

/** localStorage key holding the id of the run in progress. */
export const SESSION_STORAGE_KEY = 'doorman.session.id';

/** Outcomes the server can report. Mirrors app/game/rules.py GameStatus. */
export const STATUS = {
  IN_PROGRESS: 'in_progress',
  ACCESS_GRANTED: 'access_granted',
  TURNS_EXHAUSTED: 'turns_exhausted',
  EJECTED: 'ejected',
};

export const isTerminal = (status) => Boolean(status) && status !== STATUS.IN_PROGRESS;
