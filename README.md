# SmartHub AI

A responsive Arabic/English toolbox website built with HTML, CSS and vanilla JavaScript.

## Image generation providers

The image generator supports three server-side providers:

- **OVHcloud AI Endpoints (default):** Stable Diffusion XL. Anonymous requests are supported with a limit of 2 requests per minute per model and source IP. An optional `OVH_AI_ENDPOINTS_ACCESS_TOKEN` raises the documented limit; OVHcloud account keys require a Public Cloud project with a payment method.
- **Pollinations:** FLUX.1 schnell. Requires the secret `POLLINATIONS_API_KEY` from https://enter.pollinations.ai. Keep this key on the backend only.
- **Cloudflare Workers AI:** FLUX.1 schnell. Requires `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.

Set optional credentials in Render → Environment. The user selects the provider in the image generator. OVHcloud's anonymous rate limit is shared by requests from the same server IP, so it is suitable for limited testing, not unlimited production use.

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


## Image generation and editing

SmartHub includes two separate Google Gemini image tools:
- `image-generator.html`: text-to-image generation. Google Gemini (Nano Banana 2 / `gemini-3.1-flash-image`) is the default provider; OVHcloud, Pollinations, and Cloudflare remain optional alternatives.
- `image-editor.html`: upload a PNG, JPEG, or WebP image and describe edits in natural language. The image and prompt are sent to the backend for Gemini image editing.

Configure `GEMINI_API_KEY` in the Render API service environment. The key is read only by FastAPI and is never exposed to browser JavaScript. Both image endpoints require an authenticated SmartHub user:
- `POST /api/images/generate`
- `POST /api/images/edit`

The editor accepts images up to 12 MB. Gemini API usage is subject to the model's current pricing, quotas, and regional availability; do not assume unlimited or free image generation. See the official [Gemini image generation and editing guide](https://ai.google.dev/gemini-api/docs/image-generation).

Optional alternative providers:
- OVHcloud: public anonymous inference has rate limits; an optional `OVH_AI_ENDPOINTS_ACCESS_TOKEN` can be configured.
- Pollinations: requires `POLLINATIONS_API_KEY`.
- Cloudflare Workers AI: requires `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`; free Neurons are quota-limited, not unlimited.
