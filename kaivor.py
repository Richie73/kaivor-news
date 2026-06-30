from core.banner import show_banner
from core.config import VERSION, OWNER, MODULES
from core.menu import show_menu

from modules.dashboard import show_dashboard

from modules.ai_news import get_ai_news
from modules.technology import get_technology_news
from modules.uk_news import get_uk_news
from modules.world_news import get_world_news
from modules.investment import get_investment_news
from modules.football import get_football_news
from modules.android import get_android_news
from modules.music import get_music_news
from modules.search import search_database


def main():
    show_banner()

    print()
    print(f"Version : {VERSION}")
    print("Status  : Ready")
    print()

    print("Modules Loaded:")
    for module in MODULES:
        print(f"✓ {module}")

    print()
    print(f"Welcome, {OWNER}.")
    print("Kaivor is ready.")

    while True:

        choice = show_menu()

        if choice == "1":
            show_dashboard()

        elif choice == "2":
            print("\nFetching AI Intelligence...\n")
            get_ai_news()

        elif choice == "3":
            print("\nFetching Technology News...\n")
            get_technology_news()

        elif choice == "4":
            print("\nFetching UK News...\n")
            get_uk_news()

        elif choice == "5":
            print("\nFetching World News...\n")
            get_world_news()

        elif choice == "6":
            print("\nFetching Investment News...\n")
            get_investment_news()

        elif choice == "7":
            print("\nFetching Football News...\n")
            get_football_news()

        elif choice == "8":
            print("\nFetching Android News...\n")
            get_android_news()

        elif choice == "9":
            print("\nFetching Music News...\n")
            get_music_news()
            
        elif choice == "10":
            search_database()

        elif choice == "0":
            print(f"\nGoodbye, {OWNER}.")
            break

        else:
            print("\nInvalid selection.\n")


if __name__ == "__main__":
    main()
