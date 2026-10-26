"""북 허브 화면 — 책 메타데이터 관리, 개인 서재, 검증 자료."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
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

logger = logging.getLogger(__name__)


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
            "recent_books": Book.objects.order_by("-created_at")[:5],
            "recent_verifications": BookVerification.objects.order_by("-verified_at")[:5],
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
        return ctx


class BookCreateView(LoginRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "book_hub/book_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "책을 등록했습니다.")
        return super().form_valid(form)


class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "book_hub/book_form.html"

    def form_valid(self, form):
        messages.success(self.request, "책 정보를 수정했습니다.")
        return super().form_valid(form)


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
    template_name = "book_hub/book_form.html"

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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "내 서재에 추가"
        if self.book:
            ctx["book"] = self.book
        return ctx


class PersonalBookUpdateView(LoginRequiredMixin, UpdateView):
    model = PersonalBook
    form_class = PersonalBookForm
    template_name = "book_hub/book_form.html"

    def get_queryset(self):
        return PersonalBook.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "내 책 정보를 수정했습니다.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("book_hub:personalbook_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"'{self.object.book.title}' 수정"
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


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "book_hub/settings.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["config"] = {}
        try:
            from plugin_system.utils import get_plugin_config

            ctx["config"] = get_plugin_config("book_hub", default={})
        except Exception:
            pass
        return ctx
