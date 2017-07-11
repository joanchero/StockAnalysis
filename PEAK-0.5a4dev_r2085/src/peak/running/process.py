from __future__ import generators
from peak.api import *
from interfaces import *
from weakref import WeakValueDictionary, ref
from peak.events.io_events import signals, signal_names     # XXX
import errno



































class ChildProcess(binding.Component):

    protocols.advise(
        instancesProvide = [IProcessProxy]
    )

    log        = binding.Obtain('logger:running.process')
    pid        = None
    isRunning  = binding.Make(lambda self: (~self.isStopped & ~self.isFinished))
    isStopped  = isFinished = binding.Make(lambda: events.Condition(False))
    exitStatus = stoppedBecause = exitedBecause = binding.Make(
        lambda: events.Value(None)
    )

    statusEvents = binding.Obtain(
        [   'isStopped','isFinished','exitStatus','stoppedBecause',
            'exitedBecause'
        ]
    )

    isOpen    = binding.Make(lambda: events.Condition(True))
    eventLoop = binding.Obtain(events.IEventLoop)

    import os

    def waitForSignals(self):
        while self.isRunning() and self.isOpen():
            yield self.eventLoop.signals('SIGCLD','SIGCHLD'); events.resume()
            if not self.isOpen(): return

            # ensure that we are outside the signal handler before we 'wait()'
            yield self.eventLoop.sleep(); events.resume()
            self._checkStatus()

        self.close()

    waitForSignals = binding.Make(
        events.taskFactory(waitForSignals), uponAssembly = True
    )


    def close(self):
        self._delBinding('waitForSignals')  # drop references
        self.isOpen.set(False)


    def sendSignal(self, signal):

        if signal in signals:
            # convert signal name to numeric signal
            signal = signals[signal]

        elif signal not in signal_names:
            raise ValueError,"Unsupported signal", signal

        try:
            self.os.kill(self.pid, signal)
        except:
            return False
        else:
            return True


    def _checkStatus(self):
        try:
            p, s = self.os.waitpid(self.pid, self.os.WNOHANG)
        except OSError,v:
            if v.args[0]==errno.ECHILD:
                self._setStatus(None)
            elif v.args[0]==errno.EINTR:
                self._checkStatus() # retry
            else:
                self.log.exception("Unexpected error in waitpid()")
        else:
            if p==self.pid:
                self._setStatus(s)






    def _setStatus(self,status=None):

        for event in self.statusEvents:
            event.disable()

        self.exitedBecause.set(None)
        self.stoppedBecause.set(None)

        if status is None:
            self.exitedBecause.set(-1)
            self.exitStatus.set(-1)
        else:
            self.isStopped.set(self.os.WIFSTOPPED(status))
    
            if self.os.WIFEXITED(status):
                self.exitStatus.set(self.os.WEXITSTATUS(status))
    
            if self.isStopped:
                self.stoppedBecause.set(self.os.WSTOPSIG(status))
    
            if self.os.WIFSIGNALED(status):
                self.exitedBecause.set(self.os.WTERMSIG(status))

        self.isFinished.set(
            self.exitedBecause() is not None or self.exitStatus() is not None
        )

        for event in self.statusEvents:
            try:
                event.enable()
            except:
                self.log.exception("Unexpected error in process listener")









class AbstractProcessTemplate(binding.Component):

    protocols.advise(
        instancesProvide = [IProcessTemplate],
        asAdapterForProtocols = [IExecutable],
        factoryMethod = 'templateForCommand'
    )

    import os

    proxyClass = ChildProcess   # default factory for proxy
    readPipes  = ()             # sequence of attribute names for p<-c pipes
    writePipes = ()             # sequence of attribute names for p->c pipes

    def spawn(self, parentComponent):

        parentPipes, childPipes = {}, {}

        for name in self.readPipes:
            parentPipes[name], childPipes[name] = self._mkPipe()
        for name in self.writePipes:
            childPipes[name], parentPipes[name] = self._mkPipe()

        pid = self.os.fork()

        if pid:
            # Parent process
            [f.close() for f in childPipes.values()]
            del childPipes
            return self._makeProxy(parentComponent,pid,parentPipes), None

        else:
            # Child process
            [f.close() for f in parentPipes.values()]
            del parentPipes
            self.__dict__.update(childPipes)    # set named attrs w/pipes
            return None, self._redirectWrapper(self._makeStub())




    def _mkPipe(self):
        r,w = self.os.pipe()
        return self.os.fdopen(r,'r',0), self.os.fdopen(w,'w',0)


    def _makeProxy(self,parentComponent,pid,pipes):

        proxy = self.proxyClass(pid=pid)

        for name, stream in pipes.items():
            setattr(proxy, name, stream)

        # Set parent component *after* the pipes are set up, in case
        # the proxy has assembly events that make use of the pipes.
        binding.suggestParentComponent(parentComponent,None,proxy)
        return proxy


    def _redirect(self):
        pass


    def _redirectWrapper(self, cmd):
        """Wrap 'cmd' so that it's run after doing our redirects"""

        def runner():
            self._redirect()
            return cmd

        return runner











    def _makeStub(self):
        return self.command


    command = binding.Require(
        "Command to run in subprocess", suggestParent=False
    )


    def templateForCommand(klass, ob, proto):
        return klass(ob, command = ob)

    templateForCommand = classmethod(templateForCommand)




























