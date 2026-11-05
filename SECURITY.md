# Security policy

## Secrets and browser visibility
- Store API keys, database credentials, JWT secrets, Google OAuth client secrets, Hugging Face tokens, and upload-provider secrets only in backend environment variables.
- The browser may contain the Google OAuth **client ID** and the public API base URL. A client ID is not a client secret.
- Never put API keys, service-account JSON, database URLs, admin setup keys, or private signing keys in HTML, JavaScript, public configuration, or GitHub Pages.
- Browser source code, public configuration, network requests, request payloads, and responses can be inspected with developer tools. It is impossible to hide them reliably. The server must therefore treat every browser value as untrusted.
- The public registration flow cannot promote an account to admin. Provision admin roles through a controlled database operation and keep the email on the server-side ADMIN_EMAILS allowlist.

## Account and data persistence
- User profiles and support tickets are stored in PostgreSQL.
- Passwords are stored as salted scrypt hashes; plaintext passwords are not stored.
- Google ID tokens are verified server-side against the configured OAuth client ID and verified email claim.
- Browser session tokens are kept in sessionStorage for the current browser session. Do not move bearer tokens to localStorage without a reviewed XSS threat model.
- Private API endpoints must enforce authorization on every request; hiding a UI route is not authorization.

## Image sharing
- Image sharing requires authentication and PostgreSQL.
- Only PNG, JPEG, and WebP files up to 5 MB are accepted; the server checks file signatures. Each account is limited to 10 active share links and 25 MB of active shared image data.
- Share URLs are public bearer links for anyone who has the URL and expire after 30 days. Users should not upload sensitive images.
- Expired records are excluded from retrieval and are purged during subsequent uploads. Configure a database retention job if strict physical deletion timing is required.

## AI text detection
- Text is sent from the browser to the backend and then to the configured Hugging Face model when the feature is used.
- Configure HF_TOKEN only in Render, never in the frontend.
- Detection output is probabilistic, model-dependent, and not proof of authorship. Short texts are rejected; do not use results for high-stakes or punitive decisions.
- Hugging Face inference availability, model support, and quotas can change. A configured model may still be unavailable or rate-limited.

## API controls
- CORS defaults to the GitHub Pages origin and should be set to the exact deployed frontend origin in Render.
- API responses use no-store caching and baseline security headers.
- Authentication and AI detector endpoints have lightweight in-process throttling. Add hosting-edge/WAF rate limiting for production and multi-instance deployments.
- Request-size checks use Content-Length plus endpoint-level Pydantic/file limits. A reverse proxy should also enforce request-body limits.

## Deployment checklist
1. Configure DATABASE_URL, JWT_SECRET (at least 32 random characters), GOOGLE_CLIENT_ID, HF_TOKEN, and FRONTEND_ORIGIN in Render.
2. Add the frontend JavaScript origin to Google Cloud OAuth settings.
3. Set AI_DETECTOR_MODEL_AR and AI_DETECTOR_MODEL_EN only to models you have verified are available through your Hugging Face inference entitlement.
4. Rotate any key that has ever appeared in logs, screenshots, browser code, or repository history.
5. Review Render logs and configure edge-level rate limiting.
6. Review Gitleaks and dependency-audit workflow results before merging.
