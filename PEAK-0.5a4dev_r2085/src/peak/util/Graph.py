import dispatch
from sets import Set



class Graph:
    def __init__(self,iterable=()):
        self.kvl = {}
        self.has_key = self.kvl.has_key
        for k,v in iterable:
            self[k] = v
        
    [dispatch.as(classmethod)]
    def fromkeys(cls,keys):
        return cls([(k,k) for k in keys])

    def neighbors(self,key):
        return self.kvl.get(key,[])

    def __getitem__(self,key):
        return self.kvl[key][0]

    def restrict(self,other):
        if not isinstance(other,Graph):
            other = Graph(other)
        kvl = other.kvl
        return Graph([(k,v) for k,v in self if k in kvl])

    def __sub__(self,other):
        return Graph(Set(self) - Set(other))

    def __eq__(self,other):
        return Set(self) == Set(other)

    def __ne__(self,other):
        return Set(self) != Set(other)

    def __len__(self):
        return sum([len(v) for v in self.kvl.values()])

    def reachable(self,key):
        oldkey = key
        stack = [key]
        found = Set()
        add = found.add
        extend = stack.extend
        while stack:
            key = stack.pop()
            if key not in found:
                next = self.kvl.get(key,[])
                stack.extend(next)
                add(key)
        found.remove(oldkey)
        return found

    def __repr__(self):
        keys = list(self)
        keys.sort()
        return "Graph(%r)" % keys

    def __iter__(self):
        for k,vl in self.kvl.items():
            for v in vl:
                yield k,v

    def __setitem__(self,key,val):
        vl = self.kvl.setdefault(key,[]) 
        if val not in vl:
            vl.append(val)

    add = __setitem__

    def __invert__(self):
        return Graph([(v,k) for k,v in self])

    def __add__(self,other):
        return Graph(list(self)+list(other))

    def __iadd__(self,other):
        for k,v in other:
            self[k] = v
        return self

    __ior__ = __iadd__

    def __or__(self,other):
        return Graph(list(self)+list(other))

    def __mul__(self,other):
        if not isinstance(other,Graph):
            other = Graph(other)
        all = other.kvl
        return Graph([(k,v2) for k,v in self if v in all for v2 in all[v]])

    def __contains__(self,(key,val)):
        return val in self.kvl.get(key,())

    def keys(self):
        return self.kvl.keys()

    def values(self):
        data = []
        for v in self.kvl.values(): data.extend(v)
        return data

    def items(self):
        return list(self)

