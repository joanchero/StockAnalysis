"""Manage potentially-conflicting settings from multiple sources"""

class ConflictManager:
    """Manage potentially-conflicting settings from multiple sources

    Usage::
        cm = ConflictManager()

        # This keeps the "most-specific" data (shortest non-conflicting path)
        # or raises an error if a conflicting setting is made
        cm[key] = path, setting

        for setting in cm.values():
            # process setting

    Keys can be any hashable value.  'path' objects must be sequences of
    a uniform type, representing an "inclusion path".  For example, if
    the settings are being read from a file 'foo' that was included within a
    file 'bar', then the 'path' would be '("bar","foo")'.  If 'foo' then
    includes a file 'baz', its path would be '("bar","foo","baz")'.  For any
    given pair of settings, one is kept if its path is a prefix of the other
    path.  If neither path is a prefix of the other, or the paths are equal,
    a 'KeyError' will be raised to indicate a conflict.

    At any time, the current settings can be read back out via the 'values()'
    method.
    """

    def __init__(self):
        self.clear()

    def __getitem__(self,key):
        return self.data[key][1]

    def values(self):
        return [v[1] for v in self.data.values()]

    def clear(self):
        self.data = {}


    def __setitem__(self,key,(path,val)):
        if key in self.data:
            old = self.data[key][0]

            new_beats_old = old[:len(path)]==path
            old_beats_new = path[:len(old)]==old

            if new_beats_old == old_beats_new:
                raise KeyError  # paths are equal or disjoint -> conflict
            elif old_beats_new:
                return
        self.data[key] = path,val





























