"""
Kaivor Memory Console
"""

from core.memory.api import recall, search
from modules.developer.ui import title, pause


def memory_console():

    while True:

        title("MEMORY MANAGER")

        print("1. View All Memories")
        print("2. Search Memories")
        print("0. Return")

        choice = input("\nSelect option: ").strip()

        if choice == "1":

            memories = recall()

            print()

            if not memories:
                print("No memories stored.")
            else:
                for memory in memories:
                    print(f"[{memory.id}] {memory.category}")
                    print(f"Title : {memory.title}")
                    print(f"Content : {memory.content}")
                    print("-" * 40)

            pause()

        elif choice == "2":

            keyword = input("Keyword: ")

            results = search(keyword)

            print()

            if not results:
                print("No matching memories.")
            else:
                for memory in results:
                    print(f"[{memory.id}] {memory.title}")
                    print(memory.content)
                    print("-" * 40)

            pause()

        elif choice == "0":
            break

        else:
            print("Invalid selection.")
            pause()
