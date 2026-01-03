import { API_BASE } from '../config';

/** An HTTP error that kept the server's message. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError('Cannot reach the door. Is the backend running?', 0);
  }

  if (response.status === 204) return null;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new ApiError(
      typeof detail === 'string' ? detail : `Request failed (${response.status})`,
      response.status,
    );
  }
  return body;
}

/** Ask the server for a new run. The id is issued server side. */
export const createSession = () => request('/api/sessions', { method: 'POST' });

/** Reload a run, including its transcript. */
export const fetchSession = (sessionId) => request(`/api/sessions/${sessionId}`);

/** Abandon a run. */
export const deleteSession = (sessionId) =>
  request(`/api/sessions/${sessionId}`, { method: 'DELETE' });

/** Say one line to Marcus. The score comes back from the server. */
export const playTurn = (sessionId, message) =>
  request(`/api/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });

/** The hidden judge's per-turn reasoning. Only available once a run has ended. */
export const fetchDebrief = (sessionId) => request(`/api/sessions/${sessionId}/debrief`);

/** Which provider is answering, and is it the offline one. */
export const fetchHealth = () => request('/healthz');
