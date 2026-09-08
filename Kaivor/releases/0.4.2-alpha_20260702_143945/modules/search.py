from database.search import Search


def search_database():

    query = input("\nSearch for: ")

    engine = Search()

    results = engine.search(query)

    print()
    print("=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)

    if not results:
        print("\nNo matching articles found.\n")
        return

    for i, article in enumerate(results, start=1):

        print(f"{i}. {article['title']}")
        print(f"   Source : {article['source']}")
        print(f"   Date   : {article['published']}")
        print(f"   Link   : {article['link']}")
        print()
