# SmartHub AI — Android release preparation

## Current delivery model

The repository is a static multi-page HTML/CSS/JavaScript website with a separate FastAPI service. This branch adds an installable PWA shell and the Capacitor configuration needed to generate a native Android project. It does **not** contain a generated, signed APK/AAB yet.

## Test the PWA

1. Deploy the branch to a HTTPS host (GitHub Pages is supported).
2. Open the site in current Chrome on Android.
3. Confirm the install prompt appears when Chrome considers the app installable, or use Chrome menu → Install app.
4. Test navigation, account sign-in, uploads, video processing, and API-backed tools online.
5. Test offline mode only for the cached app shell. API-backed features require network access.

The service worker deliberately does not cache API responses, authentication tokens, user uploads, or generated private media. It caches only the static shell and same-origin static assets.

## Generate the Android project

Use Node.js 20 LTS or newer on a development computer:

```bash
npm install
npx cap add android
npx cap sync android
npx cap open android
```

Build a debug APK from Android Studio first. Test it on a physical Android device before preparing a release.

## Before public distribution

- Verify the production API URL and CORS origin.
- Configure all required provider secrets only on the backend.
- Add a real 192×192 and 512×512 PNG launcher icon and a branded splash screen before store submission.
- Set a unique final Android application ID if needed; changing it later creates a separate app identity.
- Review camera, photo, file, microphone, and notification permissions; request only those actually used.
- Add a public privacy policy, support contact, and accurate app description.
- Test Android back navigation, external links, file pickers, camera scanning, video uploads, and large media files.
- Generate a release AAB/APK and sign it with a secure release keystore. Back up the keystore and passwords securely; never commit them.
- Keep the API and database operational. A web wrapper does not remove backend costs, provider quotas, or uptime requirements.

## Known limitations

- This is a web wrapper, not a rewrite into native Android UI.
- Offline support is limited to the cached website shell; AI generation, accounts, support, and remote storage need connectivity.
- A service worker cannot make unavailable third-party AI providers work offline.
- Android store acceptance, ranking, downloads, and revenue are not guaranteed. Each distribution platform applies its own review and content policies.
