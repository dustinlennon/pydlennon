
import numpy

class SeededRng(object):
    def __init__(self, seed):
        self._seed = seed
        self._rng  = None

    def __getattr__(self, k):
        if hasattr(self._rng, k):
            return getattr(self._rng, k)
        else:
            raise AttributeError(k)

    def __enter__(self):
        self._rng = numpy.random.default_rng(self._seed)
        return self

    def __exit__(self, exc_typ, exc_value, exc_tb):
        self._rng = None

