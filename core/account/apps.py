from django.apps import AppConfig


class AccountConfig(AppConfig):
    """
    Configuration class for the Account application.
    """

    # Default primary key field type for models in this app
    default_auto_field = "django.db.models.BigAutoField"

    # Application label used by Django
    name = "account"

    def ready(self):
        """
        Import and register application signals.

        This method is called when the app is fully loaded.
        Importing signals here ensures they are registered
        without causing circular import issues.
        """
        from account import signals  # noqa: F401
