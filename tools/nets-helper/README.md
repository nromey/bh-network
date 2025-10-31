# Blind Hams Net Helper

Web helper for trusted schedulers to draft `_data/nets.yml` updates from a browser. The app intentionally **never overwrites** the live file; instead it writes a timestamped pending copy so a maintainer can inspect, rename, and commit.

## Overview

- **Frontend:** Accessible form with live YAML preview.
- **Backend:** Small Flask app that validates inputs, checks for duplicate IDs, and appends the new entry to a pending copy of `_data/nets.yml` (saved under `_data/pending/`).
- **Security:** Protect the route with HTTP Basic Auth (Nginx `auth_basic`) so only designated editors can reach it.

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
   }
   ```

4. **Basic auth credentials**
   ```bash
   sudo apt-get install apache2-utils
   sudo htpasswd -c /etc/apache2/.htpasswd_bhn_nets net-listing-manager
   sudo systemctl reload apache2
   ```

5. **Workflow for maintainers**
   - Net Listing Manager submits a new net.
   - The app writes `_data/pending/nets.pending.YYYYMMDD_HHMMSS.yml`.
   - Review the file (diff against `_data/nets.yml`), then replace the canonical file:
     ```bash
     mv _data/pending/nets.pending.20250317_153000.yml _data/nets.yml
     git add _data/nets.yml
     git commit -m "Add <net name>"
     ```
   - Push or pull into other hosts as usual.

   Make sure the `_data/pending/` directory exists and is writable by the service account (`www-data` on Andre’s host):
   ```bash
   sudo mkdir -p /home/ner/bhn/_data/pending
   sudo chown www-data:www-data /home/ner/bhn/_data/pending
   sudo chmod 775 /home/ner/bhn/_data/pending
   ```

## Future Enhancements

- Edit existing entries (load by ID, update, and rewrite pending file).
- Surface category management.
- Offer optional connection presets (AllStar, DMR, etc.) as reusable snippets.

## Upcoming Workflow

- Prefer an existing `_data/pending/nets.pending.*.yml` snapshot when loading context; fall back to `_data/nets.yml` if no pending file exists. That working snapshot powers previews and duplicate checks.
- Let schedulers enter a net, click **Add**, and keep iterating so multiple nets can be staged in one session. Duplicate IDs only need to be checked against the working snapshot (pending file already contains the live data).
- When the staged list is ready, write the working snapshot plus all queued additions to a timestamped pending file so maintainers can review before promoting to `nets.yml`.
- Next phase will introduce edit mode against the same working snapshot (pending first, canonical as fallback) while keeping the append-only flow available.
- Longer term, surface user-submitted nets for scheduler review so they can merge, edit, and submit the bundle for webmaster approval from the same interface.
