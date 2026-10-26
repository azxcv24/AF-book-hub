from django.urls import path

from . import views

app_name = "book_hub"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("books/", views.BookListView.as_view(), name="book_list"),
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
    path("settings/", views.SettingsView.as_view(), name="settings"),
]
