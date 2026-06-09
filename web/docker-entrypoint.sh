#!/bin/sh
# Regenerate config.js from the API_URL env var at container startup.
# The nginx base image runs every /docker-entrypoint.d/*.sh before launching
# nginx, so this lets one immutable image be deployed to dev/staging/prod with
# only the API_URL env var differing.
set -e

cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = { apiUrl: "${API_URL}" }
EOF

echo "config.js: apiUrl=\"${API_URL}\""
