Netlify Blobs — Visit Counter
=============================

This site ships a Netlify Function that uses Netlify Blobs for a simple visit counter: `/.netlify/functions/counter-home`. The widget is enabled on both main and dev. Dev uses a namespace so it does not mix with production totals.

Quick checks
- Verify function builds: open `/.netlify/functions/counter-home?mode=env&diag=1` on your deploy. You should see runtime flags and whether an edge token/header are present.
- Toggle diagnostics: add `?diag=1` to the homepage to log counter responses in the console.

When Blobs isn’t auto‑bound
- If `blobs_context` is false in `mode=env`, the runtime didn’t auto‑bind Blobs for this deploy/context.
- The function supports three ways to connect automatically:
  - Edge access: when the runtime provides `event.blobs` (url + token) and the `x-nf-site-id` header.
  - API access: when `NETLIFY_SITE_ID` and `NETLIFY_BLOBS_TOKEN` are set.
  - Auto-binding: when Netlify injects `NETLIFY_BLOBS_CONTEXT`.

Where to set variables
- Netlify UI → Site settings → Build & deploy → Environment → Add environment variable.
- You can scope vars to specific branches. If you ever need an API token, add `NETLIFY_BLOBS_TOKEN` only for branch `dev` (main normally won’t need it).

Branch contexts and the widget
- `netlify.toml` includes a `dev` context that builds with `_config_dev.yml`. The widget is on for both main and dev.
- On dev only, `index.md` sets `window.BHN_COUNTER_NS = 'dev'`, so keys become `dev:home` and `dev:home:YYYY-MM`.
- On main, no namespace is set; keys are `home` and `home:YYYY-MM`.

Key format and reset
- Keys: total → `home` (or `dev:home`), monthly → `home:YYYY-MM` (or `dev:home:YYYY-MM`).
- Reset main: `/.netlify/functions/counter-home?mode=purge&diag=1&key=home`
- Reset dev: `/.netlify/functions/counter-home?mode=purge&diag=1&ns=dev` (or `&key=dev:home`)
- Reset a single month: `/.netlify/functions/counter-home?mode=purge&diag=1&key=home:YYYY-MM` (or `dev:home:YYYY-MM`)

Diagnostics endpoints
- Env snapshot: `/.netlify/functions/counter-home?mode=env&diag=1`
- Get counts: `/.netlify/functions/counter-home?mode=get` (add `&diag=1` for verbose)
- List keys (diag only): `/.netlify/functions/counter-home?mode=list&diag=1` (optional `&ns=dev` or `&key=home`)
- Purge keys (diag only; requires prefix): `/.netlify/functions/counter-home?mode=purge&diag=1&ns=dev` or `&key=home`

Notes
- Functions are bundled with `esbuild` so `@netlify/blobs` is included in the artifact; no extra install step is needed at runtime.
- The counter groups monthly tallies by the site time zone (`COUNTER_TZ`, default `America/New_York`).
