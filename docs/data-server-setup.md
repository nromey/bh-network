Title: Data Host Setup for Blind Hams JSON

Overview
- This guide describes how to configure the data host that serves live JSON to https://www.blindhams.network.
- Endpoints (canonical):
  - Weekly and Next Net: /next_nets.json
  - NCO 12-week: /bhn_nco_12w.json

Core requirements
- HTTPS required
- Content-Type: application/json; charset=utf-8
- CORS: either allow https://www.blindhams.network or wildcard for read-only GET
- Caching: enable ETag/Last-Modified and a small max-age for freshness

Minimal headers to send
- Access-Control-Allow-Origin: https://www.blindhams.network
  - For public data, you may use: *
- Access-Control-Allow-Methods: GET, OPTIONS
- Cache-Control: public, max-age=60, s-maxage=300
- Content-Type: application/json; charset=utf-8

JSON shapes
1) Weekly + Next Net (next_nets.json)
   - Prefer current shape:
     {
       "generated_at": "2025-10-09T17:20:01Z",
       "items": [
         {
           "id": "friday-night-net",
           "name": "The Friday Night Blind Hams Allstar and Echolink Net",
           "category": "bhn",
           "duration_min": 60,
           "start_iso": "2025-10-10T20:00:00-04:00",
           "end_iso": "2025-10-10T21:00:00-04:00",
           "time_zone": "America/New_York"   // optional but recommended
         }
       ],
       "next_net": { /* same shape as items[] object (optional) */ }
     }

   - Legacy shape also accepted (week[] + start_local_iso). The client supports both.

2) NCO 12-week (bhn_nco_12w.json)
   {
     "updated_at": "2025-10-09T17:20:01Z",
     "time_local": "10:00",            // 24h HH:MM (optional)
     "tz_full": "Eastern",             // Human label for table header (optional)
     "items": [
       { "date": "2025-10-11", "nco": "VE3RWJ", "notes": "optional", "unassigned": false },
       { "date": "2025-10-18", "nco": "N2DYI",  "notes": "",         "unassigned": false }
     ]
   }

Notes and expectations
- Dates are YYYY-MM-DD (no time portion) for NCO.
- For weekly items, include start_iso with an explicit offset (e.g., -04:00) and time_zone when possible (IANA ID).
- The client derives end times from duration_min if end_iso is omitted.

Recommended hosting setups

NGINX example
  location ~ ^/(next_nets\.json|bhn_nco_12w\.json)$ {
    add_header Access-Control-Allow-Origin "https://www.blindhams.network" always;
    add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
    add_header Cache-Control "public, max-age=60, s-maxage=300";
    types { application/json json; }
    default_type application/json; charset=utf-8;
    try_files $uri =404;
  }

Apache example (.htaccess)
  <FilesMatch "^(next_nets|bhn_nco_12w)\.json$">
    Header set Access-Control-Allow-Origin "https://www.blindhams.network"
    Header set Access-Control-Allow-Methods "GET, OPTIONS"
    Header set Cache-Control "public, max-age=60, s-maxage=300"
    AddType application/json .json
    CharsetSourceEnc utf-8
  </FilesMatch>

Apache VirtualHost (reverse proxy to upstream path)
  # If data.blindhams.network is a CNAME to 3.onj.me and you proxy to /data
  # Requires: a vhost for data.blindhams.network and modules: headers, proxy, proxy_http
  <VirtualHost *:443>
    ServerName data.blindhams.network
    # SSL config elided

    ProxyPreserveHost On
    ProxyPass        /  http://3.onj.me/data/
    ProxyPassReverse /  http://3.onj.me/data/

    # CORS for the website origin
    Header always set Access-Control-Allow-Origin "https://www.blindhams.network"
    Header always set Access-Control-Allow-Methods "GET, HEAD, OPTIONS"
    Header always set Access-Control-Allow-Headers "Content-Type"

    # Ensure correct content-type for JSON files
    AddType application/json .json
  </VirtualHost>

S3/CloudFront
- Bucket CORS JSON:
  [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedOrigins": ["https://www.blindhams.network"],
      "ExposeHeaders": [],
      "MaxAgeSeconds": 300
    }
  ]
- Set Content-Type metadata to application/json and enable ETag/Last-Modified.

Operational tips
- Keep timestamps in UTC (Z) where applicable.
- Automate generation to run at least daily or on change.
- Validate JSON before publish; return well-formed JSON even when empty (e.g., items: []).
- Prefer short cache lifetimes (60–300s) to balance freshness and CDN efficiency.

Testing checklist
- curl -I https://data.example.tld/bhn_nco_12w.json → verify CORS and Content-Type
- curl -fsSL https://data.example.tld/next_nets.json | jq 
- Load https://www.blindhams.network/?diag=1 and confirm “Live data loaded …” lines appear.
