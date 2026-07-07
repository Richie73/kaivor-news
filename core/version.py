"""
Kaivor Version Information
"""


class Version:
    """Kaivor version information."""

    NAME = "Kaivor"

    VERSION = "0.9.5"

    CODENAME = "Hermes"

    STATUS = "Development"

    BUILD = "KR-038"

    @classmethod
    def full(cls):
        """Return the full version string."""

        return (
            f"{cls.NAME} "
            f"v{cls.VERSION} "
            f"({cls.CODENAME})"
        )
