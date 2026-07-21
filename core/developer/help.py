"""
Developer Help
"""


class DeveloperHelp:
    """Displays Developer Mode help."""

    def run(self):

        print()
        print("=" * 60)
        print("DEVELOPER HELP")
        print("=" * 60)
        print()

        commands = [
            ("dashboard", "Show developer dashboard"),
            ("doctor", "Run project health checks"),
            ("build", "Compile every Python file"),
            ("snapshot", "Create Kaivor snapshot ZIP"),
            ("status", "Display project status"),
            ("help", "Show this help"),
            ("exit", "Return to Kaivor"),
        ]

        for command, description in commands:
            print(f"{command:<12} {description}")

        print()
