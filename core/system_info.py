"""
Kaivor System Information
"""

import platform
import sys

from core.version import Version


class SystemInfo:
    """Provides system information."""

    def info(self):
        """Return system information."""

        return {
            "name": Version.NAME,
            "version": Version.VERSION,
            "codename": Version.CODENAME,
            "status": Version.STATUS,
            "build": Version.BUILD,
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "architecture": platform.machine(),
        }
