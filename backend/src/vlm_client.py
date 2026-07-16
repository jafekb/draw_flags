"""
Query-time VLM client: describe an uploaded flag image with a free, hosted, open
vision model, then let the existing text search do the matching.

We deliberately do NOT run a vision model on the Render box (512 MB / 0.5 CPU). The
image goes to a hosted provider (default Cloudflare Workers AI, Hugging Face as a
swappable alternative), which returns a country-agnostic description; that text feeds
the same bge description search users get when they type a query. So the deployed
service gains no heavy dependency — this module only needs `requests`.

The exact same prompt as the offline description generator (VLM_PROMPT) is used, so an
uploaded image is described in the same vocabulary as the corpus it's matched against.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Dict, List

import requests

from backend.common.descriptions import VLM_PROMPT

# Providers vary in how strictly they emit JSON and how they accept images; both are
# behind describe_image() so the endpoint doesn't care which one is configured.
DEFAULT_PROVIDER = "cloudflare"
DEFAULT_CF_MODEL = "@cf/meta/llama-3.2-11b-vision-instruct"
DEFAULT_HF_MODEL = "meta-llama/Llama-3.2-11B-Vision-Instruct"
REQUEST_TIMEOUT_S = 45
MAX_TOKENS = 400


class VLMError(RuntimeError):
    """Raised when the hosted VLM call fails (transport, auth, rate limit, bad body)."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise VLMError(f"{name} is not set; cannot call the hosted VLM provider.")
    return value


def _call_cloudflare(image_bytes: bytes) -> str:
    """POST the image to Cloudflare Workers AI, return the model's raw text response."""
    account_id = _require_env("CF_ACCOUNT_ID")
    token = _require_env("CF_API_TOKEN")
    model = os.getenv("VLM_MODEL", DEFAULT_CF_MODEL)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    # Workers AI vision models take the image as an array of unsigned byte values.
    payload = {
        "image": list(image_bytes),
        "prompt": VLM_PROMPT,
        "max_tokens": MAX_TOKENS,
    }
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise VLMError(f"Cloudflare request failed: {exc}") from exc
    if resp.status_code != 200:
        raise VLMError(f"Cloudflare returned {resp.status_code}: {resp.text[:300]}")
    try:
        body = resp.json()
        return body["result"]["response"]
    except (ValueError, KeyError, TypeError) as exc:
        raise VLMError(f"Unexpected Cloudflare response shape: {resp.text[:300]}") from exc


def _call_huggingface(image_bytes: bytes, media_type: str) -> str:
    """POST the image to a Hugging Face Inference Provider (OpenAI-compatible chat)."""
    token = _require_env("HF_TOKEN")
    model = os.getenv("VLM_MODEL", DEFAULT_HF_MODEL)
    data_uri = f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    payload = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": VLM_PROMPT},
                ],
            }
        ],
    }
    try:
        resp = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise VLMError(f"Hugging Face request failed: {exc}") from exc
    if resp.status_code != 200:
        raise VLMError(f"Hugging Face returned {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise VLMError(f"Unexpected Hugging Face response shape: {resp.text[:300]}") from exc


def _parse_description(text: str) -> Dict:
    """
    Parse the model's reply into {description, layout, colors, symbols}. Open models
    follow strict-JSON less reliably than Claude, so strip code fences and, if JSON
    parsing fails entirely, fall back to using the whole reply as the description — a
    plain sentence is still a perfectly good query.
    """
    raw = (text or "").strip()
    cleaned = raw
    if cleaned.startswith("```"):
        # ```json\n{...}\n``` -> take the fenced middle segment
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1].removeprefix("json").strip()
    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
    except (ValueError, TypeError):
        return {"description": raw, "layout": "", "colors": [], "symbols": []}

    def _as_list(value) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value if str(v).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return {
        "description": str(data.get("description", "") or "").strip(),
        "layout": str(data.get("layout", "") or "").strip(),
        "colors": _as_list(data.get("colors")),
        "symbols": _as_list(data.get("symbols")),
    }


def describe_image(image_bytes: bytes, media_type: str = "image/jpeg") -> Dict:
    """
    Describe a flag image via the configured hosted VLM.

    Returns a dict with keys description/layout/colors/symbols. Raises VLMError on any
    provider/transport failure so the endpoint can surface a clear message.
    """
    provider = os.getenv("VLM_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider == "cloudflare":
        raw = _call_cloudflare(image_bytes)
    elif provider in ("huggingface", "hf"):
        raw = _call_huggingface(image_bytes, media_type)
    else:
        raise VLMError(f"Unknown VLM_PROVIDER '{provider}' (use 'cloudflare' or 'huggingface').")
    return _parse_description(raw)


def description_to_query(parsed: Dict) -> str:
    """
    Turn a parsed VLM description into a search string, mirroring the corpus documents
    built by backend.common.descriptions.build_document (description. layout. symbols.
    colors) so the query and the indexed flags share vocabulary. No name is included —
    an uploaded image carries no name to match.
    """
    parts: List[str] = []
    if parsed.get("description"):
        parts.append(parsed["description"])
    if parsed.get("layout"):
        parts.append(parsed["layout"])
    if parsed.get("symbols"):
        parts.append(", ".join(parsed["symbols"]))
    if parsed.get("colors"):
        parts.append(", ".join(parsed["colors"]))
    return ". ".join(parts)
