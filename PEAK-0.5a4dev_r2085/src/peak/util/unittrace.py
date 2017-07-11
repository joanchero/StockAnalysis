from __future__ import generators
from types import FunctionType, MethodType
import sys

callable_types = FunctionType, MethodType

__all__ = [
    'Call', 'History'
]


class Args:
    def __init__(self,vars):
        self.__dict__ = vars.copy()


def splitCallable(func):
    args=[]
    while hasattr(func,'im_self'):
        self = func.im_self
        if self is not None:
            args.append(self)
        func = func.im_func

    return func.func_code,tuple(args)


def iterCalls(log, func, **kw):
    for call in log:
        if call==func:
            if kw and not call.hadArgs(**kw):
                continue
            yield call








class Call:
    """Record of a single function invocation"""
    def __init__(self,code,vars):
        self.code = code
        self.args = Args(vars)

    def hadArgs(__self,**vars):
        args = __self.args.__dict__
        for k,v in vars.items():
            if k not in args or args[k]<>v:
                return False
        return True

    def __cmp__(self,other):
        if isinstance(other,callable_types):
            code,args = splitCallable(other)
            if code is self.code:
                if args:
                    vars = self.args.__dict__
                    for argname,argval in zip(code.co_varnames,args):
                        if vars[argname]!=argval: break
                    else:
                        return 0
                else:
                    return 0
        return cmp((self.code,self.args),other)

    def __repr__(self):
        return "Call(%r,%r)" % (self.code,self.args.__dict__)












class HistIter:

    def __init__(self,log):
        self.it = iter(log)
        self.next = self.it.next

    def __iter__(self):
        return self

    def find(self, func, **kw):
        return iterCalls(self.it,func,**kw).next()






























class History:

    def __init__(self,max_depth=5):
        self.log = []
        self.max_depth = max_depth
        self.depth = 0
        self.curframe = None

    def __iter__(self):
        return HistIter(self.log)

    def callsTo(self, func, **kw):
        return iterCalls(self.log, func, **kw)

    def called(self, func, **kw):
        for call in iterCalls(self.log, func, **kw):
            return call
        return None

    def calledOnce(self, func, **kw):
        items = list(self.callsTo(func,**kw))
        if len(items)==1:
            return items[0]
        return None

    def trace_event(self,frame,event,arg):

        if event=='call':
            self.depth += 1
            if self.depth<=self.max_depth:
                self.log.append(Call(frame.f_code, frame.f_locals))

        elif event=='return':
            self.depth -= 1

        elif event=='exception':
            if frame is not self.curframe:
                self.depth -= 1

        self.curframe = frame

    def trace(__s,__f,*__a,**__k):
        try:
            sys.setprofile(__s.trace_event)
            return __f(*__a,**__k)
        finally:
            sys.setprofile(None)



































