from django.apps import AppConfig


class BookHubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plugins.book_hub"
    label = "book_hub"
    verbose_name = "북 허브"
