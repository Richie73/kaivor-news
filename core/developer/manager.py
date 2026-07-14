"""
Kaivor Developer Manager
"""

from core.developer.dashboard import DeveloperDashboard
from core.developer.doctor import DeveloperDoctor
from core.developer.build import BuildManager


class DeveloperManager:
    """Developer Mode controller."""

    def __init__(self):

        self.dashboard = DeveloperDashboard()
        self.doctor = DeveloperDoctor()
        self.build = BuildManager()

    def dashboard_view(self):
        self.dashboard.show()

    def doctor_check(self):
        self.doctor.run()

    def build_project(self):
        self.build.run()
