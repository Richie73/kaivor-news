
"""
Kaivor Compile Verification Service
"""

from pathlib import Path
import py_compile
import time


class ProjectCompiler:
    """Compile the active Kaivor project."""

    IGNORE_DIRS = {
        "__pycache__",
        ".git",
        ".venv",
        "backups",
        "releases",
        "logs",
        "output",
        "workspace",
    }

    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path.cwd())

    def _should_skip(self, path):
        return any(part in self.IGNORE_DIRS for part in path.parts)

    def compile_all(self):

        start = time.time()

        results = []
        checked = 0
        failed = 0

        for py_file in sorted(self.project_root.rglob("*.py")):

            if self._should_skip(py_file):
                continue

            checked += 1

            relative = py_file.relative_to(self.project_root)

            try:
                py_compile.compile(str(py_file), doraise=True)

                results.append(
                    {
                        "file": str(relative),
                        "success": True,
                        "error": "",
                    }
                )

            except py_compile.PyCompileError as error:

                failed += 1

                results.append(
                    {
                        "file": str(relative),
                        "success": False,
                        "error": str(error),
                    }
                )

        elapsed = round(time.time() - start, 2)

        return {
            "passed": failed == 0,
            "checked": checked,
            "failed": failed,
            "elapsed": elapsed,
            "results": results,
        }

    def print_report(self):

        report = self.compile_all()

        print()
        print("=" * 50)
        print("KAIVOR COMPILE REPORT")
        print("=" * 50)

        for result in report["results"]:

            if not result["success"]:
                print()
                print(f"FAILED: {result['file']}")
                print(result["error"])

        print()
        print(f"Python files checked : {report['checked']}")
        print(f"Files failed         : {report['failed']}")
        print(f"Elapsed              : {report['elapsed']} seconds")

        print()

        if report["passed"]:
            print("STATUS : PASS")
        else:
            print("STATUS : FAIL")

        print("=" * 50)

        return report