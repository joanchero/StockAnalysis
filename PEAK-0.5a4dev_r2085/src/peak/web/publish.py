"""Publish 'peak.web' apps"""

from peak.api import *
from interfaces import *
from errors import NotFound, NotAllowed
from environ import StartContext, Context
from wsgiref.util import application_uri, setup_testing_defaults
from cStringIO import StringIO
from peak.security.api import Anybody
import os,sys

__all__ = [
    'NullAuthenticationService', 'InteractionPolicy', 'WSGIPublisher',
    'DefaultExceptionHandler', 'TraversalPath', 'TestPolicy',
]


class DefaultExceptionHandler(binding.Singleton):

    def handleException(self,ctx,exc_info,retry_allowed=1):

        policy = ctx.policy

        try:
            storage.abortTransaction(policy.app)

            # XXX note that the following assumes exc_info is available as
            # XXX sys.exc_info; will this always be the case?
            policy.log.exception("ERROR:")

            return '500',[('Content-type','text/plain')],['An error occurred']

        finally:
            # Don't allow exc_info to leak, even if the above resulted in
            # an error
            exc_info = None





class TraversalPath(naming.CompoundName):

    """Name that knows how to do 'IWebTraversable' traversal"""

    syntax = naming.PathSyntax(
        direction=1,
        separator='/'
    )

    def traverse(self, ctx, wrapper=lambda ctx:ctx):

        path = iter(self)
        part = path.next()

        if not part:
            # Deliberately set 'name' of context to 'None' so that
            # 'traversedURL' will break with a TypeError if you try
            # to access it; going to an "absolute" traversal path is
            # an "escape" reserved for template paths, not URLs
            ctx = Context(None,wrapper(ctx),ctx.environ,ctx,clone_from=ctx)
        else:
            # reset to beginning
            path = iter(self)

        for part in path:
            if part:
                ctx = ctx.traverseName(part)

        return ctx


class NullAuthenticationService:

    protocols.advise(
        instancesProvide=[IAuthService]
    )

    def getUser(self, environ):
        return None


class InteractionPolicy(binding.Configurable, security.Context):

    protocols.advise(
        instancesProvide = [IInteractionPolicy],
    )

    app            = binding.Require("The application", [security.Anybody])
    log            = binding.Obtain(APPLICATION_LOG)

    defaultMethod  = binding.Obtain(DEFAULT_METHOD, [security.Anybody])
    resourcePrefix = binding.Obtain(RESOURCE_PREFIX, [security.Anybody])

    _authSvc       = binding.Make(IAuthService, adaptTo=IAuthService)

    getUser = binding.Delegate('_authSvc')

    ns_handler    = binding.Make(lambda self: NAMESPACE_NAMES.of(self).get)
    _getSkinName  = binding.Obtain(PropertyName('peak.web.getSkinName'))


    def newContext(self,environ=None,start=NOT_GIVEN,skin=None,user=NOT_GIVEN):

        if environ is None:
            environ = {}

        if user is NOT_GIVEN:
            user = self.getUser(environ)

        if skin is None:
            skin = self.getSkin(self._getSkinName(environ,user))

        if start is NOT_GIVEN:
            start = self.app

        root_url = application_uri(environ)

        return StartContext('', start, environ,
            policy=self, skin=skin, user=user, rootURL=root_url
        )


    def beforeTraversal(self, environ):
        """Begin transaction before traversal"""
        storage.beginTransaction(self.app)


    def afterCall(self, ctx):
        """Commit transaction after successful hit"""
        storage.commitTransaction(self.app)


    def handleException(self, ctx, exc_info, retry_allowed=1):
        """Convert exception to a handler, and invoke it"""
        try:
            handler = IWebException(exc_info[1], DefaultExceptionHandler)
            return handler.handleException(
                ctx, exc_info, retry_allowed
            )
        finally:
            # Don't allow exc_info to leak, even if the above resulted in
            # an error
            exc_info = None


    layerMap = binding.Make( config.Namespace('peak.web.layers') )

    def getLayer(self,layerName,default=None):
        ob = self.layerMap.get(layerName,default)
        return ob


    skinMap = binding.Make( config.Namespace('peak.web.skins') )

    def getSkin(self, name, default=None):
        ob = self.skinMap.get(name,default)
        binding.suggestParentComponent(self,name,ob)
        return ob





class TestPolicy(InteractionPolicy):

    """Convenient interaction policy to use for tests, experiments, etc."""

    app = binding.Obtain('..')

    def newContext(self,environ=None,start=NOT_GIVEN,skin=None,user=NOT_GIVEN):
        # Set up defaults for test environment
        if environ is None:
            environ = {}
        setup_testing_defaults(environ)
        return super(TestPolicy,self).newContext(
            environ, start, skin, user
        )

    def simpleTraverse(self, path, run=True):

        path = str(adapt(path, TraversalPath))  # Normalize path, verify syntax

        if not path.startswith('/'):
            path ='/'+path

        ctx = self.newContext({'SCRIPT_NAME':'', 'PATH_INFO':path})

        if run:
            ctx.environ['wsgi.input'] = StringIO('')
            ctx.environ['wsgi.errors'] = StringIO()
            status, headers, body = ctx.renderHTTP()
            return ''.join(body)

        while True:
            part = ctx.shift()
            if part is None:
                return ctx
            ctx = ctx.traverseName(part)






class WSGIPublisher(binding.Component):

    """Publish an arbitrary component as a WSGI application, using peak.web"""

    protocols.advise(
        instancesProvide=[running.IWSGIApplication],
    )

    # The fromApp method is registered as an adapter factory for
    # arbitrary components to IWSGIApplication, in peak.running.interfaces.
    # If we registered it here, it wouldn't be usable unless peak.web
    # was already imported, which leads to bootstrap problems, at least
    # with very trivial web apps (like examples/trivial_web).

    def fromApp(klass, app, protocol=None):
        return klass(app, app=app)

    fromApp = classmethod(fromApp)

    app    = binding.Require("Application root to publish")
    mkPolicy = binding.Obtain(config.FactoryFor(IInteractionPolicy))
    policy = binding.Make(
        lambda self: self.mkPolicy(self,app=self.app)
    )

    def __call__(self, environ, start_response):
        """PEP 333 "application" callable"""
        s,h,b = self._handle_http(environ)
        start_response(s,h)
        return b











    def _handle_http(self,environ):

        policy  = self.policy
        ctx = policy.newContext(environ)

        try:
            policy.beforeTraversal(ctx)
            result = ctx.renderHTTP()
            policy.afterCall(ctx)
            return result
        except:
            return policy.handleException(ctx, sys.exc_info())





























