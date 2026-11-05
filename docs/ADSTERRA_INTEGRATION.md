# Adsterra integration notes

## Current implementation
- The homepage and tools directory contain neutral, accessible ad-placement containers.
- These containers are intentionally inert: they do not load third-party JavaScript, open popups, track visitors, or contact Adsterra.
- No Adsterra script URL or publisher code has been added to the repository.

## Before enabling a provider
1. Obtain the current official integration instructions and code directly from the authenticated Adsterra publisher dashboard.
2. Verify the script origin, redirect behavior, privacy implications, and whether the selected placement is permitted on GitHub Pages.
3. Review the integration against the site's security policy and applicable privacy/consent requirements.
4. Test in a separate branch with browser developer tools, including mobile behavior, content blockers, and failure cases.
5. Only then replace the placeholder with a reviewed integration. Do not paste publisher JavaScript into the page without that review.

## Placement locations
- `index.html`: between the hero and homepage tools section.
- `tools.html`: above the tools grid.
- `styles.css`: responsive `.ad-slot` styling.
