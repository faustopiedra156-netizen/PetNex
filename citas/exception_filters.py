import re

from django.views.debug import SafeExceptionReporterFilter


class PetNexoExceptionReporterFilter(SafeExceptionReporterFilter):
    """Hide connection strings and provider credentials in error reports."""

    hidden_settings = re.compile(
        r"API|AUTH|TOKEN|KEY|SECRET|PASS|SIGNATURE|HTTP_COOKIE|DATABASE_URL|"
        r"REDIS_URL|SENTRY_DSN",
        flags=re.IGNORECASE,
    )
