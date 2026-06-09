// Runtime config. In dev this placeholder is ignored (the app falls back to
// VITE_API_URL). In the Docker image, the container entrypoint regenerates this
// file from the API_URL env var at startup — so one image works in every env.
window.__APP_CONFIG__ = { apiUrl: "__API_URL__" }
