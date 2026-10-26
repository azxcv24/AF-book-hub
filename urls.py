from django.urls import path

from . import views

app_name = "book_hub"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("books/", views.BookListView.as_view(), name="book_list"),
    path("books/export/", views.BookCSVExportView.as_view(), name="book_export"),
    path("books/create/", views.BookCreateView.as_view(), name="book_create"),
    path("books/<int:pk>/", views.BookDetailView.as_view(), name="book_detail"),
    path("books/<int:pk>/edit/", views.BookUpdateView.as_view(), name="book_update"),
    path(
        "books/<int:pk>/verify/",
        views.BookVerificationCreateView.as_view(),
        name="book_verify",
    ),
    path("my/", views.PersonalBookListView.as_view(), name="personalbook_list"),
    path("my/add/", views.PersonalBookCreateView.as_view(), name="personalbook_create"),
    path(
        "my/<int:pk>/edit/",
        views.PersonalBookUpdateView.as_view(),
        name="personalbook_update",
    ),
    path(
        "my/<int:pk>/delete/",
        views.PersonalBookDeleteView.as_view(),
        name="personalbook_delete",
    ),
    path(
        "my/<int:pk>/status/",
        views.PersonalBookStatusUpdateView.as_view(),
        name="personalbook_status",
    ),
    path("verifications/", views.VerificationListView.as_view(), name="verification_list"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
    # API
    path("api/isbn-lookup/", views.ISBNLookupAPIView.as_view(), name="api_isbn_lookup"),
    path("api/books/", views.BookListAPIView.as_view(), name="api_book_list"),
    path("api/books/<int:pk>/", views.BookDetailAPIView.as_view(), name="api_book_detail"),
    path(
        "api/books/<int:pk>/verify/",
        views.BookVerifyAPIView.as_view(),
        name="api_book_verify",
    ),
    path(
        "api/books/<int:pk>/add-to-library/",
        views.AddToLibraryAPIView.as_view(),
        name="api_add_to_library",
    ),
    path(
        "api/my-books/<int:pk>/status/",
        views.MyBookStatusAPIView.as_view(),
        name="api_mybook_status",
    ),
]
