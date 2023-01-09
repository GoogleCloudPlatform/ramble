class SetCache:
    def __init__(self):
        self.store = set()

    def add(self, tupl):
        self.store.add(tupl)

    def contains(self, tupl):
        return (tupl in self.store)
