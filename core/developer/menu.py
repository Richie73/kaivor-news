"""
Developer Menu
"""


class DeveloperMenu:
    """Interactive Developer Menu."""

    def __init__(self, manager):
        self.manager = manager

    def run(self):

        actions = {
            "1": self.manager.dashboard_view,
            "dashboard": self.manager.dashboard_view,
            "2": self.manager.doctor_check,
            "doctor": self.manager.doctor_check,
            "3": self.manager.build_project,
            "build": self.manager.build_project,
            "4": self.manager.snapshot_project,
            "snapshot": self.manager.snapshot_project,
            "5": self.manager.project_status,
            "status": self.manager.project_status,
        }

        while True:

            print()
            print("=" * 60)
            print("KAIVOR DEVELOPER MODE")
            print("=" * 60)
            print()
            print("1. Dashboard")
            print("2. Doctor")
            print("3. Build")
            print("4. Snapshot")
            print("5. Status")
            print("0. Exit")
            print()

            choice = input("Developer> ").strip().lower()

            if choice in ("0", "exit", "quit", "back"):
                break

            action = actions.get(choice)

            if action:
                action()
            else:
                print()
                print("Unknown command.")
                print("Try: 1-5, dashboard, doctor, build, snapshot, status, exit")
