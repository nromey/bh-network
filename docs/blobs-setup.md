Netlify Blobs — Visit Counter
=============================

This site ships a Netlify Function that uses Netlify Blobs for a simple visit counter: `/.netlify/functions/counter-home`. The widget is enabled on both main and dev. Dev uses a namespace so it does not mix with production totals.

Quick checks
- Verify function builds: open `/.netlify/functions/counter-home?mode=env&diag=1` on your deploy. You should see `netlify: true` and whether `blobs_context` is available.
- Toggle diagnostics: add `?diag=1` to the homepage to log counter responses in the console.

When Blobs isn’t auto‑bound
- If `blobs_context` is false in `mode=env`, the runtime didn’t auto‑bind Blobs for this deploy/context.
- You can still use Blobs by providing manual credentials via environment variables:
  - `NETLIFY_BLOBS_TOKEN` (preferred name) or `BLOBS_TOKEN`
  - `NETLIFY_SITE_ID` (provided by Netlify) or `BLOBS_SITE_ID`
- The function auto‑detects these (see `netlify/functions/counter-home.js`). If both `siteID` and `token` are present, it uses them; otherwise it relies on auto‑binding.

Where to set variables
- Netlify UI → Site settings → Build & deploy → Environment → Add environment variable.
- You can scope vars to specific branches. For example, add `NETLIFY_BLOBS_TOKEN` for branch `devb` if production already has Blobs auto‑binding.

Branch contexts and the widget
- `netlify.toml` includes a `dev` context that builds with `_config_dev.yml`. The widget is on for both main and dev.
- On dev only, `index.md` sets `window.BHN_COUNTER_NS = 'dev'`, so keys become `dev:home` and `dev:home:YYYY-MM`.
- On main, no namespace is set; keys are `home` and `home:YYYY-MM`.

Key format and reset
- Keys: total → `home` (or `dev:home`), monthly → `home:YYYY-MM` (or `dev:home:YYYY-MM`).
- Reset main: `/.netlify/functions/counter-home?mode=purge&diag=1&key=home`
- Reset dev: `/.netlify/functions/counter-home?mode=purge&diag=1&ns=dev`

Diagnostics endpoints
- Env snapshot: `/.netlify/functions/counter-home?mode=env&diag=1`
- Get counts: `/.netlify/functions/counter-home?mode=get` (add `&diag=1` for verbose)
- List keys (diag only): `/.netlify/functions/counter-home?mode=list&diag=1` (optional `&ns=dev`)
- Purge keys (diag only; requires prefix): `/.netlify/functions/counter-home?mode=purge&diag=1&ns=dev`

Notes
- Functions are bundled with `esbuild` so `@netlify/blobs` is included in the artifact; no extra install step is needed at runtime.
- Runtime binding varies by context. The function supports these options automatically:
  - Edge access: when the runtime provides `event.blobs` (url + token) and the `x-nf-site-id` header.
  - API access: when `NETLIFY_SITE_ID` and `NETLIFY_BLOBS_TOKEN` are set.
  - Auto-binding: when Netlify injects `NETLIFY_BLOBS_CONTEXT`.
- The counter groups monthly tallies by the site time zone (`COUNTER_TZ`, default `America/New_York`).
