"""
Tests for image-upload flag search: the VLM response parsing / query building
(pure functions) and the POST /image endpoint (with the hosted VLM and the searcher
faked, so the test needs no network, no model files, and no httpx/TestClient).
"""

import asyncio
import base64
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.append(str(Path(__file__).parent.parent.parent))

from backend import main
from backend.common.flag_data import Flag, FlagList
from backend.src import vlm_client
from backend.src.vlm_client import _parse_description, description_to_query


def _fake_flag(name: str) -> Flag:
    return Flag(
        name=name,
        wikipedia_page=name,
        wikipedia_url=f"https://en.wikipedia.org/wiki/{name}",
        wikipedia_image_url=f"https://img.test/{name}.svg",
        category="national",
        entity_type="country",
        score=0.9,
    )


class _FakeSearcher:
    def __init__(self):
        self.last_query = None
        self.last_kwargs = None

    def query(self, text_query, filters=None, top_k=None):
        self.last_query = text_query
        self.last_kwargs = {"filters": filters, "top_k": top_k}
        return FlagList(flags=[_fake_flag("Japan")])


# ---- pure helpers -------------------------------------------------------------


def test_parse_description_plain_json():
    parsed = _parse_description(
        '{"description": "a red disc on white", "layout": "plain field", '
        '"colors": ["white", "red"], "symbols": ["disc"]}'
    )
    assert parsed["description"] == "a red disc on white"
    assert parsed["layout"] == "plain field"
    assert parsed["colors"] == ["white", "red"]
    assert parsed["symbols"] == ["disc"]


def test_parse_description_fenced_json():
    parsed = _parse_description('```json\n{"description": "green field, white crescent"}\n```')
    assert parsed["description"] == "green field, white crescent"
    assert parsed["colors"] == []


def test_parse_description_non_json_falls_back_to_raw_text():
    # Open models sometimes ignore the JSON instruction; the raw reply is still a query.
    parsed = _parse_description("A blue flag with a white sun in the center.")
    assert parsed["description"] == "A blue flag with a white sun in the center."
    assert parsed["layout"] == ""
    assert parsed["colors"] == []


def test_description_to_query_mirrors_build_document():
    query = description_to_query(
        {
            "description": "a red disc on white",
            "layout": "plain field",
            "symbols": ["disc"],
            "colors": ["white", "red"],
        }
    )
    assert query == "a red disc on white. plain field. disc. white, red"


# ---- endpoint -----------------------------------------------------------------


def _b64_bytes(data: bytes = b"\x89PNG\r\n\x1a\n") -> str:
    return base64.b64encode(data).decode("ascii")


def test_search_by_image_happy_path(monkeypatch):
    fake = _FakeSearcher()
    monkeypatch.setattr(main.app.state, "flag_searcher", fake, raising=False)
    monkeypatch.setattr(
        main,
        "describe_image",
        lambda _b: {
            "description": "a red disc on white",
            "layout": "plain field",
            "colors": ["white", "red"],
            "symbols": ["disc"],
        },
    )

    req = main.ImageSearchRequest(image=_b64_bytes())
    result = asyncio.run(main.search_by_image(req))

    assert result.detected == "a red disc on white"
    assert [f.name for f in result.flags] == ["Japan"]
    # The description (not any name) is what gets searched.
    assert fake.last_query == "a red disc on white. plain field. disc. white, red"


def test_search_by_image_accepts_data_uri(monkeypatch):
    monkeypatch.setattr(main.app.state, "flag_searcher", _FakeSearcher(), raising=False)
    monkeypatch.setattr(main, "describe_image", lambda _b: {"description": "blue"})
    req = main.ImageSearchRequest(image=f"data:image/jpeg;base64,{_b64_bytes()}")
    result = asyncio.run(main.search_by_image(req))
    assert result.detected == "blue"


def test_search_by_image_vlm_failure_returns_502(monkeypatch):
    monkeypatch.setattr(main.app.state, "flag_searcher", _FakeSearcher(), raising=False)

    def _boom(_b):
        raise vlm_client.VLMError("rate limited")

    monkeypatch.setattr(main, "describe_image", _boom)
    req = main.ImageSearchRequest(image=_b64_bytes())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.search_by_image(req))
    assert exc.value.status_code == 502


def test_search_by_image_rejects_bad_base64(monkeypatch):
    monkeypatch.setattr(main.app.state, "flag_searcher", _FakeSearcher(), raising=False)
    req = main.ImageSearchRequest(image="not!base64!!")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.search_by_image(req))
    assert exc.value.status_code == 400


def test_search_by_image_empty_description_returns_422(monkeypatch):
    monkeypatch.setattr(main.app.state, "flag_searcher", _FakeSearcher(), raising=False)
    monkeypatch.setattr(main, "describe_image", lambda _b: {"description": "", "colors": []})
    req = main.ImageSearchRequest(image=_b64_bytes())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.search_by_image(req))
    assert exc.value.status_code == 422
