# Security policy

## Configuration
- Store API keys, database credentials, JWT secrets, Google OAuth client secrets, and upload-provider secrets only in the backend host's secret environment variables.
- The browser may contain a Google OAuth **client ID**; it must never contain a client secret.
- Set `GOOGLE_CLIENT_ID` on Render and the matching public `SMART_HUB_GOOGLE_CLIENT_ID` in `config.js`.
- Set `JWT_SECRET` to a cryptographically random value of at least 32 characters.
- Keep `FRONTEND_ORIGIN` restricted to the exact deployed frontend origin.

## Account and API controls
- Google ID tokens are verified server-side against the configured OAuth client ID and verified email claim.
- User profile data and support records are stored in PostgreSQL. Browser session tokens are not a substitute for server-side authorization.
- API responses disable caching and include baseline browser security headers.
- Login and registration endpoints have a lightweight per-process request throttle. For production, enforce rate limits at the hosting edge/WAF as well; in-memory limits do not coordinate across multiple instances.
- Enforce authorization on every private endpoint and never rely on hiding a route or UI element.

## Browser developer tools
It is not possible to reliably hide frontend source code, network requests, or public configuration from browser developer tools. Treat all browser-delivered code and values as public. Security comes from keeping secrets server-side, validating inputs, enforcing access control, and minimizing sensitive responses.

## Deployment checklist
1. Configure `DATABASE_URL`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, and `FRONTEND_ORIGIN` in Render.
2. Add the deployed frontend origin and callback/JavaScript origin in Google Cloud OAuth settings.
3. Rotate any API key that has ever appeared in logs, screenshots, browser code, or repository history.
4. Review Render logs for unexpected authentication failures and configure edge-level rate limiting.
