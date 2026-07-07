class NewsEngine:

    def display(self, heading, articles):

        print()
        print("=" * 60)
        print(heading.upper())
        print("=" * 60)
        print()

        if not articles:
            print("No articles found.\n")
            return

        for index, article in enumerate(articles, start=1):
            print(f"{index}. {article.title}")
            print(f"   Source : {article.source}")
            print(f"   Date   : {article.published}")
            print(f"   Link   : {article.link}")
            print()
