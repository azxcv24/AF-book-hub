"""ISBN/메타데이터 조회 서비스.

OpenLibrary(공개), 네이버 책 API, 카카오 책 검색 API를 지원한다.
환경변수에 키가 없으면 OpenLibrary만 사용하거나 None을 반환한다.
"""
from __future__ import annotations

import logging
import os
import re
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
    isbn = normalize_isbn(isbn)
    if not isbn:
        return None

    if provider == "openlibrary":
        return _lookup_openlibrary(isbn)
    if provider == "naver":
        return _lookup_naver(isbn)
    if provider == "kakao":
        return _lookup_kakao(isbn)
    return None


def lookup_isbn_any(isbn: str) -> dict[str, Any] | None:
    """ISBN으로 가능한 모든 제공자를 순회하며 조회한다."""
    isbn = normalize_isbn(isbn)
    if not isbn:
        return None

    providers = ["openlibrary", "naver", "kakao"]
    for provider in providers:
        try:
            result = lookup_isbn(isbn, provider)
            if result:
                return result
        except Exception as exc:
            logger.debug("%s 조회 실패: %s", provider, exc)
    return None


def normalize_isbn(isbn: str) -> str:
    return "".join(ch for ch in (isbn or "") if ch.isdigit())


def isbn10_to_isbn13(isbn10: str) -> str | None:
    """ISBN-10을 ISBN-13으로 변환한다."""
    isbn = normalize_isbn(isbn10)
    if len(isbn) != 10:
        return None
    body = "978" + isbn[:-1]
    check = _isbn13_checksum(body)
    return body + str(check)


def isbn13_to_isbn10(isbn13: str) -> str | None:
    """ISBN-13을 ISBN-10으로 변환한다(978 접두사만 지원)."""
    isbn = normalize_isbn(isbn13)
    if len(isbn) != 13 or not isbn.startswith("978"):
        return None
    body = isbn[3:-1]
    check = _isbn10_checksum(body)
    return body + str(check)


def _isbn13_checksum(body: str) -> int:
    total = sum((int(ch) if i % 2 == 0 else int(ch) * 3) for i, ch in enumerate(body))
    return (10 - (total % 10)) % 10


def _isbn10_checksum(body: str) -> int:
    total = sum((10 - i) * int(ch) for i, ch in enumerate(body))
    return (11 - (total % 11)) % 11


def _lookup_openlibrary(isbn: str) -> dict[str, Any] | None:
    url = f"https://openlibrary.org/isbn/{isbn}.json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return None
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
            authors.append(_fetch_openlibrary_author(author_ref["key"]))

    publish_date = data.get("publish_date", "")
    published_at = _parse_year(publish_date)

    isbn13 = isbn if len(isbn) == 13 else isbn10_to_isbn13(isbn) if len(isbn) == 10 else ""
    isbn10 = isbn if len(isbn) == 10 else isbn13_to_isbn10(isbn) if len(isbn) == 13 else ""

    return {
        "title": data.get("title", ""),
        "authors": ", ".join(a for a in authors if a),
        "publisher": data.get("publishers", [""])[0] if data.get("publishers") else "",
        "published_at": published_at,
        "description": _extract_description(data.get("description")),
        "cover_url": _openlibrary_cover(data.get("covers", [None])[0]),
        "page_count": data.get("number_of_pages"),
        "isbn13": isbn13 or "",
        "isbn10": isbn10 or "",
    }


def _fetch_openlibrary_author(key: str) -> str:
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
    m = re.search(r"\d{4}", value or "")
    return f"{m.group(0)}-01-01" if m else None


def _lookup_naver(isbn: str) -> dict[str, Any] | None:
    client_id = os.environ.get("BOOK_HUB_NAVER_CLIENT_ID")
    client_secret = os.environ.get("BOOK_HUB_NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    url = "https://openapi.naver.com/v1/search/book.json"
    try:
        resp = requests.get(
            url,
            params={"query": isbn, "display": 1},
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None
        item = items[0]
    except Exception as exc:
        logger.warning("네이버 책 API 조회 실패: %s", exc)
        return None

    isbn_text = item.get("isbn", "")
    isbn13 = normalize_isbn(isbn_text) if len(normalize_isbn(isbn_text)) == 13 else ""
    isbn10 = normalize_isbn(isbn_text) if len(normalize_isbn(isbn_text)) == 10 else ""
    if not isbn13 and len(isbn) == 13:
        isbn13 = isbn
    if not isbn10 and len(isbn) == 10:
        isbn10 = isbn
    if isbn13 and not isbn10:
        isbn10 = isbn13_to_isbn10(isbn13) or ""
    if isbn10 and not isbn13:
        isbn13 = isbn10_to_isbn13(isbn10) or ""

    return {
        "title": item.get("title", "").replace("<b>", "").replace("</b>", ""),
        "authors": item.get("author", "").replace("<b>", "").replace("</b>", ""),
        "publisher": item.get("publisher", "").replace("<b>", "").replace("</b>", ""),
        "published_at": _parse_year(item.get("pubdate", "")),
        "description": item.get("description", ""),
        "cover_url": item.get("image", ""),
        "page_count": None,
        "isbn13": isbn13,
        "isbn10": isbn10,
    }


def _lookup_kakao(isbn: str) -> dict[str, Any] | None:
    api_key = os.environ.get("BOOK_HUB_KAKAO_REST_API_KEY")
    if not api_key:
        return None

    url = "https://dapi.kakao.com/v3/search/book"
    try:
        resp = requests.get(
            url,
            params={"query": isbn, "size": 1},
            headers={"Authorization": f"KakaoAK {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        documents = data.get("documents", [])
        if not documents:
            return None
        doc = documents[0]
    except Exception as exc:
        logger.warning("카카오 책 API 조회 실패: %s", exc)
        return None

    isbn_text = doc.get("isbn", "")
    parts = [normalize_isbn(p) for p in isbn_text.split(" ")]
    isbn13 = next((p for p in parts if len(p) == 13), "")
    isbn10 = next((p for p in parts if len(p) == 10), "")
    if not isbn13 and len(isbn) == 13:
        isbn13 = isbn
    if not isbn10 and len(isbn) == 10:
        isbn10 = isbn
    if isbn13 and not isbn10:
        isbn10 = isbn13_to_isbn10(isbn13) or ""
    if isbn10 and not isbn13:
        isbn13 = isbn10_to_isbn13(isbn10) or ""

    return {
        "title": doc.get("title", ""),
        "authors": ", ".join(doc.get("authors", [])),
        "publisher": doc.get("publisher", ""),
        "published_at": _parse_year(doc.get("datetime", "")),
        "description": doc.get("contents", ""),
        "cover_url": doc.get("thumbnail", ""),
        "page_count": None,
        "isbn13": isbn13,
        "isbn10": isbn10,
    }
