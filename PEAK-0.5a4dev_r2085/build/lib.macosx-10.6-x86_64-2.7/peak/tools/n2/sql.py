"""
SQL Interactor
"""

from peak.api import *
from commands import *
from interfaces import *
from peak.util.readline_stack import *

from tempfile import mktemp
import sys, os, time, re


varpat = re.compile('\\$\\{((?:[a-zA-Z0-9_\\.]+)|(?:=[^}]+))\\}')


def bufname(s):
    """comvert buffer name to canonical form
    ignoring leading ! on user-defined buffers"""

    if s in ('!.', '!!'):
        return s
    elif s.startswith('!'):
        return s[1:]

    return s


class SQLInteractor(storage.TransactionComponent):

    editor = binding.Obtain(PropertyName('__main__.EDITOR'), default='vi')

    shell = binding.Obtain('..')
    con = binding.Require('The SQL connection')

    state = ''
    pushbuf = binding.Make(list)
    bufs = binding.Make(dict)
    buf = ''
    line = 1
    semi = -1
    
    is_outside = False
    txnAttrs = storage.TransactionComponent.txnAttrs + ('is_outside',)


    def obnames(self):
        """Object names for completer"""

        si = adapt(self.con, storage.ISQLObjectLister, None)
        if si is not None:
            return [x.obname
                for x in si.listObjects(False,
		('table','view','proc','synonym'))]

        return []

    obnames = binding.Make(obnames, suggestParent=False)


    def prompt(self):
        p = self.getVar('sql.prompt')
        p = p.replace('$L', str(self.line))
        p = p.replace('$S', self.state)
        p = p.replace('$T', self.is_outside and 'U' or '')
        return p



    def interact(self, object, shell):
        binding.suggestParentComponent(shell, None, object)

        self.joinedTxn      # ensure we're in the current PEAK transaction
        self.con.connection # ensure it's opened immediately

        self.quit = False

        pushRLHistory('.n2sql_history', self.complete,
            ' \t\n`~@#%^&*()=+[]|;:\'",<>/?', self.shell.environ)

        while not self.quit:
            try:
                l = self.readline(self.prompt()) + '\n'
            except KeyboardInterrupt:
                print >>shell.stderr, '^C'
                continue
            except EOFError:
                print >>shell.stdout
                popRLHistory()
                return

            sl = l.strip()
            if ';' in sl:
                sl = sl.split(';', 1)[0].strip()

            if sl:
                cmd = sl.split(None, 1)[0].lower()

                if self.handleCommand(cmd, l) is not NOT_FOUND:
                    continue

            self.line += 1

            self.updateState(l)
            semi = self.semi

            if semi >= 0:
                b = self.getBuf()
                b, cmd = b[:semi] + '\n', b[semi+1:]
                self.setBuf(b)

                self.handleCommand('go', 'go ' + cmd)

        popRLHistory()



    def getVar(self, name):
        return self.shell.getvar(name, '')


    def substVar(self, s):
        s = varpat.split(s)
        for i in range(1, len(s), 2):
            v = s[i]
            if v.startswith('='):
                try:
                    v = eval(s[i][1:], self.shell.idict, self.shell.idict)
                except Exception, x:
                    v = "${%s:ERROR:%s}" % (v, x)
            else:
                v = self.getVar(s[i])
            s[i] = str(v)

        return ''.join(s)



    def getBuf(self, name='!.'):
        name = bufname(name)
        if name.startswith('$'):
            try:
                return str(self.getVar(name[1:]))
            except:
                return ''

        return self.bufs.get(name, '')



    def setBuf(self, val, name='!.', append=False):
        name = bufname(name)

        if name.startswith('$'):
            name = name[1:]
            if append:
                self.shell.setvar(name, self.getVar(name) + val)
            else:
                self.shell.setvar(name, val)
        elif append:
            self.bufs[name] = self.bufs.get(name, '') + val
        else:
            self.bufs[name] = val



    def resetBuf(self):
        self.state = ''; self.line = 1; self.semi = - 1
        self.setBuf('')



    def command(self, cmd):
        return getattr(self, 'cmd_' + cmd.replace('-', '_'), None)



    def handleCommand(self, cmd, l):
        shell = self.shell

        r = NOT_FOUND

        cmd = cmd.lower()
        if cmd[0] == '\\' or cmd in (
            'go','commit','abort','rollback','help'
        ):
            if cmd[0] == '\\':
                cmd = cmd[1:]

            cmdobj = self.command(cmd)
            if cmdobj is None:
                print >>shell.stderr, "command '%s' not found. Try 'help'." % cmd

                return
            else:
                cmdinfo = parseCmd(self, self.substVar(l), shell)
                try:
                    r = cmdobj.run(
                        cmdinfo['stdin'], cmdinfo['stdout'], cmdinfo['stderr'],
                        cmdinfo['environ'], cmdinfo['argv']
                    )
                finally:
                    for f in cmdinfo['close']:
                        f.close()            

                    del cmdinfo

            if r is True:
                self.redraw(self.shell.stdout, True)

        return r



    def showResults(self, c, opts, stdout, stderr):
        kw = {}

        if opts.has_key('-h'):
            kw['header'] = False

        if opts.has_key('-f'):
            kw['footer'] = False
                
        v = opts.get('-d')
        if v is not None:
            kw['delim'] = v
                
        v = opts.get('-N')
        if v is not None:
            kw['null'] = v
                
        c.dumpTo(stdout, format = opts.get('-m'), **kw)


       
    def command_names(self):
        l = [k for k in dir(self) if k.startswith('cmd_')]
        l2 = [k[4:].replace('_','-') for k in l
            if getattr(getattr(self, k), 'noBackslash', False)]
        l = ['\\'+k[4:].replace('_','-') for k in l]
        l.sort(); l2.sort()

        return l2 + l



    class cmd_go(ShellCommand):
        """go [-N null] [-d delim] [-m style] [-x code] [-r code] [-p] [-h] [-f] [-n] -- submit current input

-N null\tuse given string to represent NULL
-d delim\tuse specified delimiter
-m style\tuse specified format (see \\styles for a list)
-h\t\tsuppress header
-f\t\tsuppress footer
-n\t\tdon't expand variables in SQL
-x\t\texecute python code with "cursor" bound to results, instead
\t\tof printing
-r\t\texecute python code per row with "row" bound, instead of
\t\tprinting
-p\t\tdrop into python interactor with "cursor" bound, instead of
\t\tprinting"""

        noBackslash = True

        args = ('N:d:m:hfnx:r:p', 0, 0)

        def cmd(self, cmd, opts, args, stdout, stderr, **kw):
            try:
                i = self.interactor.getBuf()
                if i.strip():
                    if self.interactor.state:
                        print >>stderr, "Please finish comment or quotes first."
                        return
                else:
                    i = self.interactor.getBuf('!!')
                    if not i.strip():
                        self.interactor.resetBuf()
                        return

                if opts.has_key('-n'):
                    sql = i
                else:
                    sql = self.interactor.substVar(i)

                con = self.interactor.con
                c = con(sql, multiOK=True, outsideTxn=self.interactor.is_outside)

                ccode = opts.get('-x')
                rcode = opts.get('-r')
                pymode = opts.has_key('-p')

                if ccode or rcode or pymode:
                    shell = self.shell
                
                    if ccode or pymode:
                        shell.setvar('cursor', c)
                        try:
                            if ccode:
                                shell.execute(ccode)
                            if pymode:
                                shell.interact()
                        finally:
                            shell.unsetvar('cursor')

                    if rcode:
                        try:
                            for row in c:
                                shell.setvar('row', row)
                                shell.execute(rcode)
                        finally:
                            shell.unsetvar('row')
                else:
                    self.interactor.showResults(c, opts, stdout, stderr)

                self.interactor.setBuf(i, name='!!')

                self.interactor.resetBuf()
            except KeyboardInterrupt:
                print >>stderr, '^C'
                self.interactor.resetBuf()
            except: # con.Exceptions:
                # currently the error is logged
                # sys.excepthook(*sys.exc_info()) # XXX
                self.interactor.resetBuf()

    cmd_go = binding.Make(cmd_go)



    class cmd_abort(ShellCommand):
        """abort -- abort current transaction
rollback -- abort current transaction"""

        noBackslash = True

        args = ('', 0, 0)

        def cmd(self, cmd, stderr, **kw):
            if not self.interactor.txnSvc.isActive():
                print >>stderr, "No transaction active."
            else:
                storage.abortTransaction(self)
                storage.beginTransaction(self)
                self.interactor.joinedTxn
                self.interactor.resetBuf()

    cmd_rollback = binding.Make(cmd_abort)
    cmd_abort = binding.Make(cmd_abort)



    class cmd_commit(ShellCommand):
        """commit -- commit current transaction"""

        noBackslash = True

        args = ('', 0, 0)

        def cmd(self, cmd, stderr, **kw):
            if self.interactor.getBuf().strip():
                print >>stderr, "Use GO or semicolon to finish outstanding input first"
            elif not self.interactor.txnSvc.isActive():
                print >>stderr, "No transaction active."
            else:
                storage.commitTransaction(self)
                storage.beginTransaction(self)
                self.interactor.joinedTxn
                self.interactor.resetBuf()

    cmd_commit = binding.Make(cmd_commit)



    class cmd_reset(ShellCommand):
        """\\reset -- empty input buffer"""

        args = ('', 0, 0)

        def cmd(self, cmd, **kw):
            self.interactor.resetBuf()

    cmd_reset = binding.Make(cmd_reset)



    class cmd_outside(ShellCommand):
        """\\outside -- begin execution outside a database transaction"""

        args = ('', 0, 0)

        def cmd(self, cmd, stderr, **kw):
            if self.interactor.con.dbTxnStarted:
                print >>stderr, "Already active in a transaction; commit or abort first."
            else:
                self.interactor.is_outside = True

            self.interactor.resetBuf()

    cmd_outside = binding.Make(cmd_outside)



    class cmd_exit(ShellCommand):
        """\\exit -- exit SQL interactor
\\quit -- exit SQL interactor"""

        args = ('', 0, 0)

        def cmd(self, cmd, **kw):
            self.interactor.quit = True

    cmd_quit = binding.Make(cmd_exit)
    cmd_exit = binding.Make(cmd_exit)



    class cmd_python(ShellCommand):
        """\\python [code] -- enter python interactor or run code"""

        args = ('', 0, sys.maxint)

        def cmd(self, cmd, args, **kw):
            if args:
                try:
                    exec ' '.join(args) in self.shell.idict
                except:
                    sys.excepthook(*sys.exc_info()) # XXX
            else:
                self.shell.interact()

    cmd_python = binding.Make(cmd_python)



    class cmd_buf_copy(ShellCommand):
        """\\buf-copy dest [src] -- copy buffer src to dest

default for src is '!.', the current input buffer"""

        args = ('', 1, 2)

        def cmd(self, cmd, args, stdout, **kw):
            src = '!.'
            if len(args) == 2:
                src = args[1]

            self.interactor.setBuf(self.interactor.getBuf(src), name=args[0])

            if args[0] == '!.':
                return True

    cmd_buf_copy = binding.Make(cmd_buf_copy)



    class cmd_buf_get(ShellCommand):
        """\\buf-get src -- like \buf-append !. src"""

        args = ('', 1, 1)

        def cmd(self, cmd, args, stdout, **kw):
            self.interactor.setBuf(self.interactor.getBuf(args[0]), append=True)

            return True

    cmd_buf_get = binding.Make(cmd_buf_get)



    class cmd_buf_append(ShellCommand):
        """\\buf-append dest [src] -- append buffer src to dest

default for src is '!.', the current input buffer"""

        args = ('', 1, 2)

        def cmd(self, cmd, args, stdout, **kw):
            src = '!.'
            if len(args) == 2:
                src = args[1]

            self.interactor.setBuf(self.interactor.getBuf(src), name=args[0],
                append=True)

            if args[0] == '!.':
                return True

    cmd_buf_append = binding.Make(cmd_buf_append)



    class cmd_buf_save(ShellCommand):
        """\\buf-save [-a] filename [src] -- save buffer src in a file

-a\tappend to file instead of overwriting"""

        args = ('a', 1, 2)

        def cmd(self, cmd, opts, args, stderr, **kw):
            mode = 'w'
            if opts.has_key('-a'):
                mode = 'a'

            src = '!.'
            if len(args) == 2:
                src = args[1]

            try:
                f = open(args[0], mode)
                f.write(self.interactor.getBuf(src))
                f.close()
            except:
                sys.excepthook(*sys.exc_info()) # XXX

    cmd_buf_save = binding.Make(cmd_buf_save)



    class cmd_buf_load(ShellCommand):
        """\\buf-load [-a] filename [dest] -- load buffer dest from file

-a\tappend to buffer instead of overwriting"""

        args = ('a', 1, 2)

        def cmd(self, cmd, opts, args, stderr, **kw):
            try:
                dest = '!.'
                if len(args) == 2:
                    dest = args[1]

                f = open(args[0], 'r')
                l = f.read()
                self.interactor.setBuf(l, append=opts.has_key('-a'), name=dest)

                f.close()

                l = self.interactor.getBuf(dest)
                if l and not l.endswith('\n'):
                    self.interactor.setBuf('\n', append=True, name=dest)

            except:
                sys.excepthook(*sys.exc_info()) # XXX

            if dest == '!.':
                return True

    cmd_buf_load = binding.Make(cmd_buf_load)



    class cmd_buf_show(ShellCommand):
        """\\buf-show -- show buffer list
\\buf-show [buf] -- show named buffer"""

        args = ('', 0, 1)

        def cmd(self, cmd, args, stdout, **kw):
            if len(args) == 1:
                stdout.write(self.interactor.getBuf(args[0]))
            else:
                l = self.interactor.bufs.keys()
                l.sort()
                stdout.write('\n'.join(l))
                stdout.write('\n')

            stdout.flush()

    cmd_buf_show = binding.Make(cmd_buf_show)



    class cmd_buf_edit(ShellCommand):
        """\\buf-edit -- use external editor on current input buffer"""

        args = ('r:w:', 0, 0)

        def cmd(self, cmd, opts, stderr, **kw):
            t = mktemp()
            f = open(t, 'w')
            f.write(self.interactor.getBuf(opts.get('-r', '!.')))
            f.close()
            r = os.system('%s "%s"' % (self.interactor.editor, t))
            if r:
                print >>stderr, '[edit file unchanged]'
            else:
                f = open(t, 'r')
                l = f.read()
                f.close()
                wr = opts.get('-w', '!.')
                self.interactor.setBuf(l, name=wr)
                if l and not l.endswith('\n'):
                    self.interactor.setBuf('\n', append=True, name=wr)

            os.unlink(t)

            return True

    cmd_e = binding.Make(cmd_buf_edit)
    cmd_buf_edit = binding.Make(cmd_buf_edit)



    class cmd_source(ShellCommand):
        """\\source [-r] filename -- interpret input from file

-r\treset input buffer before sourcing file"""

        args = ('r', 1, 1)

        def cmd(self, cmd, opts, args, stderr, **kw):
            try:
                f = open(args[0], 'r')
                l = f.read()
                if l[-1] == '\n':
                    l = l[:-1]
                l = l.split('\n')
                l.reverse()
                self.interactor.pushbuf = l + self.interactor.pushbuf
                f.close()

                return opts.has_key('-r')
            except:
                sys.excepthook(*sys.exc_info()) # XXX

    cmd_source = binding.Make(cmd_source)



    class cmd_help(ShellCommand):
        """\\help [cmd] -- help on commands"""

        noBackslash = True

        args = ('', 0, 1)

        def cmd(self, stdout, stderr, args, **kw):
            if args:
                c = self.interactor.command(args[0].lstrip('\\'))
                if c is None:
                    print >>stderr, 'help: no such command: ' + args[0]
                else:
                    print c.__doc__
            else:
                print >>stdout, 'Available commands:\n'
                self.shell.printColumns(
                    stdout, self.interactor.command_names(), sort=False)

    cmd_help = binding.Make(cmd_help)



    class cmd_reconnect(ShellCommand):
        """\\reconnect -- abort current transaction and reconnect to database"""

        args = ('', 0, 0)

        def cmd(self, cmd, **kw):
            self.interactor.con.closeASAP()
            storage.abortTransaction(self)

            try:
                del self.obnames
            except:
                pass

            self.interactor.con.connection
            storage.beginTransaction(self)
            self.interactor.joinedTxn
            self.interactor.resetBuf()

    cmd_reconnect = binding.Make(cmd_reconnect)



    class cmd_redraw(ShellCommand):
        """\\redraw -- redraw current input buffer"""

        args = ('', 0, 0)

        def cmd(self, cmd, **kw):
            self.interactor.redraw(self.shell.stdout)

    cmd_redraw = binding.Make(cmd_redraw)



    class cmd_echo(ShellCommand):
        """\\echo msg -- print message"""

        args = ('-n', 0, sys.maxint)

        def cmd(self, cmd, opts, args, stdout, **kw):
            stdout.write(' '.join(args))
            if not opts.has_key('-n'):
                stdout.write('\n')
            stdout.flush()

    cmd_echo = binding.Make(cmd_echo)



    class cmd_sleep(ShellCommand):
        """\\sleep secs -- sleep for 'secs' seconds"""

        args = ('', 1, 1)

        def cmd(self, cmd, args, stderr, **kw):
            try:
                s = float(args[0])
            except:
                print >>stderr, "%s: invalid number '%s'" % (cmd, args[0])
                return

            time.sleep(s)

    cmd_sleep = binding.Make(cmd_sleep)



    class cmd_set(ShellCommand):
        """\\set name=val [name2=val2] [...] -- set variables"""

        args = ('', 1, sys.maxint)

        def cmd(self, cmd, opts, args, stderr, **kw):
            for x in args:
                try:
                    k, v = x.split('=', 1)
                except:
                    print >>stderr, "%s: invalid syntax '%s'" % (cmd, x)
                    continue

                try:
                    self.shell.setvar(k, v)
                except KeyError:
                    print >>stderr, "%s: unable to set '%s'" % (cmd, args[0])

    cmd_set = binding.Make(cmd_set)



    class cmd_styles(ShellCommand):
        """\\styles -- list available output styles"""
        
        args = ('', 0, 0)
        
        def cmd(self, stdout, **kw):
            base = PropertyName('peak.cursor.formatters.*')
            skip = len(base.asPrefix())
        
            l = [v[skip:] for v in config.iterKeys(self, base)]
            
            self.shell.printColumns(stdout, l)
            
    cmd_styles = binding.Make(cmd_styles)


    class cmd_describe(ShellCommand):
        """\\describe [-d delim] [-m style] [-h] [-f] [-v] [name] -- describe objects in database, or named object

-d delim\tuse specified delimiter
-m style\tuse specified format (see \\styles for a list)
-h\t\tsuppress header
-f\t\tsuppress footer
-v\t\tverbose; give more information"""

        args = ('d:m:hfv', 0, 1)

        def cmd(self, cmd, opts, args, stdout, stderr, **kw):
            if args:
                print >>stderr, "Feature not implemented yet."
            else:
                si = adapt(self.interactor.con, storage.ISQLObjectLister, None)
                if si is None:
                    print >>stderr, "%s: database doesn't support describe" % cmd
                else:
                    c = si.listObjects('-v' in opts)
                    self.interactor.showResults(c, opts, stdout, stderr)

    cmd_describe = binding.Make(cmd_describe)



    class cmd_extract(ShellCommand):
        """\\extract [-n [-x ext]] name -- extract DDL for named object
        
-n\t\textract to a file with an automatically generated name
-x ext\t\tadditional file extension for -n mode"""

        args = ('nx:', 1, 1)

        def cmd(self, cmd, opts, args, stdout, stderr, **kw):
            fnext = {
                'table' :   'TBL',       'trigger' : 'TRG',
                'view'  :   'VIEW',      'proc' : 'PRC',
            }
        
            xi = adapt(self.interactor.con, storage.ISQLDDLExtractor, None)
            if xi is None:
                print >>stderr, "%s: database doesn't support extraction" % cmd
            else:
                ot, ddl = xi.getDDLForObject(args[0])
                if ddl is None:
                    print >>stderr, "%s: can't extract DDL for %s" % (cmd, args[0])
                else:
                    f = stdout
                    n = None
                    
                    if opts.has_key('-n'):
                        n = args[0] + '.' + fnext.get(ot, ot.upper()) + \
                            opts.get('-x', '')
                            
                        f = open(n, 'w')

                    f.write(ddl)
                    
                    if n is not None:
                        f.close()
                        
                
    cmd_extract = binding.Make(cmd_extract)



    class cmd_cd(ShellCommand):
        """\\cd [directoryname] -- change directory, or print current directory"""
    
        args = ('', 0, 1)
        
        def cmd(self, cmd, opts, args, stdout, stderr, **kw):
            if args:
                try:
                    os.chdir(args[0])
                except:
                    sys.excepthook(*sys.exc_info()) # XXX
            else:
                print >>stdout, os.getcwd()

    cmd_cd = binding.Make(cmd_cd)


        
    class cmd_htmldump(ShellCommand):
        """\\htmldump [-f] [-x table[,table,...]] -- dump entire database as HTML document

-f\t\t\tsuppress footer (rowcount)
-x table[,table,...]\texclude tables from result"""

        args = ('fx:', 0, 0)

        def cmd(self, cmd, opts, args, stdout, stderr, **kw):
            con = self.interactor.con
            si = adapt(con, storage.ISQLObjectLister, None)
            if si is None:
                print >>stderr, "%s: database doesn't support object listing" % cmd
                return

            exclude = dict([
                (k.strip(), 1) for k in opts.get('-x', '').split(',')
            ]).has_key
            
            tl = si.listObjects(obtypes=['table'])
            tl = [r.obname for r in tl if not exclude(r.obname)]
            tl.sort()

            print >>stdout, "<html><body>"

            for t in tl:
                c = con('select * from %s' % t)
                c.dumpTo(stdout, format="ddt",
                    footer=(not opts.has_key('-f')),
                    title="Contents of table %s" % t
                )

                print >>stdout, "<br>"

            print >>stdout, "</body></html>"
                            

    cmd_htmldump = binding.Make(cmd_htmldump)



    def redraw(self, stdout, add_hist=False):
        b = self.getBuf()
        self.resetBuf()
        out = self.shell.stdout

        if b.endswith('\n'):
            b = b[:-1]

        b = b.split('\n')

        for l in b:
            addRLHistoryLine(l)
            l += '\n'
            stdout.write(self.prompt())
            stdout.write(l)

            self.line += 1

            self.updateState(l)



    def updateState(self, s):
        state = self.state

        i = 0
        for c in s:
            if not state:
                if c in '\'"/':
                    state = c
                elif c == ';' and self.semi < 0:
                    self.semi = len(self.getBuf()) + i
            elif state == '/':
                if c == '*':
                    state = 'C'
                elif c == ';' and self.semi < 0:
                    self.semi = len(self.getBuf()) + i
                else:
                    state = ''
            elif state == 'C':
                if c == '*':
                    state = c
            elif state == '*':
                if c == '/':
                    state = ''
                else:
                    state = 'C'
            elif state in ("'", '"'):
                if c == state:
                    state = 'D' + c
            elif state[0] == 'D':
                if c == state[1]:
                    state = state[1]
                elif c == '/':
                    state = c
                elif c == ';' and self.semi < 0:
                    self.semi = len(self.getBuf()) + i
                else:
                    state = ''
            i += 1

        self.state = state
        self.setBuf(s, append=True)


    def readline(self, prompt):
        if self.pushbuf:
            l = self.pushbuf.pop()
            self.shell.stdout.write(prompt + l + '\n')
            return l
        else:
            return self.shell.readline(prompt)


    def complete(self, s, state):
        if state == 0:
            #print s
            if s.startswith('!'):
                self.matches = m = []
                for b in self.bufs.keys():
                    if not b.startswith('!'):
                        b = '!' + b
                    m.append(b)
            elif s.startswith('${'):
                self.matches = ['${' + k + '}' for k in self.vars.keys()]
            elif s.startswith('$'):
                self.matches = ['$' + k for k in self.vars.keys()]
            else:
                self.matches = self.command_names() + self.obnames

            self.matches = [x for x in self.matches if x.startswith(s)]

        try:
            return self.matches[state]
        except IndexError:
            return None


protocols.declareAdapter(
    lambda con, proto: SQLInteractor(con=con),
    provides = [IN2Interactor],
    forProtocols = [storage.ISQLConnection]
)
