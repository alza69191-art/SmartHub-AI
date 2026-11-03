# SmartHub AI

A responsive Arabic/English toolbox website built with HTML, CSS and vanilla JavaScript.

## Included browser tools
1. Word counter
2. Case converter
3. JSON formatter and validator
4. Prompt generator
5. Quick notes (saved in browser localStorage)
6. Base64 encoder / decoder
7. URL encoder / decoder
8. Text cleaner
9. Secure random password generator (uses the browser Web Crypto API)

All tools run locally in the browser. User-entered text is not sent to a server.

## Deploy with GitHub Pages
1. Open repository **Settings** → **Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select **main** and **/(root)**, then click **Save**.
4. Wait for deployment; GitHub will display the published URL in Pages settings.

## Future AI integrations
GitHub Pages is static hosting. Never put private API keys in browser files. Add AI providers through a backend or serverless function and store credentials in server-side environment variables.

 
## Groq AI backend on Render

The FastAPI backend lives in `api/`. The `render.yaml` file defines a Render web service.
1. In Render, choose **New → Blueprint** and connect this repository.
2. Review the `smarthub-ai-api` service and deploy it.
3. In the service's **Environment** settings, add `GROQ_API_KEY` with your private Groq key. Never commit the key.
4. Copy the deployed service URL and set `window.SMART_HUB_API_URL` in `config.js` to that URL, then commit the change.
5. Redeploy the static GitHub Pages site if required.

The chat uses the server-side Groq client and the `llama-3.3-70b-versatile` model. Configure `FRONTEND_ORIGIN` to your exact GitHub Pages origin before public launch.
