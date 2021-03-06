from __future__ import generators
from peak.api import *
from interfaces import *
import io_events, sources
from twisted.internet import defer
from twisted.python import failure


def getTwisted():

    """Get Twisted reactor, or die trying"""

    try:
        from twisted.internet import reactor
    except ImportError:
        raise exceptions.NameNotFound(
            """twisted.internet.reactor could not be imported"""
        )
    else:
        return reactor

Reactor = getTwisted  # for easy reference in peak.ini



















class DeferredAsEventSource(sources.Value,protocols.StickyAdapter):

    attachForProtocols = (IWritableSource,IValue,IPausableSource)

    protocols.advise(
        instancesProvide=attachForProtocols, asAdapterForTypes=[defer.Deferred],
    )

    def __init__(self,ob):
        protocols.StickyAdapter.__init__(self,ob)
        sources.Value.__init__(self)

    def _fire(self,event):
        super(DeferredAsEventSource,self)._fire(event)
        if not isinstance(event,failure.Failure):
            return event

    def set(self,value,force=False):
        if self.subject.called:
            cb = lambda v: self._fire(value)
            self.subject.addCallbacks(cb,cb)
        else:
            self.subject.callback(value)

    def addCallback(self,func):
        if self.subject.called:
            func(self, self.subject.result)
            return lambda:None  # cancel is no-op

        haveCB = len(self._callbacks)
        canceller = super(DeferredAsEventSource,self).addCallback(func)
        if not haveCB:
            self.subject.addCallbacks(self._fire, self._fire)
        return canceller

    def __call__(self):
        if self.subject.called:
            return self.subject.result
        else:
            return NOT_GIVEN

    def derive(self,func):
        b = sources.Value()
        self.subject.addCallback(lambda v: [b.set(func(v)),v][1])
        return b



    def nextAction(self, task=None, state=None):

        if state is not None:

            def handler():
                v = events.resume()
                if isinstance(v,failure.Failure):
                    raise v
                else:
                    yield v

            state.CALL(handler())

            if self.subject.called:
                state.YIELD(self.subject.result)
            else:
                self.addCallback(task.step)

        return self.subject.called















class Scheduler(binding.Component,events.Scheduler):

    """'events.IScheduler' that uses a Twisted reactor for timing"""

    reactor = binding.Obtain(running.ITwistedReactor)
    now     = binding.Obtain('import:time.time')
    isEmpty = binding.Make(lambda: events.Condition(True))

    def time_available(self):
        return 0    # no way to find this out from a reactor :(

    def tick(self,stop=False):
        self.reactor.iterate()

    def _callAt(self, what, when):
        self.isEmpty.set(False)
        self.reactor.callLater(max(0,when-self.now()), what, self, when)
























class EventLoop(io_events.EventLoop):

    """Implement an event loop using reactor.run()"""

    reactor = binding.Obtain(running.ITwistedReactor)

    def runUntil(self, eventSource, suppressErrors=False, idle=None):

        if not suppressErrors:
            raise NotImplementedError(
                "Twisted reactors always suppress errors"
            )

        exit = []   # holder for exit event

        # When event fires, record it for our return
        adapt(eventSource,IEventSource).addCallback(
            lambda s,e: [exit.append(e), self.reactor.crash()]
        )

        if not exit:
            self.reactor.run(False)

        if exit:
            return exit.pop()
        else:
            raise StopIteration("Unexpected reactor exit")














class TwistedReadEvent(io_events.AbstractIOEvent):

    __slots__ = 'reactor','fd'

    def __init__(self,reactor,fileno):
        super(TwistedReadEvent,self).__init__()
        self.fd = fileno
        self.reactor = reactor

    def fileno(self):
        return self.fd

    def doRead(self):
        self._fire(True)

    def connectionLost(self,*args): pass    # XXX

    def logPrefix(self):
        return '(peak.events)'

    def _activate(self):
        self.reactor.addReader(self)

    def _deactivate(self):
        self.reactor.removeReader(self)


class TwistedWriteEvent(TwistedReadEvent):

    __slots__ = ()

    def doWrite(self):
        self._fire(True)

    def _activate(self):
        self.reactor.addWriter(self)

    def _deactivate(self):
        self.reactor.removeWriter(self)


class Selector(io_events.Selector):

    """Implement ISelector using a reactor"""

    reactor = binding.Obtain(running.ITwistedReactor)
    monitor = None  # don't run a monitoring task!

    def _mkEvent(self,rwe,key):
        if rwe==2:
            return sources.Broadcaster()    # XXX reactor doesn't allow this
        else:
            return [TwistedReadEvent, TwistedWriteEvent][rwe](self.reactor,key)





























