"""Run web-based app locally"""

from __future__ import generators
import sys, webbrowser
from cStringIO import StringIO
from peak.api import *
from peak.net.interfaces import IListeningSocket
import socket
from peak.running import options

from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

class Handler(WSGIRequestHandler):

    def log_message(self,format,*args):
        self.server.log.info(format,*args)

    def get_stderr(self):
        return self.server.stderr






















class WSGIServer(commands.EventDriven, WSGIServer):

    cgiCommand = binding.Require(
        "IWSGIApplication to invoke on each hit",
        adaptTo = running.IWSGIApplication
    )

    fileno  = binding.Delegate('socket')
    runInBrowser        = False
    RequestHandlerClass = Handler

    socketURL = binding.Obtain(
        PropertyName('peak.tools.server.url'), default='tcp://localhost:0'
    )

    socket = binding.Obtain(
        naming.Indirect('socketURL'), adaptTo=IListeningSocket
    )

    socket_address = binding.Make(lambda self: self.socket.getsockname())

    server_name = binding.Make(
        lambda self: socket.getfqdn(self.socket_address[0])
    )

    server_port = binding.Make(lambda self: self.socket_address[1])

    _getEnv = binding.Make(lambda self: self.setup_environ(), uponAssembly=True)

    def startBrowser(self,new=False,autoraise=True):
        import webbrowser
        if self.server_port<>80:
            port=':%d' % self.server_port
        else:
            port=''
        webbrowser.open("http://%s%s/" % (self.server_name,port),new,autoraise)

    def get_app(self):
        return self.cgiCommand


    eventLoop = binding.Obtain(events.IEventLoop)

    def serve_requests(self):

        yield self.eventLoop.sleep(); events.resume()

        if self.runInBrowser:
            self.startBrowser(True)

        while True:
            yield self.eventLoop.readable(self); events.resume()
            self.handle_request()

    serve_requests = binding.Make(
        events.taskFactory(serve_requests),uponAssembly=True
    )

    log = binding.Obtain('logger:tools.local_server')


class WSGILauncher(WSGIServer):

    runInBrowser = True


















class Serve(commands.CGIInterpreter):

    usage = """
Usage: peak serve [options] NAME_OR_URL ...

Run NAME_OR_URL as a WSGI application in a local webserver on the address given
by the 'peak.tools.server.url' property.  The object found at the specified
name or URL will be adapted to the 'running.IWSGIApplication' interface, and
then run in a local web server.
"""

    cgiWrapper = WSGIServer

    defaultURL = binding.Make(
        lambda self:
            naming.parseURL(self,
                config.lookup(
                    self,'peak.tools.server.url', default='tcp://localhost:0'
                )
            )
    )

    set_host = binding.Obtain('defaultURL/host',
        [options.Set('-h','--host',type=str,metavar="HOST",
            help="Host to listen on")]
    )

    set_port = binding.Obtain('defaultURL/port',
        [options.Set('-p','--port',type=int,metavar="PORT",
            help="Port to listen on")]
    )

    socketURL = binding.Make(
        lambda self: "tcp://%s:%s" % (self.set_host,self.set_port),
        offerAs = ['peak.tools.server.url']
    )





class Launch(Serve):

    usage = """
Usage: peak launch [options] NAME_OR_URL ...

Run NAME_OR_URL as a WSGI application in a local webserver on the address given
by the 'peak.tools.server.url' property.  The object found at the specified
name or URL will be adapted to the 'running.IWSGIApplication' interface, and
then run in a local web server.

This command is similar to the 'peak serve' command, except that it also
attempts to open the application in a web browser window.
"""
    cgiWrapper = WSGILauncher



def demo_service(environ,start_response):
    stdout = StringIO()
    print >>stdout, "Hello world!"
    print >>stdout
    h = environ.items(); h.sort()
    for k,v in h:
        print >>stdout, k,'=',`v`
    start_response("200 OK", [('Content-Type','text/plain')])
    return [stdout.getvalue()]

protocols.adviseObject(demo_service, [running.IWSGIApplication])

if __name__ == '__main__':
    WSGIServer(config.makeRoot(), cgiCommand=demo_service()).run()










