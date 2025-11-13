# Blind Hams Net Helper

Web helper for trusted schedulers to draft `_data/nets.json` updates from a browser. The app intentionally **never overwrites** the live file; instead it writes a timestamped draft copy so a maintainer can inspect, rename, and commit.

## Overview

- **Frontend:** Accessible form with live JSON preview, edit mode, autosave drafts, and a draft-review dashboard.
- **Automatic IDs:** Net IDs are generated from the name (slugged + dedupe) so editors no longer have to hand-type identifiers.
- **Backend:** Flask app that validates inputs, prevents ID collisions, writes timestamped drafts in `_data/pending/`, and can promote approved bundles into `_data/nets.json`.
- **Metadata:** Every draft save records the authenticated username, timestamp, and optional submission note so reviewers know who staged the change.
- **Security:** Keep HTTP Basic Auth in front, and have the web server forward the authenticated username so role-based permissions (review vs. promote) can be enforced.
- **Notifications:** Optional [ntfy.sh](https://docs.ntfy.sh/) integration announces when batches are submitted or published.

## Local Development

```bash
cd tools/nets-helper
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export BHN_NETS_FILE="$(git rev-parse --show-toplevel)/_data/nets.json"
export BHN_NETS_OUTPUT_DIR="$(git rev-parse --show-toplevel)/_data"
flask --app app run --debug

# Note: if you override these paths manually, use absolute paths or `$HOME`.
# Using a literal `"~/..."` will not expand the tilde.
```

## Testing

Automated tests cover validation, draft writes, and the publish flow using Flask's built‑in test client. Install the dev dependencies and run `pytest` from the helper directory:

```bash
cd tools/nets-helper
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Each test run sets up temporary copies of `_data/nets.json`, `_data/pending/`, and `roles.yml`, so the live files in the repo are never touched.

Load http://127.0.0.1:5000/ to try the form. Draft files will be created under `_data/pending/` with names like `nets.pending.20250317_153000.json`.

### Roles & Permissions

- Roles are defined in `tools/nets-helper/roles.yml`. The sample file maps `publishers` (can publish drafts) and `reviewers` (can stage/edit but not publish).
- The helper looks for the authenticated username in `X-Forwarded-User` or `REMOTE_USER`. Make sure your proxy forwards whichever header your web server populates.
- Locally, you can set `export BHN_NETS_DEFAULT_USER=web-admin` to emulate a publisher account without Basic Auth.

## Deployment (Andre’s host)

1. **Python environment**
   ```bash
   cd /opt/bhn/repo/tools/nets-helper
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt gunicorn
   ```

2. **Systemd service** (save as `/etc/systemd/system/bhn-nets-helper.service`):
   ```ini
   [Unit]
   Description=Blind Hams Nets Helper
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/opt/bhn/repo/tools/nets-helper
   # Adjust these if your data checkout lives elsewhere (e.g., /home/ner/bhn/_data)
   Environment="BHN_NETS_FILE=/opt/bhn/repo/_data/nets.json"
   Environment="BHN_NETS_OUTPUT_DIR=/opt/bhn/repo/_data"
   ExecStart=/opt/bhn/repo/tools/nets-helper/.venv/bin/gunicorn --bind unix:/run/bhn-nets-helper.sock 'app:create_app()'
   Restart=on-failure
   User=bhn
   Group=bhn

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now bhn-nets-helper
   ```

3. **Web server proxy**

   **Apache (Andre’s host)**
   ```apache
   <Location "/nets-helper/">
       AuthType Basic
       AuthName "Blind Hams Nets Helper"
       AuthUserFile /etc/apache2/.htpasswd_bhn_nets
       Require valid-user

       ProxyPass "unix:/run/bhn-nets-helper.sock|http://localhost/"
       ProxyPassReverse "unix:/run/bhn-nets-helper.sock|http://localhost/"
       RequestHeader set X-Forwarded-Proto "https"
       RequestHeader set X-Forwarded-User "%{REMOTE_USER}e" env=REMOTE_USER
   </Location>

   RedirectMatch permanent "^/nets-helper$" "/nets-helper/"
   ```

   Disable directory listings for `/data` if not already (e.g., `Options -Indexes`).

   **Nginx (other hosts)**
   ```nginx
   location /nets-helper/ {
       auth_basic "Blind Hams Nets Helper";
       auth_basic_user_file /etc/nginx/.htpasswd_bhn_nets;
       proxy_pass http://unix:/run/bhn-nets-helper.sock;
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_set_header X-Forwarded-User $remote_user;
   }
   ```

4. **Basic auth credentials**
   ```bash
   sudo apt-get install apache2-utils
   sudo htpasswd -c /etc/apache2/.htpasswd_bhn_nets net-listing-manager
   sudo systemctl reload apache2
   ```

5. **Workflow for maintainers**
   - A reviewer (e.g., `list-manager`) stages additions or edits. Each save produces or updates a draft snapshot under `_data/pending/`, and the UI lists it under the **Draft review queue**.
   - Publishers (e.g., `web-admin`) see the same list. They review the inline diff summary (including who submitted it and any notes), optionally make further edits, then click **Publish to live**.
   - Publishing stages the updated `_data/nets.json`, commits it to git with an auto-generated message, and pushes to GitHub after the publisher confirms the summary. A timestamped backup (e.g., `nets.backup.20241028_153000.json`) is kept alongside the canonical file.
   - If something goes wrong, publishers can still publish manually by copying a draft file over `_data/nets.json`; the helper simply automates that workflow.
   - After publishing, commit the updated `_data/nets.json` to git as usual so other hosts stay in sync.

   Make sure the `_data/pending/` directory exists and is writable by the service account (`www-data` on Andre’s host):
   ```bash
   sudo mkdir -p /home/ner/bhn/_data/pending
   sudo chown www-data:www-data /home/ner/bhn/_data/pending
   sudo chmod 775 /home/ner/bhn/_data/pending
   ```

### Notifications (optional)

The helper can post updates to [ntfy](https://docs.ntfy.sh/) whenever someone submits a batch for review or publishes a draft to `_data/nets.json`. Configure the service via environment variables:

| Variable | Purpose | Example |
| --- | --- | --- |
| `BHN_NTFY_ENDPOINT` | ntfy base URL (leave empty to disable). | `https://ntfy.sh` |
| `BHN_NTFY_TOPIC` | Topic name to publish into. | `bh-nets-helper` |
| `BHN_NTFY_TOKEN` | *(Optional)* Bearer token if your ntfy instance requires auth. | `secret-token` |

All three variables can be set in the systemd unit or exported before launching the helper. When `BHN_NTFY_ENDPOINT` and `BHN_NTFY_TOPIC` are provided, the helper sends a notification for:

- Batch submitted for review (shows submitter, change count, and the first few IDs).
- Draft published to `_data/nets.json` (shows publisher, stats, and commit information).

## Future Enhancements

- Surface category management helpers.
- Offer optional connection presets (AllStar, DMR, etc.) as reusable snippets.
- Add additional notification channels (email, webhook, SMS, etc.).
- Longer term, accept public “suggest a net” submissions and route them through the same review/publish queue.
