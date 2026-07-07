from database.storage import Storage


class DatabaseStats:

    def __init__(self):
        self.storage = Storage()

    def total_articles(self):
        return len(self.storage.load())
