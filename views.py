"""북 허브 화면 — 책 메타데이터 관리, 개인 서재, 검증 자료, 공개 API."""
from __future__ import annotations

import csv
import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    BookForm,
    BookSearchForm,
    BookVerificationForm,
    PersonalBookForm,
)
from .models import Book, BookVerification, PersonalBook
from .services import metadata

logger = logging.getLogger(__name__)


def _file_hub_picker_url():
    """file_hub picker URL 반환(설치된 경우)."""
    try:
        from django.urls import reverse
        return reverse("file_hub:picker")
    except Exception:
        return None


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "book_hub/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx.update({
            "book_count": Book.objects.count(),
            "verified_count": Book.objects.filter(verified=True).count(),
            "my_count": PersonalBook.objects.filter(owner=user).count(),
            "reading_count": PersonalBook.objects.filter(
                owner=user, status=PersonalBook.Status.READING
            ).count(),
            "completed_count": PersonalBook.objects.filter(
                owner=user, status=PersonalBook.Status.COMPLETED
            ).count(),
            "wishlist_count": PersonalBook.objects.filter(
                owner=user, status=PersonalBook.Status.WISHLIST
            ).count(),
            "dropped_count": PersonalBook.objects.filter(
                owner=user, status=PersonalBook.Status.DROPPED
            ).count(),
            "recent_books": Book.objects.order_by("-created_at")[:5],
            "recent_verifications": BookVerification.objects.order_by("-verified_at")[:5],
            "top_verified": Book.objects.filter(verified=True).order_by("-updated_at")[:5],
        })
        return ctx


class BookListView(LoginRequiredMixin, ListView):
    model = Book
    template_name = "book_hub/book_list.html"
    paginate_by = 20
    context_object_name = "books"

    def get_queryset(self):
        qs = Book.objects.prefetch_related("tags").all()
        form = BookSearchForm(self.request.GET or None)
        if form.is_valid():
            data = form.cleaned_data
            q = data.get("q")
            if q:
                qs = qs.filter(
                    Q(title__icontains=q)
                    | Q(authors__icontains=q)
                    | Q(isbn13__icontains=q)
                    | Q(isbn10__icontains=q)
                    | Q(publisher__icontains=q)
                )
            if data.get("source_type"):
                qs = qs.filter(source_type=data["source_type"])
            if data.get("verified_only"):
                qs = qs.filter(verified=True)
        return qs.order_by("title")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = BookSearchForm(self.request.GET or None)
        return ctx


class BookCSVExportView(LoginRequiredMixin, View):
    """GET /books/export/ — 등록된 책 목록을 CSV로 낼 수 있다."""

    def get(self, request):
        qs = Book.objects.prefetch_related("tags").all()
        form = BookSearchForm(request.GET or None)
        if form.is_valid():
            data = form.cleaned_data
            q = data.get("q")
            if q:
                qs = qs.filter(
                    Q(title__icontains=q)
                    | Q(authors__icontains=q)
                    | Q(isbn13__icontains=q)
                    | Q(isbn10__icontains=q)
                    | Q(publisher__icontains=q)
                )
            if data.get("source_type"):
                qs = qs.filter(source_type=data["source_type"])
            if data.get("verified_only"):
                qs = qs.filter(verified=True)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="books.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "id", "title", "subtitle", "authors", "publisher", "published_at",
            "isbn13", "isbn10", "page_count", "language", "category",
            "source_type", "verified", "tags", "description",
        ])
        for book in qs.order_by("title"):
            writer.writerow([
                book.pk,
                book.title,
                book.subtitle,
                book.authors,
                book.publisher,
                book.published_at,
                book.isbn13,
                book.isbn10,
                book.page_count,
                book.language,
                book.category,
                book.source_type,
                "1" if book.verified else "0",
                ", ".join(t.name for t in book.tags.all()),
                book.description,
            ])
        return response


class BookDetailView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = "book_hub/book_detail.html"
    context_object_name = "book"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        book = self.object
        ctx["verifications"] = book.verifications.order_by("-verified_at")
        ctx["personal_copy"] = PersonalBook.objects.filter(
            book=book, owner=self.request.user
        ).first()
        ctx["picker_url"] = _file_hub_picker_url()
        ctx["status_choices"] = PersonalBook.Status.choices
        ctx["format_choices"] = PersonalBook.Format.choices
        return ctx


class BookCreateView(LoginRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "book_hub/book_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "책을 등록했습니다.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "책 등록"
        ctx["picker_url"] = _file_hub_picker_url()
        return ctx


class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "book_hub/book_form.html"

    def form_valid(self, form):
        messages.success(self.request, "책 정보를 수정했습니다.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"'{self.object.title}' 수정"
        ctx["picker_url"] = _file_hub_picker_url()
        return ctx


class BookVerificationCreateView(LoginRequiredMixin, CreateView):
    model = BookVerification
    form_class = BookVerificationForm
    template_name = "book_hub/book_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.book = get_object_or_404(Book, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.book = self.book
        form.instance.verifier = self.request.user
        messages.success(self.request, "검증 자료를 추가했습니다.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("book_hub:book_detail", args=[self.book.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["book"] = self.book
        ctx["title"] = f"'{self.book.title}' 검증 자료 추가"
        return ctx


class VerificationListView(LoginRequiredMixin, ListView):
    model = BookVerification
    template_name = "book_hub/verification_list.html"
    paginate_by = 20
    context_object_name = "verifications"

    def get_queryset(self):
        return BookVerification.objects.select_related("book", "verifier").order_by("-verified_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        total = BookVerification.objects.count()
        high = BookVerification.objects.filter(reliability=BookVerification.Reliability.HIGH).count()
        medium = BookVerification.objects.filter(reliability=BookVerification.Reliability.MEDIUM).count()
        low = BookVerification.objects.filter(reliability=BookVerification.Reliability.LOW).count()
        ctx["stats"] = {"total": total, "high": high, "medium": medium, "low": low}
        return ctx


class PersonalBookListView(LoginRequiredMixin, ListView):
    model = PersonalBook
    template_name = "book_hub/personalbook_list.html"
    paginate_by = 20
    context_object_name = "personal_books"

    def get_queryset(self):
        return PersonalBook.objects.filter(owner=self.request.user).select_related("book")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["status_counts"] = [
            {
                "key": status.value,
                "label": status.label,
                "count": PersonalBook.objects.filter(owner=user, status=status.value).count(),
            }
            for status in PersonalBook.Status
        ]
        return ctx


class PersonalBookCreateView(LoginRequiredMixin, CreateView):
    model = PersonalBook
    form_class = PersonalBookForm
    template_name = "book_hub/personalbook_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.book = None
        book_id = self.request.GET.get("book") or self.request.POST.get("book")
        if book_id:
            self.book = get_object_or_404(Book, pk=book_id)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.owner = self.request.user
        if self.book:
            form.instance.book = self.book
        try:
            return super().form_valid(form)
        except Exception as exc:
            messages.error(self.request, f"저장하지 못했습니다: {exc}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("book_hub:personalbook_list")

    def get_initial(self):
        initial = super().get_initial()
        if self.book:
            initial["book"] = self.book
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["book_given"] = self.book is not None
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "내 서재에 추가"
        ctx["picker_url"] = _file_hub_picker_url()
        if self.book:
            ctx["book"] = self.book
        return ctx


class PersonalBookUpdateView(LoginRequiredMixin, UpdateView):
    model = PersonalBook
    form_class = PersonalBookForm
    template_name = "book_hub/personalbook_form.html"

    def get_queryset(self):
        return PersonalBook.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["book_given"] = True
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "내 책 정보를 수정했습니다.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("book_hub:personalbook_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"'{self.object.book.title}' 수정"
        ctx["picker_url"] = _file_hub_picker_url()
        return ctx


class PersonalBookDeleteView(LoginRequiredMixin, DeleteView):
    model = PersonalBook
    template_name = "book_hub/confirm_delete.html"
    success_url = reverse_lazy("book_hub:personalbook_list")

    def get_queryset(self):
        return PersonalBook.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.info(request, "내 서재에서 제거했습니다.")
        return super().delete(request, *args, **kwargs)


class PersonalBookStatusUpdateView(LoginRequiredMixin, View):
    """UI용 내 책 상태/진행률 빠른 변경."""

    def post(self, request, pk):
        pb = get_object_or_404(PersonalBook.objects.filter(owner=request.user), pk=pk)
        status = request.POST.get("status")
        progress = request.POST.get("progress_percent")
        if status and status in dict(PersonalBook.Status.values):
            pb.status = status
            if status == PersonalBook.Status.COMPLETED:
                pb.progress_percent = 100
        if progress is not None:
            try:
                pb.progress_percent = max(0, min(100, int(progress)))
            except ValueError:
                pass
        pb.save()
        messages.success(request, "상태를 업데이트했습니다.")
        return redirect(request.POST.get("next") or "book_hub:personalbook_list")


class SettingsView(LoginRequiredMixin, View):
    """북 허브 설정 — plugin_system.Plugin.config JSON을 편집."""

    template_name = "book_hub/settings.html"

    def get(self, request):
        ctx = {"config": self._get_config()}
        return render(request, self.template_name, ctx)

    def post(self, request):
        config = self._get_config()
        config["default_currency"] = (request.POST.get("default_currency") or "KRW").upper()
        config["enable_isbn_lookup"] = request.POST.get("enable_isbn_lookup") == "on"
        config["lookup_provider"] = request.POST.get("lookup_provider") or "openlibrary"
        self._save_config(config)
        messages.success(request, "설정을 저장했습니다.")
        return redirect("book_hub:settings")

    def _get_config(self):
        try:
            from plugin_system.utils import get_plugin_config
            return get_plugin_config("book_hub", default={})
        except Exception:
            return {}

    def _save_config(self, config):
        from plugin_system.models import Plugin as PluginModel
        obj = PluginModel.objects.get(identifier="book_hub")
        obj.config = config
        obj.save(update_fields=["config"])


# =============================================================================
# API (다른 플러그인 / 에이전트 / 외부 연동용)
# =============================================================================

class ISBNLookupAPIView(LoginRequiredMixin, View):
    """GET /api/isbn-lookup/?isbn=...&provider=openlibrary|naver|kakao"""

    def get(self, request):
        isbn = request.GET.get("isbn", "").strip()
        provider = request.GET.get("provider", "openlibrary").strip()
        if not isbn:
            return JsonResponse({"error": "isbn 파라미터가 필요합니다."}, status=400)
        result = metadata.lookup_isbn(isbn, provider=provider)
        if result is None:
            return JsonResponse({"error": "메타데이터를 찾을 수 없습니다."}, status=404)
        return JsonResponse({"ok": True, "data": result})


class BookListAPIView(LoginRequiredMixin, View):
    """GET /api/books/?q=...&verified_only=1&source_type=..."""

    def get(self, request):
        qs = Book.objects.prefetch_related("tags").all()
        q = request.GET.get("q", "").strip()
        verified_only = request.GET.get("verified_only") in ("1", "true", "on")
        source_type = request.GET.get("source_type", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(authors__icontains=q)
                | Q(isbn13__icontains=q)
                | Q(isbn10__icontains=q)
                | Q(publisher__icontains=q)
            )
        if verified_only:
            qs = qs.filter(verified=True)
        if source_type:
            qs = qs.filter(source_type=source_type)

        limit = min(100, max(1, int(request.GET.get("limit", 20))))
        items = []
        for book in qs.order_by("title")[:limit]:
            items.append(_book_to_dict(book))
        return JsonResponse({"count": len(items), "items": items})


class BookDetailAPIView(LoginRequiredMixin, View):
    """GET /api/books/<pk>/"""

    def get(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        data = _book_to_dict(book, include_verifications=True)
        return JsonResponse(data)


class BookVerifyAPIView(LoginRequiredMixin, View):
    """POST /api/books/<pk>/verify/ — 검증 자료 추가."""

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON 바디가 필요합니다."}, status=400)

        reliability = body.get("reliability", "medium")
        if reliability not in dict(BookVerification.Reliability.values):
            return JsonResponse({"error": "유효하지 않은 reliability 값입니다."}, status=400)

        verification = BookVerification.objects.create(
            book=book,
            verifier=request.user,
            source_url=str(body.get("source_url", ""))[:1000],
            source_title=str(body.get("source_title", ""))[:255],
            reliability=reliability,
            notes=str(body.get("notes", ""))[:2000],
        )
        return JsonResponse({
            "ok": True,
            "id": verification.pk,
            "book_id": book.pk,
            "reliability": verification.reliability,
        })


class AddToLibraryAPIView(LoginRequiredMixin, View):
    """POST /api/books/<pk>/add-to-library/ — 내 서재에 담기."""

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}
        fmt = body.get("format", PersonalBook.Format.PHYSICAL)
        if fmt not in dict(PersonalBook.Format.values):
            return JsonResponse({"error": "유효하지 않은 format 값입니다."}, status=400)

        pb, created = PersonalBook.objects.get_or_create(
            book=book,
            owner=request.user,
            format=fmt,
            defaults={"status": body.get("status", PersonalBook.Status.WISHLIST)},
        )
        if not created:
            return JsonResponse({"ok": True, "id": pb.pk, "created": False})
        return JsonResponse({"ok": True, "id": pb.pk, "created": True})


class MyBookStatusAPIView(LoginRequiredMixin, View):
    """POST /api/my-books/<pk>/status/ — 내 책 상태/진행률 변경."""

    def post(self, request, pk):
        pb = get_object_or_404(PersonalBook.objects.filter(owner=request.user), pk=pk)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            body = {}
        status = body.get("status")
        if status and status in dict(PersonalBook.Status.values):
            pb.status = status
            if status == PersonalBook.Status.COMPLETED:
                pb.progress_percent = 100
        progress = body.get("progress_percent")
        if progress is not None:
            try:
                pb.progress_percent = max(0, min(100, int(progress)))
            except ValueError:
                pass
        pb.save()
        return JsonResponse({"ok": True, "id": pb.pk, "status": pb.status, "progress_percent": pb.progress_percent})


def _book_to_dict(book: Book, include_verifications: bool = False) -> dict:
    data = {
        "id": book.pk,
        "title": book.title,
        "subtitle": book.subtitle,
        "authors": book.authors,
        "publisher": book.publisher,
        "published_at": book.published_at.isoformat() if book.published_at else None,
        "isbn13": book.isbn13,
        "isbn10": book.isbn10,
        "description": book.description,
        "cover_url": book.cover_url,
        "page_count": book.page_count,
        "language": book.language,
        "category": book.category,
        "source_type": book.source_type,
        "verified": book.verified,
        "tags": [t.name for t in book.tags.all()],
        "created_at": book.created_at.isoformat(),
        "updated_at": book.updated_at.isoformat(),
        "detail_url": f"/plugins/book_hub/books/{book.pk}/",
    }
    if include_verifications:
        data["verifications"] = [
            {
                "id": v.pk,
                "source_title": v.source_title,
                "source_url": v.source_url,
                "reliability": v.reliability,
                "notes": v.notes,
                "verified_at": v.verified_at.isoformat(),
            }
            for v in book.verifications.order_by("-verified_at")
        ]
    return data
