import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, createSession, fetchDebrief, playTurn } from './client';

const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('api client', () => {
  it('asks the server to issue a session id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ session_id: 'abc' }, 201));
    vi.stubGlobal('fetch', fetchMock);

    await expect(createSession()).resolves.toEqual({ session_id: 'abc' });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/sessions');
    expect(options.method).toBe('POST');
    expect(options.body).toBeUndefined();
  });

  it('sends only the message when playing a turn', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ reply: 'hm' }));
    vi.stubGlobal('fetch', fetchMock);

    await playTurn('abc', 'evening mate');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ message: 'evening mate' });
  });

  it('never sends a score, a status or a session id in the body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ reply: 'hm' }));
    vi.stubGlobal('fetch', fetchMock);

    await playTurn('abc', 'evening mate');
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(Object.keys(body)).toEqual(['message']);
  });

  it('surfaces the server detail on an error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'this run already ended' }, 409)),
    );

    await expect(playTurn('abc', 'hi')).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      message: 'this run already ended',
    });
  });

  it('falls back to a status message when there is no detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(null, 500)));
    await expect(fetchDebrief('abc')).rejects.toThrow('Request failed (500)');
  });

  it('explains a dead backend rather than throwing a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed to fetch')));

    const error = await createSession().catch((caught) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toMatch(/backend running/i);
  });
});
