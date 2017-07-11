from peak.api import *
from interfaces import *

class AbstractDelta(object):

    protocols.advise(instancesProvide = [IDelta])

    __slots__ = 'active', 'done'
    undoable = True
    key = None

    def __init__(self):
        self.active = self.done = True

    def undo(self):
        if self.active:
            self.finish()
        if self.done:
            if self.undoable:
                self._undo()
                self.done = False
            else:
                raise UndoError("Can't undo", self)
        else:
            raise UndoError("Repeated undo", self)

    def redo(self):
        if self.done:
            raise UndoError("Repeated redo", self)
        else:
            self._redo()
            self.done = True

    def finish(self):
        if self.active:
            self._finish()
            self.active = False
        else:
            raise UndoError("Delta is already checkpointed", self)


    def merge(self,delta):
        if self.active:
            self._merge(delta)
        else:
            raise UndoError("Delta no longer active", self)

    def _merge(self,delta):
        raise NotImplementedError

    def _undo(self):
        raise NotImplementedError

    def _redo(self):
        raise NotImplementedError

    def _finish(self):
        raise NotImplementedError
























class History(AbstractDelta):

    protocols.advise(instancesProvide = [IHistory])

    def __init__(self):
        AbstractDelta.__init__(self)
        self.data = []
        self.by_key = {}

    def _merge(self,delta):
        history = IHistory(delta,None)
        if history is not None:
            map(self._merge,history)
            return

        key = delta.key
        if key in self.by_key and key is not None:
            self.by_key[key].merge(delta)
        else:
            self.data.append(delta)
            self.by_key[key] = delta

        if not delta.undoable:
            self.undoable = False

    def _finish(self):
        for delta in self.data:
            delta.finish()

    def _redo(self):
        for delta in self.data:
            delta.redo()

    def _undo(self):
        for delta in self.data:
            delta.undo()





    def __iter__(self):
        return iter(self.data)

    def __contains__(self,key):
        return key in self.by_key

    def __len__(self):
        return len(self.data)

































class UndoManager:
    
    protocols.advise(instancesProvide = [IUndoManager])

    def __init__(self):
        self.history = History()
        self.undos = []
        self.redos = []
        
    def record(self,delta):
        self.history.merge(delta)
        if self.redos:
            self.redos = []
        
    def has_delta_for(self,key):
        return key in self.history
    
    def checkpoint(self):
        self.history.finish()
        if self.history.undoable:
            self.undos.append(self.history)
        else:
            self.undos = []

        self.history = History()
        if self.redos:
            self.redos = []

    def revert(self):
        self.history.undo()
        self.history = History()










    def undoLast(self):
        if self.history:
            raise UndoError("Can't undo; deltas have not been checkpointed")
        last = self.undos.pop()
        last.undo()
        self.redos.append(last)
        
    def redoNext(self):
        if self.redos:
            next = self.redos.pop()
            next.redo()
            self.undos.append(next)
        else:
            raise UndoError("Nothing to redo")


























