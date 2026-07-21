"""
Kaivor Project Verification Service
"""

from pathlib import Path


class ProjectVerification:
    """Checks the health of a Kaivor project."""

    REQUIRED_DIRECTORIES = [
        "core",
        "config",
        "modules",
        "docs",
        "tests",
        "data",
    ]

    REQUIRED_FILES = [
        "README.md",
        "requirements.txt",
        "kaivor.py",
    ]

    def __init__(self, project_root=None):
        if project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)

    def verify(self):
        """Run all verification checks."""

        report = {
            "directories": [],
            "files": [],
            "passed": True,
        }

        for directory in self.REQUIRED_DIRECTORIES:
            exists = (self.project_root / directory).exists()

            report["directories"].append(
                {
                    "name": directory,
                    "exists": exists,
                }
            )

            if not exists:
                report["passed"] = False

        for filename in self.REQUIRED_FILES:
            exists = (self.project_root / filename).exists()

            report["files"].append(
                {
                    "name": filename,
                    "exists": exists,
                }
            )

            if not exists:
                report["passed"] = False

        return report

    def print_report(self):
        """Display a readable report."""

        report = self.verify()

        print()
        print("=" * 40)
        print("KAIVOR PROJECT VERIFICATION")
        print("=" * 40)

        print("\nDirectories")

        for item in report["directories"]:
            status = "✓" if item["exists"] else "✗"
            print(f"{status} {item['name']}")

        print("\nFiles")

        for item in report["files"]:
            status = "✓" if item["exists"] else "✗"
            print(f"{status} {item['name']}")

        print()

        if report["passed"]:
            print("Project verification PASSED")
        else:
            print("Project verification FAILED")

        print("=" * 40)

        return report