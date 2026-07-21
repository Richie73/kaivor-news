"""
Kaivor Developer Manager
"""

from core.developer.dashboard import DeveloperDashboard
from core.developer.doctor import DeveloperDoctor
from core.developer.build import BuildManager
from core.developer.snapshot import DeveloperSnapshot
from core.developer.status import DeveloperStatus
from core.developer.menu import DeveloperMenu
from core.developer.help import DeveloperHelp

class DeveloperManager:
    """Developer Mode controller."""

    def __init__(self):

        self.dashboard = DeveloperDashboard()
        self.doctor = DeveloperDoctor()
        self.build = BuildManager()
        self.snapshot = DeveloperSnapshot()
        self.status = DeveloperStatus()
        self.menu = DeveloperMenu(self)
        self.help = DeveloperHelp()

    def dashboard_view(self):
        self.dashboard.show()

    def doctor_check(self):
        self.doctor.run()

    def build_project(self):
        self.build.run()

    def snapshot_project(self):
        self.snapshot.run()

    def project_status(self):
        self.status.run()

    def run(self):
        self.menu.run()

    def developer_help(self):
        self.help.run()
