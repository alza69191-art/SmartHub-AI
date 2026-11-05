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


## PostgreSQL on Render

The API connects to a Render PostgreSQL database using the server-side DATABASE_URL environment variable. Add the Internal Database URL to the smarthub-ai-api service in Render → Environment. Never commit database credentials to GitHub or expose them in browser JavaScript.

On startup, the API creates the initial profiles, support_tickets, and support_replies tables and their indexes if they do not already exist. The /health response reports whether PostgreSQL is reachable.

This schema is groundwork only: authentication, authorization, and protected support-ticket endpoints must be implemented before exposing the tables to users. Admin roles must only be assigned through a trusted server-side process.


## Accounts and support center

The API now includes email/password registration and login, bearer-token sessions,
user profiles, support tickets, ticket replies, and admin-only ticket status changes.
Passwords are stored as salted scrypt hashes; plaintext passwords are never stored.

### Required Render environment variables
- `DATABASE_URL`: the Render PostgreSQL **Internal Database URL**.
- `JWT_SECRET`: a random secret of at least 32 characters. Generate one securely and add it only in Render.
- `ADMIN_EMAILS`: comma-separated email addresses allowed to request admin activation.
- `ADMIN_SETUP_KEY`: a separate secret used once during administrator registration. Admin access requires both an allowlisted email and this key.

After setting these variables, redeploy the Render API. Create the administrator account using an address listed in `ADMIN_EMAILS` and enter `ADMIN_SETUP_KEY` in the admin setup field. Other registrations receive the regular user role. Do not share the setup key.

This first release does not yet include email verification, password reset, or automated abuse/rate limiting. Do not treat it as a fully hardened production identity system until those controls are added. The browser keeps the bearer token in session storage for the current tab.

## Free LTX-Video text-to-video integration

The SmartHub video generator uses the public Lightricks LTX-Video Space on Hugging Face. It submits jobs to a shared public GPU queue; no paid video-provider account or video API key is required. An optional `HF_TOKEN` can improve access limits, but anonymous calls are supported.

### Requirements
- Existing SmartHub login and Render API configuration.
- Existing Python dependencies in `api/requirements.txt`; no additional package is needed.
- Public Space availability and shared GPU queue capacity. Queue times, rate limits, and temporary outages are outside SmartHub's control.

### Usage
1. Sign in to SmartHub.
2. Open `video-generator.html` from the Tools page.
3. Enter a prompt, choose 5 or 8 seconds and an aspect ratio.
4. SmartHub creates a background job and polls its status until the video is ready.

API routes:
- `POST /api/video/generate` — queues a text-to-video job.
- `GET /api/video/status/{project_id}` — checks the job and returns the output URL.

The model is `Lightricks/LTX-Video` hosted in the public `Lightricks/ltx-video-distilled` Space. Public demo capacity is shared; it is suitable for testing, not guaranteed production availability. Generation may fail when the Space is paused or overloaded.


## FLUX.1 schnell image generation via Cloudflare Workers AI

The image generator now uses Cloudflare Workers AI instead of the public Qwen Gradio Space.

Add these secrets to the Render API service environment:
- CLOUDFLARE_ACCOUNT_ID: your Cloudflare account ID.
- CLOUDFLARE_API_TOKEN: an API token with Workers AI Write permission.

The API calls @cf/black-forest-labs/flux-1-schnell server-side; credentials are never sent to the browser. The model accepts prompts up to 2,048 characters and supports 4- or 8-step generation. Cloudflare's free Workers AI allocation is 10,000 Neurons per day; it is a quota, not unlimited usage. See https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/ and https://developers.cloudflare.com/workers-ai/platform/pricing/.
