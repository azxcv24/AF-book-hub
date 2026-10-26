"""ISBN/메타데이터 조회 서비스 뼈대.

현재는 OpenLibrary 공개 API만 구현되어 있으며, 네이버/카카오 API 키가
환경변수로 제공되면 해당 제공자를 추가할 수 있다.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


def lookup_isbn(isbn: str, provider: str = "openlibrary") -> dict[str, Any] | None:
    """ISBN으로 책 메타데이터를 조회한다.

    Args:
        isbn: ISBN-10 또는 ISBN-13.
        provider: "openlibrary" | "naver" | "kakao".

    Returns:
        Book 모델 생성/업데이트에 쓸 수 있는 dict 또는 None.
    """
    isbn = _normalize_isbn(isbn)
    if not isbn:
        return None

    if provider == "openlibrary":
        return _lookup_openlibrary(isbn)
    if provider == "naver":
        return _lookup_naver(isbn)
    if provider == "kakao":
        return _lookup_kakao(isbn)
    return None


def _normalize_isbn(isbn: str) -> str:
    return "".join(ch for ch in (isbn or "") if ch.isdigit())


def _lookup_openlibrary(isbn: str) -> dict[str, Any] | None:
    url = f"https://openlibrary.org/isbn/{isbn}.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("OpenLibrary 조회 실패: %s", exc)
        return None

    authors = []
    for author_ref in data.get("authors", []):
        name = author_ref.get("name") if isinstance(author_ref, dict) else None
        if name:
            authors.append(name)
        elif isinstance(author_ref, dict) and "key" in author_ref:
            authors.append(_fetch_author_name(author_ref["key"]))

    publish_date = data.get("publish_date", "")
    published_at = _parse_year(publish_date)

    return {
        "title": data.get("title", ""),
        "authors": ", ".join(a for a in authors if a),
        "publisher": data.get("publishers", [""])[0] if data.get("publishers") else "",
        "published_at": published_at,
        "description": _extract_description(data.get("description")),
        "cover_url": _openlibrary_cover(data.get("covers", [None])[0]),
        "page_count": data.get("number_of_pages"),
        "isbn13": isbn if len(isbn) == 13 else "",
        "isbn10": isbn if len(isbn) == 10 else "",
    }


def _fetch_author_name(key: str) -> str:
    try:
        resp = requests.get(f"https://openlibrary.org{key}.json", timeout=10)
        resp.raise_for_status()
        return resp.json().get("name", "")
    except Exception as exc:
        logger.warning("OpenLibrary 저자 조회 실패: %s", exc)
        return ""


def _extract_description(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("value", "")
    return ""


def _openlibrary_cover(cover_id: int | None) -> str:
    if not cover_id:
        return ""
    return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


def _parse_year(value: str) -> str | None:
    import re

    m = re.search(r"\d{4}", value or "")
    return f"{m.group(0)}-01-01" if m else None


def _lookup_naver(isbn: str) -> dict[str, Any] | None:
    import os

    client_id = os.environ.get("BOOK_HUB_NAVER_CLIENT_ID")
    client_secret = os.environ.get("BOOK_HUB_NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.warning("네이버 책 API 키가 없습니다.")
        return None
    # TODO: 네이버 책 API 연동
    return None


def _lookup_kakao(isbn: str) -> dict[str, Any] | None:
    import os

    api_key = os.environ.get("BOOK_HUB_KAKAO_REST_API_KEY")
    if not api_key:
        logger.warning("카카오 API 키가 없습니다.")
        return None
    # TODO: 카카오 책 검색 API 연동
    return None
