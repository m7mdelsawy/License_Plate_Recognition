from collections import defaultdict, Counter
import numpy as np

class PlateVoting:
    def __init__(self, window=10, min_votes=3):
        self.window = window
        self.min_votes = min_votes
        self.data = defaultdict(list)

    def add(self, vid, text, conf):
        self.data[vid].append((text, conf))
        self.data[vid] = self.data[vid][-self.window:]

    def consensus(self, vid):
        if len(self.data[vid]) < self.min_votes:
            return None
        texts = [t for t,_ in self.data[vid]]
        best = Counter(texts).most_common(1)[0][0]
        confs = [c for t,c in self.data[vid] if t == best]
        return best, float(np.mean(confs))
