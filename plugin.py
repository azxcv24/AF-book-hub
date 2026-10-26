"""북 허브 — 전자책·실물책·오디오북 등 모든 책을 관리하고 검증 자료를 제공한다.

다른 플러그인이 "이 책을 근거로 삼아도 되는가"를 확인할 수 있도록
Book(메타데이터) + BookVerification(검증 자료)를 중심에 둔다.
"""
from __future__ import annotations

import logging

from django.urls import reverse

from plugin_system.base import BasePlugin, DashboardCard, NavItem

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    identifier = "book_hub"
    name = "북 허브"
    description = (
        "전자책·실물책·오디오북을 한 곳에서 관리하고, "
        "다른 플러그인이 신뢰할 수 있는 검증 자료로 활용할 수 있게 한다."
    )
    version = "0.1.0"
    category = "productivity"
    author = "AlphaFlow"
    icon = "bi-book"

    def get_default_config(self):
        return {
            "default_currency": "KRW",
            "enable_isbn_lookup": True,
            "lookup_provider": "openlibrary",  # openlibrary, naver, kakao
        }

    def get_nav_items(self, request):
        if not request.user.is_authenticated:
            return []
        badge = None
        try:
            from .models import PersonalBook

            reading = PersonalBook.objects.filter(
                owner=request.user, status=PersonalBook.Status.READING
            ).count()
            badge = str(reading) if reading else None
        except Exception:  # 마이그레이션 전 등
            pass
        return [
            NavItem(
                order=10,
                label="북 허브",
                url=reverse("book_hub:dashboard"),
                icon="bi-book",
            ),
            NavItem(
                order=11,
                label="내 서재",
                url=reverse("book_hub:personalbook_list"),
                icon="bi-bookshelf",
                badge=badge,
            ),
            NavItem(
                order=12,
                label="책 찾기",
                url=reverse("book_hub:book_list"),
                icon="bi-search",
            ),
            NavItem(
                order=13,
                label="검증 자료",
                url=reverse("book_hub:verification_list"),
                icon="bi-shield-check",
            ),
            NavItem(
                order=20,
                label="설정",
                url=reverse("book_hub:settings"),
                icon="bi-gear",
                kind="settings",
            ),
        ]

    def get_dashboard_cards(self, request):
        if not request.user.is_authenticated:
            return []
        context = {
            "detail_url": reverse("book_hub:dashboard"),
            "personal_url": reverse("book_hub:personalbook_list"),
            "books_url": reverse("book_hub:book_list"),
        }
        try:
            from .models import Book, PersonalBook

            user = request.user
            context.update({
                "total_books": Book.objects.count(),
                "my_books": PersonalBook.objects.filter(owner=user).count(),
                "reading": PersonalBook.objects.filter(
                    owner=user, status=PersonalBook.Status.READING
                ).count(),
                "completed": PersonalBook.objects.filter(
                    owner=user, status=PersonalBook.Status.COMPLETED
                ).count(),
                "wishlist": PersonalBook.objects.filter(
                    owner=user, status=PersonalBook.Status.WISHLIST
                ).count(),
            })
        except Exception:
            logger.debug("book_hub: 대시보드 카드 컨텍스트 생략")
        return [
            DashboardCard(
                order=15,
                title="북 허브",
                template_name="book_hub/cards/summary.html",
                context=context,
                width=4,
            )
        ]

    def get_urls(self):
        from . import urls

        return urls.urlpatterns

    def get_agent_tools(self):
        """LLM 에이전트가 책 정보를 검색·확인할 수 있는 도구."""
        return [
            {
                "name": "book_hub__search_books",
                "title": "책 검색",
                "description": (
                    "제목·저자·ISBN·키워드로 책 메타데이터를 검색한다. "
                    "다른 플러그인이 근거 자료를 찾을 때 사용."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "제목·저자·ISBN·키워드"},
                        "limit": {"type": "integer", "default": 10},
                        "verified_only": {"type": "boolean", "default": False},
                    },
                    "required": ["query"],
                },
                "handler": _tool_search_books,
                "side_effect": False,
                "danger": "safe",
            },
            {
                "name": "book_hub__get_book",
                "title": "책 상세 조회",
                "description": (
                    "book_id로 책 상세 정보와 검증 자료를 돌려준다. "
                    "다른 플러그인이 '이 책이 맞는지' 확인할 때 사용."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "book_id": {"type": "integer"},
                        "isbn": {"type": "string"},
                    },
                },
                "handler": _tool_get_book,
                "side_effect": False,
                "danger": "safe",
            },
            {
                "name": "book_hub__add_verification",
                "title": "책 검증 자료 추가",
                "description": (
                    "책에 대한 신뢰할 수 있는 출처·메모·평가를 추가한다. "
                    "'이 책을 근거로 써도 되는가'를 뒷받침하는 자료."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "book_id": {"type": "integer"},
                        "source_url": {"type": "string"},
                        "source_title": {"type": "string"},
                        "reliability": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "default": "medium",
                        },
                        "notes": {"type": "string"},
                    },
                    "required": ["book_id"],
                },
                "handler": _tool_add_verification,
                "side_effect": True,
                "danger": "caution",
            },
        ]


def _tool_user(context):
    user = getattr(context, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return user


def _need_user():
    return {"error": "로그인 사용자 컨텍스트가 없습니다(에이전트 소유자를 확인하세요)."}


def _tool_search_books(arguments, context):
    from django.db.models import Q

    from .models import Book

    args = arguments or {}
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query 가 필요합니다."}
    limit = max(1, min(50, int(args.get("limit") or 10)))
    verified_only = bool(args.get("verified_only", False))

    qs = Book.objects.all()
    if verified_only:
        qs = qs.filter(verified=True)
    qs = qs.filter(
        Q(title__icontains=query)
        | Q(authors__icontains=query)
        | Q(isbn13__icontains=query)
        | Q(isbn10__icontains=query)
        | Q(publisher__icontains=query)
    )
    items = []
    for book in qs.distinct().order_by("title")[:limit]:
        items.append({
            "id": book.pk,
            "title": book.title,
            "authors": book.authors,
            "publisher": book.publisher,
            "published_at": book.published_at,
            "isbn13": book.isbn13,
            "isbn10": book.isbn10,
            "verified": book.verified,
            "source_type": book.source_type,
            "detail_url": f"/plugins/book_hub/books/{book.pk}/",
        })
    return {"query": query, "count": len(items), "items": items}


def _tool_get_book(arguments, context):
    from .models import Book

    args = arguments or {}
    book_id = args.get("book_id")
    isbn = str(args.get("isbn") or "").strip()
    book = None
    if book_id:
        book = Book.objects.filter(pk=book_id).first()
    elif isbn:
        book = Book.objects.filter(isbn13=isbn).first() or Book.objects.filter(
            isbn10=isbn
        ).first()
    if book is None:
        return {"error": "책을 찾을 수 없습니다."}
    verifications = [
        {
            "id": v.pk,
            "source_title": v.source_title,
            "source_url": v.source_url,
            "reliability": v.reliability,
            "notes": v.notes,
            "verified_at": v.verified_at,
            "verifier": v.verifier.username if v.verifier else None,
        }
        for v in book.verifications.order_by("-verified_at")
    ]
    return {
        "id": book.pk,
        "title": book.title,
        "authors": book.authors,
        "publisher": book.publisher,
        "published_at": book.published_at,
        "description": book.description,
        "isbn13": book.isbn13,
        "isbn10": book.isbn10,
        "page_count": book.page_count,
        "language": book.language,
        "category": book.category,
        "source_type": book.source_type,
        "verified": book.verified,
        "verifications": verifications,
        "detail_url": f"/plugins/book_hub/books/{book.pk}/",
    }


def _tool_add_verification(arguments, context):
    from .models import Book, BookVerification

    user = _tool_user(context)
    if user is None:
        return _need_user()
    args = arguments or {}
    book_id = args.get("book_id")
    if not book_id:
        return {"error": "book_id 가 필요합니다."}
    book = Book.objects.filter(pk=book_id).first()
    if book is None:
        return {"error": "책을 찾을 수 없습니다."}
    verification = BookVerification.objects.create(
        book=book,
        verifier=user,
        source_url=str(args.get("source_url") or ""),
        source_title=str(args.get("source_title") or ""),
        reliability=str(args.get("reliability") or "medium"),
        notes=str(args.get("notes") or ""),
    )
    return {
        "ok": True,
        "id": verification.pk,
        "book_id": book.pk,
        "reliability": verification.reliability,
    }
