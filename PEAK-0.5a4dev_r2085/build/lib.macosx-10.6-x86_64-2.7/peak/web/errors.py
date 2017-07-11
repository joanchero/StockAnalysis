from peak.api import *
from interfaces import *
from cStringIO import StringIO
import sys
__all__ = ['WebException', 'NotFound', 'NotAllowed', 'UnsupportedMethod']

class WebException(Exception):

    protocols.advise( instancesProvide = [IWebException,IHTTPHandler] )

    binding.metadata(
        httpStatus = security.Anybody,
        args = security.Anybody,
        template = security.Anybody,
        exc_info = security.Anybody,
        traversedName = security.Anybody,
        # ...?
    )

    httpStatus = '500 Internal Error'
    traversedName = None
    levelName = 'ERROR'

    def __init__(self, ctx, *args):
        Exception.__init__(self, *args)
        self.ctx = ITraversalContext(ctx)   # Fail unless ctx supplied!

    def template(self):
        skin = self.ctx.skin
        try:
            return skin.getResource('/peak.web/error_%s' % self.httpStatus)
        except NotFound:
            try:
                return skin.getResource('/peak.web/standard_error')
            except NotFound:
                return self     # XXX

    template = binding.Make(template)



    def handle_http(self,ctx):
        return (
            self.httpStatus, [('Content-type','text/plain')],
            [self.__class__.__name__+str(self.args)]
        )


    def handleException(self, ctx, exc_info, retry_allowed=1):

        try:
            policy = ctx.policy
            self.exc_info = exc_info

            storage.abortTransaction(policy.app)

            # XXX note that the following assumes exc_info is available as
            # XXX sys.exc_info(); will this always be the case?
            policy.log.log(self.levelName,"ERROR:",exc_info=exc_info)

            ctx = self.ctx.clone(current=self, environ=ctx.environ.copy())
            ctx.environ['wsgi.input'] = StringIO('')

            s,h,b = ctx.childContext('template',self.template).renderHTTP()

            if s[:3]=='200':
                s = self.httpStatus     # replace with our error status

            return s, h, b

        finally:
            # Don't allow exc_info to leak, even if the above resulted in
            # an error
            ctx = exc_info = self.exc_info = None








class NotFound(WebException):
    httpStatus = '404 Not Found'
    levelName = 'DEBUG'


class NotAllowed(WebException):
    httpStatus = '403 Forbidden'
    levelName = 'INFO'


class UnsupportedMethod(WebException):
    httpStatus = '405 Method Not Allowed'





























