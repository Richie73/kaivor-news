from datetime import datetime


def show_dashboard():

    now = datetime.now()

    print("=" * 60)
    print("                    KAIVOR DASHBOARD")
    print("=" * 60)

    print(f"Date : {now.strftime('%A %d %B %Y')}")
    print(f"Time : {now.strftime('%H:%M')}")

    print()

    print("Weather")
    print("  Loading...")

    print()

    print("Calendar")
    print("  No events")

    print()

    print("Unread Email")
    print("  Loading...")

    print()

    print("Markets")
    print("  Loading...")

    print()

    print("Top AI Headline")
    print("  Loading...")

    print("=" * 60)