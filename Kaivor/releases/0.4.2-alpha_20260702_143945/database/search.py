from database.storage import Storage


class Search:

    def __init__(self):
        self.storage = Storage()

    def search(self, query):

        query = query.lower()

        results = []

        for article in self.storage.load():

            if (
                query in article["title"].lower()
                or query in article["source"].lower()
            ):
                results.append(article)

        return results
