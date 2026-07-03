"""
Kaivor Developer Console
"""

from modules.diagnostics import diagnostics
from modules.developer.dashboard import developer_dashboard
from modules.developer.statistics import project_statistics
from modules.developer.verification import verify_project
from modules.developer.logs import view_log, clear_log
from modules.developer.git_tools import git_status
from modules.developer.release_tools import build_release
from modules.developer.cleanup import clean_pycache
from modules.developer.backup import create_backup
from modules.developer.restore import restore_backup
from modules.developer.ui import pause
from modules.developer.memory_console import memory_console

def developer_menu():

    while True:

        developer_dashboard()

        choice = input("Select option: ").strip()

        if choice == "1":
            diagnostics()
            input("\nPress Enter to continue...")

        elif choice == "2":
            project_statistics()
            input("\nPress Enter to continue...")

        elif choice == "3":
            verify_project()
            input("\nPress Enter to continue...")

        elif choice == "4":
            view_log()
            input("\nPress Enter to continue...")

        elif choice == "5":
            clear_log()
            input("\nPress Enter to continue...")

        elif choice == "6":
            git_status()
            input("\nPress Enter to continue...")

        elif choice == "7":
            build_release()
            input("\nPress Enter to continue...")

        elif choice == "8":
            clean_pycache()
            input("\nPress Enter to continue...")

        elif choice == "9":
            create_backup()
            input("\nPress Enter to continue...")

        elif choice == "10":
            restore_backup()
            input("\nPress Enter to continue...")

        elif choice == "11":
            memory_console()
        
        elif choice == "0":
            break

        else:
            print("\nInvalid selection.")
            input("\nPress Enter to continue...")
