# Doorman Game — client

React 19 + Vite. The browser talks only to the Python backend in `../backend`:
no model credentials are read here, and no score is calculated here.

```bash
npm install
npm run dev        # http://localhost:7322
npm test           # vitest
npm run lint       # eslint
npm run build      # production bundle into dist/
```

`vite.config.js` proxies `/api` and `/healthz` to `http://127.0.0.1:7321`, so
development is same-origin and CORS never applies. For a built bundle pointed
at a deployed backend, set `VITE_API_BASE` at build time.

Where things live:

| Path | What it holds |
|---|---|
| `src/hooks/useGame.js` | the whole client-side game state, all of it server-supplied |
| `src/api/client.js` | one thin wrapper per endpoint |
| `src/components/Stage/` | the street scene — skyline, door, two characters |
| `src/components/Transcript/` | the scrolling record of the conversation |
| `src/components/EndScreen/` | the three endings and the post-game debrief |

Full instructions, including the backend, are in the [root README](../README.md).
