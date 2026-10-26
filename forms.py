from django import forms

from .models import Book, BookVerification, PersonalBook


class BookForm(forms.ModelForm):
    """책 메타데이터 등록/수정 폼."""

    class Meta:
        model = Book
        fields = [
            "title",
            "subtitle",
            "authors",
            "publisher",
            "published_at",
            "isbn13",
            "isbn10",
            "description",
            "cover_url",
            "page_count",
            "language",
            "category",
            "source_type",
            "tags",
        ]
        widgets = {
            "published_at": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class BookSearchForm(forms.Form):
    """책 검색 폼."""

    q = forms.CharField(label="검색어", max_length=100, required=False)
    source_type = forms.ChoiceField(
        label="형태",
        choices=[("", "전체")] + list(Book.SourceType.choices),
        required=False,
    )
    verified_only = forms.BooleanField(label="검증된 책만", required=False)


class PersonalBookForm(forms.ModelForm):
    """개인 서재 등록/수정 폼."""

    book = forms.ModelChoiceField(
        queryset=Book.objects.order_by("title"),
        label="책",
        required=False,
    )

    def __init__(self, *args, book_given=False, **kwargs):
        super().__init__(*args, **kwargs)
        if book_given:
            self.fields["book"].disabled = True
        else:
            self.fields["book"].required = True

    class Meta:
        model = PersonalBook
        fields = [
            "book",
            "format",
            "status",
            "location",
            "purchase_source",
            "purchase_price",
            "purchase_currency",
            "purchased_at",
            "rating",
            "review",
            "progress_page",
            "progress_percent",
            "is_public",
            "started_at",
            "completed_at",
        ]
        widgets = {
            "purchased_at": forms.DateInput(attrs={"type": "date"}),
            "started_at": forms.DateInput(attrs={"type": "date"}),
            "completed_at": forms.DateInput(attrs={"type": "date"}),
            "review": forms.Textarea(attrs={"rows": 4}),
        }


class BookVerificationForm(forms.ModelForm):
    """책 검증 자료 추가 폼."""

    class Meta:
        model = BookVerification
        fields = ["source_url", "source_title", "reliability", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
