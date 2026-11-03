# SmartHub AI

Responsive Arabic/English toolbox website built with HTML, CSS and vanilla JavaScript.

## Included tools
- Word counter
- Case converter
- JSON formatter and validator
- Prompt generator
- Quick notes (saved in browser localStorage)
- Base64 encoder / decoder

All tools currently run locally in the browser. User-entered text is not sent to a server.

## Deploy with GitHub Pages
1. Open repository **Settings** → **Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select **main** and **/(root)**, then click **Save**.
4. Wait for deployment; GitHub will display the published URL on the Pages settings page.

## AI API integration
GitHub Pages is static hosting. Never put private API keys in browser files. Add AI providers through a backend or serverless function and store credentials in server-side environment variables.
