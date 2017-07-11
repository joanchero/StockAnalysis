"""N2 Main Program"""

from peak.api import *
from peak.running.commands import AbstractCommand, InvocationError
from peak.running import options
from peak.util.readline_stack import *
from peak.util.imports import importString
from peak.util.columns import lsFormat

import sys, os, code, __main__

from interfaces import *
import ns, sql

vars_ns = PropertyName('peak.n2')

class N2(AbstractCommand):

    # We put this here so help(n2) will work in the interpreter shell

    """PEAK and pdb are already imported for you.
c is bound to the object you looked up, or the initial context.

cd(x)\t\tlike c = c[x]
cd()\t\tsets c back to the original value
pwd\t\tinfo about c
ls()\t\tshow contents of c
"""

    usage = """usage: peak n2 [options] [name]"""

    idict = __main__.__dict__
    width = 80    # XXX screen width

    py_anyway = binding.Make(lambda: False,
        options.Set('-e', value=True,
        help='if name lookup fails, go into python interactor anyway'
    ))

    force_py = binding.Make(lambda: False,
        options.Set('-p', value=True,
        help='use python interactor even if there is a more' + \
            ' specific interactor'
    ))

    adapt_to = binding.Make(lambda: None,
        options.Set('-I', type=str, metavar='INTERFACE',
        help='adapt looked-up object to INTERFACE, specified as an' + \
            ' import string (implies -e)'
    ))

    [options.option_handler('-i', type=str, metavar='URL',
    help='read input from named URL / filename')]
    def set_input(self, parser, optname, optval, remaining_args):
        f = config.getStreamFactory(self, optval)
        self.stdin = f.open('t', autocommit=True)
    
    def _run(self):
        args = self.parsed_args
        if len(args) > 1:
            raise InvocationError('too many arguments')

        cprt = 'Type "copyright", "credits" or "license" for more information.'
        help = 'Type "help" or "help(n2)" for help.'

        self.banner = 'PEAK N2 (Python %s on %s)\n%s\n%s' % (
            sys.version.split(None, 1)[0], sys.platform, cprt, help)

        self.idict['n2'] = self

        exec 'from peak.api import *' in self.idict
        exec 'import pdb' in self.idict

        for cmd in ('cd','ls'):
            self.idict[cmd] = getattr(self, 'py_' + cmd)

        storage.begin(self)

        try:
            if args:
                c = naming.lookup(self, args[0])
            else:
                c = naming.InitialContext(self)

            if self.adapt_to is not None:
                iface = importString(self.adapt_to)
                c = adapt(c, iface)
                self.py_anyway = True
        except:
           if self.force_py or self.py_anyway:
                c = None
                sys.excepthook(*sys.exc_info()) # XXX
                print >>self.stderr
           else:
                raise

        self.idict['c'] = self.idict['__c__'] = c
        self.idict['pwd'] = `c`

        self.handle(c)

        try:
            storage.abort(self)
        except:
            pass

        return 0


    def get_pwd(self):
        return self.idict['c']


    def get_home(self):
        return self.idict['__c__']


    def execute(self, code):
        exec code in self.idict


    def getvar(self, var, default=NOT_GIVEN):
        v = self.idict.get(var, NOT_GIVEN)
        if v is NOT_GIVEN:
            v = vars_ns.of(self).get('.' + var, NOT_GIVEN)
        if v is NOT_GIVEN:
            v = default
        if v is NOT_GIVEN:
            raise KeyError, var
        else:
            return v


    def setvar(self, var, val):
        if var == 'c':
            raise KeyError, "can't change protected variable"

        self.idict[var] = val


    def unsetvar(self, var):
        if var == 'c':
            raise KeyError, "can't change protected variable"

        try:
            del self.idict[var]
        except:
            pass

    def listvars(self):
        return self.idict.keys()


    def do_cd(self, c):
        self.idict['c'] = c
        self.idict['pwd'] = r = `c`


    def __repr__(self):
        return self.__doc__


    def interact(self, c=NOT_GIVEN, n2=NOT_GIVEN):
        if c is NOT_GIVEN:
            c = self.get_pwd()

        if n2 is NOT_GIVEN:
            n2 = self

        b = self.banner
        if c is not None:
            b += '\n\nc = %s\n' % `c`

        pushRLHistory('.n2_history', True, None, self.environ)
        code.interact(banner=b, local=self.idict)
        popRLHistory()


    def handle(self, c):
        if self.force_py:
            interactor = self
        else:
            binding.suggestParentComponent(self, None, c)
            interactor = adapt(c, IN2Interactor, self)
            binding.suggestParentComponent(self, None, interactor)

        interactor.interact(c, self)


    def readline(self, prompt):
        if self.stdin is sys.stdin:
            return raw_input(prompt)
        else:
            l = self.stdin.readline()
            if not l:
                raise EOFError
            else:   
                return l[:-1]

    # Extra builtins in the python shell

    def py_cd(self, arg=None):
        if arg is None:
            c = self.idict['__c__']
        else:
            c = self.idict['c']
            c = c[arg]

        self.do_cd(c)

        print >>self.stdout, 'c = %s' % self.idict['pwd']


    def py_ls(self):
        c = self.idict['c']
        c = adapt(c, naming.IReadContext, None)
        if c is None:
            print >>self.stderr, "c doesn't support the IReadContext interface."
        else:
            for k in c.keys():
                print >>self.stdout, str(k)


    def printColumns(self, stdout, l, sort=True, rev=False):
        stdout.writelines(lsFormat(self.width, l, sort=sort, reverse=rev))
