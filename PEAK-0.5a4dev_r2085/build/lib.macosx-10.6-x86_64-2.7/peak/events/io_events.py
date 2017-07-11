from __future__ import generators
from peak.core import protocols, adapt, binding, NOT_GIVEN, PropertyName
from interfaces import *
from peak.util.EigenData import AlreadyRead
from weakref import WeakValueDictionary, ref
import sources
from event_threads import resume, taskFactory
from errno import EINTR
from time import sleep

try:
    import signal

except ImportError:
    SIG_DFL = None
    signals = {}
    signal_names = {}
    signal = lambda *args: None
    original_signal_handlers = {}

else:
    SIG_DFL = signal.SIG_DFL

    signals = dict(
        [(name,number)
            for (name,number) in signal.__dict__.items()
                if name.startswith('SIG') and not name.startswith('SIG_')
        ]
    )

    signal_names = {}
    for signame,signum in signals.items():
        signal_names.setdefault(signum,[]).append(signame)

    original_signal_handlers = dict(
        [(signum,signal.getsignal(signum)) for signum in signal_names.keys()]
    )

    signal = signal.signal


class AbstractIOEvent(sources.Broadcaster):

    """Abstract base for broadcast events based on other event systems
    
    (Such as 'signal', 'select()', etc.)
    """

    __slots__ = '_registered'

    def __init__(self,*__args,**__kw):
        self._registered = False
        super(AbstractIOEvent,self).__init__(*__args,**__kw)

    def _register(self):
        if self._callbacks:
            if not self._registered:
                self._activate()
                self._registered = True
        elif self._registered:
            self._deactivate()
            self._registered = False

    def _fire(self,event):
        try:
            super(AbstractIOEvent,self)._fire(event)
        finally:
            self._register()

    def addCallback(self,func):
        try:
            return super(AbstractIOEvent,self).addCallback(func)
        finally:
            self._register()








class SignalEvent(AbstractIOEvent):

    """Event used for trapping signals"""

    __slots__ = 'signum'

    def __init__(self,signum):
        super(SignalEvent,self).__init__()
        self.signum = signum

    def _activate(self):
        signal(self.signum, self.handler)

    def _deactivate(self):
        signal(self.signum, original_signal_handlers[self.signum])
        
    def handler(self,signum,frame):
        self.send((signum,frame))


class StreamEvent(AbstractIOEvent):

    """Event used for read/write/exception conditions on streams"""

    __slots__ = '_activate','_deactivate'
















class SignalEvents(binding.Singleton):

    """Global signal manager"""

    protocols.advise( classProvides = [ISignalSource] )

    _events = {None: sources.Broadcaster()}     # Null signal

    def signals(self,*signames):
        """'IEventSource' that triggers whenever any of named signals occur"""

        if len(signames)==1:
            signum = signals.get(signames[0])
            try:
                return self._events[signum]
            except KeyError:
                e = self._events[signum] = SignalEvent(signum)
                return e
        else:
            return sources.AnyOf(*[self.signals(n) for n in signames])


    def haveSignal(self,signame):
        """Return true if signal named 'signame' exists"""
        return signame in signals

    def __call__(self,*args):
        return self













class EventLoop(binding.Component):

    """All-in-one event source and loop runner"""

    protocols.advise( instancesProvide = [IEventLoop] )

    sigsrc = binding.Obtain(ISignalSource)
    haveSignal = signals = binding.Delegate('sigsrc')

    scheduler = binding.Obtain(IScheduler)
    spawn = now = tick = sleep = until = timeout = time_available \
        = binding.Delegate('scheduler')

    selector  = binding.Obtain(ISelector)
    readable = writable = exceptional = binding.Delegate('selector')

    log = binding.Obtain('logger:peak.events.loop')
























    def runUntil(self, eventSource, suppressErrors=False, idle=sleep):

        running = [True]
        exit = []
        tick = self.tick
        time_available = self.time_available

        adapt(eventSource,IEventSource).addCallback(
            lambda s,e: [running.pop(),exit.append(e)]
        )

        if suppressErrors:
            def tick(exit,doTick=tick):
                try:
                    doTick(exit)
                except:
                    self.log.exception("Unexpected error in event loop:")

        while running:
            tick(exit)
            if running:
                delay = time_available()
                if delay is None:
                    raise StopIteration("Nothing scheduled to execute")
                if delay>0:
                    idle(delay)

        return exit.pop()













class Selector(binding.Component):

    """Simple task-based implementation of an ISelector"""

    protocols.advise( instancesProvide = [ISelector] )

    sigsrc = binding.Obtain(ISignalSource)
    haveSignal = signals = binding.Delegate('sigsrc')


    cache = binding.Make( [dict,dict,dict] )
    rwe   = binding.Make( [dict,dict,dict] )
    count = binding.Make( lambda: sources.Semaphore(0) )
    scheduler = binding.Obtain(IScheduler)

    checkInterval = binding.Obtain(
        PropertyName('peak.running.reactor.checkInterval')
    )

    sleep   = binding.Obtain('import:time.sleep')
    select  = binding.Obtain('import:select.select')
    _error  = binding.Obtain('import:select.error')


    def readable(self,stream):
        """'IEventSource' that fires when 'stream' is readable"""
        return self._getEvent(0,stream)

    def writable(self,stream):
        """'IEventSource' that fires when 'stream' is writable"""
        return self._getEvent(1,stream)

    def exceptional(self,stream):
        """'IEventSource' that fires when 'stream' is in error/out-of-band"""
        return self._getEvent(2,stream)






    def monitor(self):

        r,w,e = self.rwe
        count = self.count
        sleep = self.scheduler.sleep()
        time_available = self.scheduler.time_available
        select = self.select
        error = self._error

        while True:
            yield count; resume()   # wait until there are selectables
            yield sleep; resume()   # ensure we are in top-level loop

            delay = time_available()
            if delay is None:
                delay = self.checkInterval

            try:
                fr,fw,fe = self.select(r.keys(),w.keys(),e.keys(),delay)
            except error, v:
                if v.args[0]==EINTR:
                    continue    # signal received during select, try again
                else:
                    raise

            for fired,events in (fe,e),(fr,r),(fw,w):
                for stream in fired:
                    events[stream].send(True)


    monitor = binding.Make(taskFactory(monitor), uponAssembly=True)










    def _getEvent(self,rwe,stream):
        if hasattr(stream,'fileno'):
            key = stream.fileno()
        else:
            key = int(stream)

        try:
            return self.cache[rwe][key]
        except KeyError:
            self.cache[rwe][key] = e = self._mkEvent(rwe,key)
            return e

    def _mkEvent(self,rwe,key):
        ob = StreamEvent()
        ob._activate = lambda: self._activate(rwe,key,ob)
        ob._deactivate = lambda: self._deactivate(rwe,key)
        return ob

    def _rmEvent(self,rwe,key):
        del self.cache[rwe][key]
        self._deactivate(rwe,key)

    def _activate(self,rwe,key,src):
        if key not in self.rwe[rwe]:
            self.rwe[rwe][key] = src
            self.count.put()

    def _deactivate(self,rwe,key):
        if key in self.rwe[rwe]:
            del self.rwe[rwe][key]
            self.count.take()










