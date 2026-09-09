# Vendored front-end assets

Third-party assets copied into the repository so that the demo page
(`docs/index.html`, also served by the API at `/demo`) renders **without an
internet connection**. Presenting locally is a first-class use case; a page
whose layout depends on a CDN is unusable offline.

| File | Origin | Version fetched | License |
|------|--------|-----------------|---------|
| `tailwind.min.js` | https://cdn.tailwindcss.com (Tailwind Play CDN, includes the in-browser JIT compiler) | 2026-09-09 | MIT |

The page loads the local copy first and falls back to the CDN only if it is
missing, so both the GitHub Pages build and a local `uvicorn` run work.

**Refresh** (online, from the repository root):

```bash
curl -fsSL https://cdn.tailwindcss.com -o docs/vendor/tailwind.min.js
```

Not vendored: the Inter web font (`fonts.googleapis.com`). Offline the page
falls back to `system-ui` via the CSS font stack, which is a cosmetic
difference only — no layout breakage.
