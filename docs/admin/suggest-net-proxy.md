# Suggest-a-Net Proxy Setup

This site now forwards `/api/public/suggest` requests to `/.netlify/functions/suggest-net`, which relays submissions to the Nets Helper running on the data host. To keep the helper locked down while still accepting public suggestions, give the Netlify Function its own HTTP Basic Auth credentials.

## 1. Create a helper account on the data host

1. Pick a username that clearly indicates automation (for example `suggest-bot`).
2. Add it to the same `.htpasswd` file that already protects `/nets-helper/`:

   ```bash
   sudo htpasswd /etc/apache2/.htpasswd_bhn_nets suggest-bot
   ```

3. Verify Apache/Nginx is still requiring auth by hitting the helper URL in a browser or with:

   ```bash
   curl -I https://data.blindhams.network/nets-helper/
   ```

   You should still receive a `401 Unauthorized` challenge when no credentials are supplied.

## 2. Configure Netlify environment variables

In Netlify → **Site settings → Build & deploy → Environment**, add:

| Variable | Purpose |
| --- | --- |
| `BHN_SUGGEST_AUTH_USER` | Username created above (`suggest-bot`). |
| `BHN_SUGGEST_AUTH_PASS` | Matching password. |
| `BHN_SUGGEST_TARGET` *(optional)* | Override the default upstream `https://data.blindhams.network/nets-helper/api/public/suggest` if needed (staging, etc.). |
| `BHN_SUGGEST_AUTH_HEADER` *(optional)* | Precomputed `Basic …` header if you would rather not store the raw password—takes precedence over the user/pass pair. |

Save the variables; Netlify will queue a fresh deploy so the `suggest-net` function can read them. (If you added the variables before pushing code, trigger **Deploy site** manually.)

## 3. Test the proxy

1. Wait for the new build to finish.
2. Confirm the function can see the helper by calling it directly:

   ```bash
   curl -i -X POST \
     -H 'Content-Type: application/json' \
     -d '{"name":"Smoke Test","description":"Proxy check","category":"bhn","start_local":"10:00","duration_min":"60","rrule":"FREQ=WEEKLY;BYDAY=MO","contact_email":"test@example.com"}' \
     https://www.blindhams.network/api/public/suggest
   ```

   - A `202` response means the submission hit the helper and created a pending draft.
   - A `400` response with validation errors means the proxy worked but the payload needs adjustment.
   - A `401`/`403` means the credentials are missing or incorrect—double-check the Netlify variables and the `.htpasswd` entry.

3. Finally, retest the form at `/nets/suggest/` in the browser to ensure end-to-end behavior (success toast or detailed error).

### Notes

- The Netlify Function automatically forwards the client IP via `X-Forwarded-For`, so the helper’s rate limiting still works.
- If you rotate the password, update both the `.htpasswd` entry and the Netlify environment variable, then redeploy.
