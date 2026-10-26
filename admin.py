from django.contrib import admin

from .models import Book, BookTag, BookVerification, PersonalBook


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "authors", "publisher", "source_type", "verified", "created_at")
    list_filter = ("source_type", "verified", "language", "created_at")
    search_fields = ("title", "authors", "isbn13", "isbn10", "publisher")
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(BookTag)
class BookTagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(BookVerification)
class BookVerificationAdmin(admin.ModelAdmin):
    list_display = ("book", "reliability", "verifier", "source_title", "verified_at")
    list_filter = ("reliability", "verified_at")
    search_fields = ("book__title", "source_title", "notes")
    readonly_fields = ("verified_at",)


@admin.register(PersonalBook)
class PersonalBookAdmin(admin.ModelAdmin):
    list_display = ("book", "owner", "format", "status", "rating", "updated_at")
    list_filter = ("format", "status", "created_at")
    search_fields = ("book__title", "owner__username", "location")
    readonly_fields = ("created_at", "updated_at")
