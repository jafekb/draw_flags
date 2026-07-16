# draw_flags
Draw a flag, have it recognized

## Prerequisites

### Install uv
This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quickstart


### Frontend
```bash
cd frontend/
npm install
npm run build
npm run dev
```

The frontend will be available at `http://localhost:5173` (or `http://<your-ip>:5173` for network access)


### Backend
```bash
./scripts/setup-env.sh deploy
./run_backend.sh
```

Note: If you encounter Python version compatibility issues, the project requires Python 3.10-3.13. You can install and pin a compatible version:
```bash
uv python install 3.13
uv python pin 3.13
```

## Image search (optional)

Users can upload a photo and have the flag identified. The image is described by a free,
hosted, open vision model (no on-device model, so the Render Starter box is unaffected), and
that description is fed into the normal text search. Set these env vars on the backend to
enable `POST /image`:

- **Cloudflare Workers AI (default):** `CF_ACCOUNT_ID`, `CF_API_TOKEN`.
  Optional: `VLM_MODEL` (default `@cf/meta/llama-3.2-11b-vision-instruct`).
- **Hugging Face (alternative):** `VLM_PROVIDER=huggingface`, `HF_TOKEN`, and optionally
  `VLM_MODEL` (a HF model id, e.g. `meta-llama/Llama-3.2-11B-Vision-Instruct`).

If unset, text search still works; image uploads return a 502 with a friendly message.
