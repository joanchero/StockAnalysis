from peak.api import *
from getopt import getopt
import re, sys, os


__all__ = ['parseCmd', 'ShellCommand']


def parseCmd(ctx, cmdline, defaults):
    """Parse a command line, and return a dictionary containing
    argv, stdin, stdout, stderr, and environ.

    default for the last for are pulled from the same-named
    attributes of the object "defaults"

    Supports <, >, >>, 2>, 2>>, | redirection, quoted arguments.

    TODO: support VAR=value before command to change environment?
    """

    r = {'close':{}}

    for a in ('stdin', 'stdout', 'stderr', 'environ'):
        r[a] = getattr(defaults, a)

    cmdline, pipeto = pipesplit(cmdline)

    av = []
    l = qsplit(cmdline)

    try:
        for a in l:
            if a.startswith('>>'):
                factory = config.getStreamFactory(ctx,a[2:])
                r['stdout'] = f = factory.update('t', append=True, autocommit=True)
                r['close'][f] = 1
            elif a.startswith('>'):
                factory = config.getStreamFactory(ctx,a[1:])
                r['stdout'] = f = factory.create('t', autocommit=True)
                r['close'][f] = 1
            elif a.startswith('2>>'):
                factory = config.getStreamFactory(ctx,a[3:])
                r['stderr'] = f = factory.update('t', append=True, autocommit=True)
                r['close'][f] = 1
            elif a.startswith('2>'):
                factory = config.getStreamFactory(ctx,a[2:])
                r['stderr'] = f = factory.create('t', autocommit=True)
                r['close'][f] = 1
            elif a.startswith('<'):
                factory = config.getStreamFactory(ctx,a[1:])
                r['stdin'] = f = factory.open('t', autocommit=True)
                r['close'][f] = 1
            else:
                av.append(a)

        if pipeto is not None:
            r['stdout'] = f = os.popen(pipeto, 'w')
            r['close'][f] = 1

        r['argv'] = av
    except:
        for f in r['close'].keys():
            f.close()
            
        raise
        
    r['close'] = r['close'].keys()

    return r



def dequote(s):
    s = s.split('"')
    a = []
    p = []
    back = False
    i = 0
    for w in s:
        if back:
            p.append('"')
        else:
            a.append(''.join(p)); p = []
        p.append(w)
        back = (i % 2) and w.endswith('\\')
        i += 1
    a.append(''.join(p))

    l = []
    for i in range(len(a)):
        v = a[i]
        if i % 2 == 0:
            v = eval('"%s"' % v)
        l.append(v)

    return ''.join(l)


def pipesplit(s):
    # shortcut common case
    if '|' not in s:
        return s, None

    quoted = back = False
    i = 0
    for c in s:
        if back:
            back = False
        elif c == '\\' and quoted:
            back = True
        elif c == '"':
            quoted = not quoted
        elif c == '|' and not quoted:
            return s[:i], s[i+1:]

        i += 1

    return s, None


splitter = re.compile('(\S+)').split


def qsplit(s):
    l = splitter(s) + ['']
    l = [(l[i], l[i+1]) for i in range(0, len(l), 2)]

    a = []; p = []
    quoted = False
    for s, t in l:
        if quoted:
            p.append(s)
        else:
            a.append(''.join(p)); p = []

        p.append(t)
        back = False
        for c in t:
            if back:
                back = False
            elif c == '\\':
                back = True
            elif c == '"':
                quoted = not quoted

    a.append(''.join(p))

    return [dequote(v) for v in a if v]



class ShellCommand(binding.Component):
    protocols.advise(
        instancesProvide = [running.IRerunnable]
    )

    interactor = binding.Obtain('..')
    shell = binding.Obtain('interactor/shell')

    def run(self, stdin, stdout, stderr, environ, argv):
        optpat, minarg, maxarg = getattr(self, 'args', ('', 0, 0))

        retval = None

        try:
            opts, args = getopt(argv[1:], optpat)
            opts = dict(opts)
            if len(args) < minarg or len(args) > maxarg:
                raise SyntaxError
        except:
            print >>stderr, 'usage:', self.__doc__
            return

        try:
            retval = self.cmd(
                cmd=argv[0], opts=opts, args=args,
                stdin=stdin, stdout=stdout, stderr=stderr, environ=environ
            )
        except:
            sys.excepthook(*sys.exc_info()) # XXX

        return retval
