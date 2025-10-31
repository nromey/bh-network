# Blind Hams Net Helper

Web helper for trusted schedulers to draft `_data/nets.yml` updates from a browser. The app intentionally **never overwrites** the live file; instead it writes a timestamped pending copy so a maintainer can inspect, rename, and commit.

## Overview

- **Frontend:** Accessible form with live YAML preview, edit mode, autosave drafts, and a pending-review dashboard.
- **Backend:** Flask app that validates inputs, prevents ID collisions, writes timestamped pending copies in `_data/pending/`, and can promote approved bundles into `_data/nets.yml`.
- **Security:** Keep HTTP Basic Auth in front, and have the web server forward the authenticated username so role-based permissions (review vs. promote) can be enforced.

## Local Development

```bash
cd tools/nets-helper
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export BHN_NETS_FILE="$(git rev-parse --show-toplevel)/_data/nets.yml"
export BHN_NETS_OUTPUT_DIR="$(git rev-parse --show-toplevel)/_data"
flask --app app run --debug

# Note: if you override these paths manually, use absolute paths or `$HOME`.
# Using a literal `"~/..."` will not expand the tilde.
```

Load http://127.0.0.1:5000/ to try the form. Pending files will be created under `_data/pending/` with names like `nets.pending.20250317_153000.yml`.

### Roles & Permissions

- Roles are defined in `tools/nets-helper/roles.yml`. The sample file maps `publishers` (can promote pending files) and `reviewers` (can stage/edit but not promote).
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
   Environment="BHN_NETS_FILE=/opt/bhn/repo/_data/nets.yml"
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
   - A reviewer (e.g., `list-manager`) stages additions or edits. Each save produces/updates a pending snapshot under `_data/pending/` and the UI lists it under “Pending submissions”.
   - Publishers (e.g., `web-admin`) see the same list. They review the change summary, optionally make further edits, then click **Promote to live** to atomically copy the snapshot into `_data/nets.yml`. A timestamped backup (e.g., `nets.backup.20241028_153000.yml`) is kept alongside the canonical file.
   - If something goes wrong, publishers can still promote manually by copying a pending file over `_data/nets.yml`; the helper simply automates that workflow.
   - After promoting, commit the updated `_data/nets.yml` to git as usual so other hosts stay in sync.

   Make sure the `_data/pending/` directory exists and is writable by the service account (`www-data` on Andre’s host):
   ```bash
   sudo mkdir -p /home/ner/bhn/_data/pending
   sudo chown www-data:www-data /home/ner/bhn/_data/pending
   sudo chmod 775 /home/ner/bhn/_data/pending
   ```

## Future Enhancements

- Diff preview for each pending bundle (so reviewers can see field-level changes inline).
- Surface category management helpers.
- Offer optional connection presets (AllStar, DMR, etc.) as reusable snippets.
- Longer term, accept public “suggest a net” submissions and route them through the same review/promotion queue.
