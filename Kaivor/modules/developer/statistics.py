
"""
Kaivor Project Statistics
"""

from pathlib import Path

from modules.developer.ui import (
    title,
    start_timer,
    end_timer,
    error,
)


def project_statistics():

    start_timer()

    title("PROJECT STATISTICS")

    try:

        project = Path(".")

        py_files = list(project.rglob("*.py"))
        md_files = list(project.rglob("*.md"))
        json_files = list(project.rglob("*.json"))
        log_files = list(project.rglob("*.log"))

        total_lines = 0

        for file in py_files:

            try:

                with open(file, "r", encoding="utf-8") as f:

                    total_lines += sum(1 for _ in f)

            except Exception:

                pass

        total_size = sum(
            f.stat().st_size
            for f in project.rglob("*")
            if f.is_file()
        )

        print(f"Python Files    : {len(py_files)}")
        print(f"Markdown Files  : {len(md_files)}")
        print(f"JSON Files      : {len(json_files)}")
        print(f"Log Files       : {len(log_files)}")
        print(f"Total Lines     : {total_lines:,}")
        print(f"Project Size    : {total_size / 1024:.1f} KB")

    except Exception as e:

        error(str(e))

    finally:

        end_timer()