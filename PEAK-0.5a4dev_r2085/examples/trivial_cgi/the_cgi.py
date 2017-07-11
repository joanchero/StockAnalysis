from peak.api import *
from types import ModuleType
from StringIO import StringIO

class DemoCGI(binding.Component):

    protocols.advise(
        instancesProvide = [running.IWSGIApplication]
    )

    runCount = 0

    def __call__(self, env, start_response):

        self.runCount += 1

        output = StringIO()

        print >>output, "I've been run %d times." % self.runCount
        print >>output
        print >>output, "Environment"
        print >>output, "-----------"

        ei = env.items(); ei.sort()
        for k,v in ei:
            print >>output, '%-20s = %r' % (k,v)

        print >>output

        import sys
        names = dict(
            [(mod.__name__,None)
                for mod in sys.modules.values() if type(mod) is ModuleType
            ]
        ).keys()

        names.sort()

        print >>output, "Modules Loaded (%d total)" % len(names)
        print >>output, "--------------------------"

        for n in names:
            print >>output, n

        start_response("200 OK", [('Content-Type','text/plain')])
        return [output.getvalue()]


