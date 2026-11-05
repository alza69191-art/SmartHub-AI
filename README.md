# SmartHub AI

A responsive Arabic/English toolbox website built with HTML, CSS and vanilla JavaScript.

## Image generation providers

The image generator supports four server-side providers:

- **Google Gemini (default):** Gemini image generation model. Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
- **OVHcloud AI Endpoints:** Stable Diffusion XL. Anonymous inference is rate-limited; an optional `OVH_AI_ENDPOINTS_ACCESS_TOKEN` may raise the limit.
- **Pollinations:** FLUX.1 schnell. Requires the secret `POLLINATIONS_API_KEY` from https://enter.pollinations.ai.
- **Cloudflare Workers AI:** FLUX.1 schnell. Requires `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.

Configure only the providers you intend to use in Render → Environment. Keep every private key on the backend. Provider quotas, prices and regional availability vary; no provider is represented as unlimited.

## Included SmartHub tools

The Tools directory currently lists **24 tools and utilities**:

- **Images:** resize, crop, rotate, flip, watermark, compression, brightness/contrast/sharpening, AI image generation, AI image editing, image upscaling (external browser tool), image-to-3D guidance (local Modly workflow), image-to-QR, and temporary image sharing.
- **Video:** trim, sequential merge, split, compression, MP4 conversion, audio extraction, mute, rotation, speed, reverse, color correction, crop, GIF, audio fade and volume adjustment.
- **Audio and documents:** audio trim/merge and WAV export; PDF merge and image-to-PDF.
- **Scanning and utilities:** QR/barcode scan and generation, word counter, case conversion, JSON formatter, prompt generator, local notes, Base64, URL encoding, text cleanup and password generation.
- **AI:** experimental Arabic/English text detector and text-to-video generation through a public LTX-Video Space.

Local browser tools process files on the device. Account-backed tools and AI endpoints send the required input to the SmartHub API or the selected external provider. Review each tool's notice before uploading private material. AI detection is probabilistic; public model demos and external tools are not guaranteed to be available.

## Tool readiness and provider configuration

The interface and tool workflows are implemented. Before using provider-backed features, configure only the credentials for the providers you choose in Render → Environment. Never put secret keys in config.js, HTML, or browser JavaScript.

| Feature | Required server configuration |
|---|---|
| AI assistant | GROQ_API_KEY (Gemini/Hugging Face are optional fallbacks where configured) |
| AI image generation/editing | GEMINI_API_KEY or GOOGLE_API_KEY; optional OVHcloud, Pollinations and Cloudflare credentials |
| AI text detector | HF_TOKEN and accessible Arabic/English inference models |
| AI video | Public Hugging Face LTX Space; optional HF_TOKEN |
| Accounts, support and image links | DATABASE_URL, JWT_SECRET, ADMIN_EMAILS |
| Google sign-in | GOOGLE_CLIENT_ID plus the matching authorized browser origin |

The video job queue is process-local and bounded: at most one active job per user and four active jobs per API process; completed/failed job records expire after six hours. This is a testing-oriented queue, not durable multi-instance job infrastructure.

## Deploy with GitHub Pages
1. Open repository **Settings** → **Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select **main** and **/(root)**, then click **Save**.
4. Wait for deployment; GitHub will display the published URL in Pages settings.

## Frontend deployment and secrets
GitHub Pages serves the static frontend. All private provider credentials belong in the Render API environment and must never be committed to browser files. The frontend calls the backend through `config.js`; update `window.SMART_HUB_API_URL` only to the actual deployed API origin.

 
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

The API initializes these tables and exposes authenticated account, support-ticket, reply and image-sharing routes. Admin-only ticket operations are protected by the server-side role check. Admin roles must only be assigned through a trusted server-side database operation for an allowlisted email.


## Accounts and support center

The API now includes email/password registration and login, bearer-token sessions,
user profiles, support tickets, ticket replies, and admin-only ticket status changes.
Passwords are stored as salted scrypt hashes; plaintext passwords are never stored.

### Required Render environment variables
- `DATABASE_URL`: the Render PostgreSQL **Internal Database URL**.
- `JWT_SECRET`: a random secret of at least 32 characters. Generate one securely and add it only in Render.
- `ADMIN_EMAILS`: comma-separated allowlisted administrator email addresses.

After setting these variables, redeploy the Render API. Public registration cannot assign administrator privileges. Create the first administrator through a trusted, authenticated database operation that sets the role for an allowlisted account. Never expose database credentials or an admin setup secret in the browser.

Email verification and password reset are not implemented. API rate limits are process-local and do not replace a shared edge/WAF limit in a multi-instance production deployment. The browser keeps the bearer token in session storage for the current tab.

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
