"""book_hub 모델.

데이터 범위:
- Book: 플랫폼(공용) — 누구나 볼 수 있는 책 메타데이터. ISBN 등으로 식별.
- BookTag: 플랫폼(공용) — 책 분류 태그.
- BookVerification: 플랫폼(공용) — 책에 대한 검증 자료. 누가(verifier) 추가했는지는
  기록되나, 자료 자체는 다른 플러그인이 근거로 삼을 수 있게 공개된다.
- PersonalBook: 개인 — 사용자가 실제로 소유/관리하는 책(전자책·실물책·오디오북).
  owner 로 격리하며, 같은 Book을 여러 사람이 각자의 서재에 담을 수 있다.

조회는 모델/뷰에서 owner 조건 또는 공개 조건을 명시한다.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Book(models.Model):
    """플랫폼(공용) 책 메타데이터."""

    class SourceType(models.TextChoices):
        EBOOK = "ebook", _("전자책")
        PHYSICAL = "physical", _("실물책")
        AUDIOBOOK = "audiobook", _("오디오북")
        UNKNOWN = "unknown", _("미상")

    title = models.CharField(_("제목"), max_length=255)
    subtitle = models.CharField(_("부제목"), max_length=255, blank=True)
    authors = models.CharField(_("저자"), max_length=500, blank=True)
    publisher = models.CharField(_("출판사"), max_length=200, blank=True)
    published_at = models.DateField(_("출판일"), null=True, blank=True)
    isbn13 = models.CharField(_("ISBN-13"), max_length=13, blank=True, db_index=True)
    isbn10 = models.CharField(_("ISBN-10"), max_length=10, blank=True, db_index=True)
    description = models.TextField(_("설명"), blank=True)
    cover_url = models.URLField(_("표지 URL"), max_length=500, blank=True)
    page_count = models.PositiveIntegerField(_("페이지 수"), null=True, blank=True)
    language = models.CharField(_("언어"), max_length=10, blank=True, default="ko")
    category = models.CharField(_("카테고리"), max_length=100, blank=True)
    source_type = models.CharField(
        _("기본 형태"), max_length=10, choices=SourceType.choices, default=SourceType.UNKNOWN
    )
    verified = models.BooleanField(_("검증됨"), default=False, help_text=_("검증 자료가 있는 책"))
    tags = models.ManyToManyField("BookTag", blank=True, related_name="books")
    metadata = models.JSONField(_("추가 메타데이터"), default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("등록자"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("책")
        verbose_name_plural = _("책")
        ordering = ("title", "authors", "published_at")
        indexes = [
            models.Index(fields=("title",), name="book_hub_title_idx"),
            models.Index(fields=("authors",), name="book_hub_authors_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("isbn13",),
                name="book_hub_isbn13_uniq",
                condition=~models.Q(isbn13=""),
            ),
            models.UniqueConstraint(
                fields=("isbn10",),
                name="book_hub_isbn10_uniq",
                condition=~models.Q(isbn10=""),
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("book_hub:book_detail", args=[self.pk])

    def update_verified_flag(self) -> None:
        self.verified = self.verifications.exists()
        self.save(update_fields=["verified", "updated_at"])


class BookTag(models.Model):
    """플랫폼(공용) 책 태그."""

    name = models.CharField(_("태그명"), max_length=50, unique=True)
    description = models.CharField(_("설명"), max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("책 태그")
        verbose_name_plural = _("책 태그")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class BookVerification(models.Model):
    """플랫폼(공용) 검증 자료 — 다른 플러그인이 근거로 삼을 수 있는 출처·메모."""

    class Reliability(models.TextChoices):
        HIGH = "high", _("높음")
        MEDIUM = "medium", _("보통")
        LOW = "low", _("낮음")

    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="verifications", verbose_name=_("책")
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("검증자"),
    )
    source_url = models.URLField(_("출처 URL"), max_length=1000, blank=True)
    source_title = models.CharField(_("출처 제목"), max_length=255, blank=True)
    reliability = models.CharField(
        _("신뢰도"), max_length=10, choices=Reliability.choices, default=Reliability.MEDIUM
    )
    notes = models.TextField(_("메모"), blank=True)
    verified_at = models.DateTimeField(_("검증 시각"), auto_now_add=True)

    class Meta:
        verbose_name = _("책 검증 자료")
        verbose_name_plural = _("책 검증 자료")
        ordering = ("-verified_at",)

    def __str__(self) -> str:
        return f"{self.book.title} 검증 자료"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.book.update_verified_flag()


class PersonalBook(models.Model):
    """개인 — 사용자가 실제로 관리하는 책 인스턴스."""

    class Status(models.TextChoices):
        WISHLIST = "wishlist", _("읽고 싶음")
        READING = "reading", _("읽는 중")
        COMPLETED = "completed", _("완독")
        DROPPED = "dropped", _("하차")

    class Format(models.TextChoices):
        EBOOK = "ebook", _("전자책")
        PHYSICAL = "physical", _("실물책")
        AUDIOBOOK = "audiobook", _("오디오북")

    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="personal_copies", verbose_name=_("책")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_books",
        verbose_name=_("소유자"),
    )
    format = models.CharField(
        _("형태"), max_length=10, choices=Format.choices, default=Format.PHYSICAL
    )
    status = models.CharField(
        _("상태"), max_length=10, choices=Status.choices, default=Status.WISHLIST
    )
    location = models.CharField(
        _("보관 위치/경로"),
        max_length=500,
        blank=True,
        help_text=_("실물 위치 또는 전자책 파일 경로/URI"),
    )
    purchase_source = models.CharField(_("구매처"), max_length=200, blank=True)
    purchase_price = models.DecimalField(
        _("구매 가격"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    purchase_currency = models.CharField(_("통화"), max_length=3, default="KRW")
    purchased_at = models.DateField(_("구매일"), null=True, blank=True)
    rating = models.PositiveSmallIntegerField(
        _("평점"), null=True, blank=True, help_text=_("1~5점")
    )
    review = models.TextField(_("리뷰"), blank=True)
    progress_page = models.PositiveIntegerField(_("현재 페이지"), null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(
        _("진행률(%)"), null=True, blank=True
    )
    is_public = models.BooleanField(
        _("공개"), default=False, help_text=_("다른 플러그인이 이 복사본을 볼 수 있게 허용")
    )
    started_at = models.DateField(_("시작일"), null=True, blank=True)
    completed_at = models.DateField(_("완료일"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("내 책")
        verbose_name_plural = _("내 책")
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("book", "owner", "format"),
                name="book_hub_personalbook_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.owner.username}의 {self.book.title} ({self.get_format_display()})"

    def get_absolute_url(self) -> str:
        return reverse("book_hub:personalbook_list")

    def save(self, *args, **kwargs):
        if self.rating and not (1 <= self.rating <= 5):
            raise ValueError("평점은 1~5 사이여야 합니다.")
        super().save(*args, **kwargs)
