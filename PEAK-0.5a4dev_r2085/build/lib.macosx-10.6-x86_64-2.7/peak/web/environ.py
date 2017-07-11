"""Functions to manipulate traversal context/environment

    TODO:

    * a function to replace outgoing MIME headers (e.g. to set content type,
      length)

    * functions to create outgoing cookies and parse incoming ones

    * Docstrings! and an intro to the 'environ' concept
"""

__all__ = [
    'Context', 'StartContext',
    'simpleRedirect', 'clientHas','parseName', 'traverseResource',
    'traverseView', 'traverseSkin', 'traverseAttr', 'traverseItem',
    'traverseDefault', 'traverseLocationId', 'relativeURL',
]

from interfaces import *
import protocols, posixpath, os, re
from cStringIO import StringIO
from peak.api import *
import errors
from wsgiref.util import shift_path_info, setup_testing_defaults, request_uri
from peak.security.api import Anybody, allow
from dispatch import generic
from dispatch.strategy import default













def relativeURL(base,url):
    """Convert absolute 'url' to be relative to 'base', if possible"""

    same = 0
    base_parts = base.split('/')
    url_parts = url.split('/')

    for b,u in zip(base_parts,url_parts):
        if b==u:
            same+=1
        else:
            break
    if same<3:
        return url

    parts = []
    if len(base_parts)==same:
        parts.append(base_parts[-1])

    parts.extend(['..'] * (len(base_parts)-same-1))
    parts.extend(url_parts[same:])
    return '/'.join(parts) or './'



















ns_match = re.compile(r"\+\+([A-Za-z_]\w*)\+\+|").match

def parseName(name):
    """Return 'ns,nm' pair for 'name'

    If 'name' begins with '"@@"', 'ns' will equal 'view', and 'nm' will be
    the remainder of 'name'.  If 'name' begins with a '"++"'-bracketed
    Python identifier, such as '"++foo_27++"', the identifier will be returned
    in 'ns', and the remainder of 'name' in 'nm'.  Otherwise, 'ns' will be
    an empty string, and 'nm' will be 'name'.
    """
    if name.startswith('@@'):
        return 'view',name[2:]
    match = ns_match(name)
    return (match.group(1) or ''), name[match.end(0):]


def traverseResource(ctx, ob, ns, nm, qname, default=NOT_GIVEN):
    if qname==ctx.policy.resourcePrefix:
        return ctx.childContext(qname, ctx.skin)
    if default is NOT_GIVEN:
        raise errors.NotFound(ctx, qname, ctx.current)
    return default


def traverseSkin(ctx, ob, ns, nm, qname, default=NOT_GIVEN):
    skin = ctx.policy.getSkin(nm)
    if skin is not None:
        return ctx.clone(skin=skin, rootURL=ctx.rootURL+'/'+qname)
    if default is NOT_GIVEN:
        raise errors.NotFound(ctx, qname, ctx.current)
    return default









class Context:
    """Keep track of current traversal state"""

    __metaclass__ = binding.Activator
    protocols.advise(instancesProvide=[ITraversalContext])

    # Public attributes
    current = binding.Require("Current object", [security.Anybody])
    previous = binding.Require("Parent context",[security.Anybody])

    environ = user = policy = skin = rootURL = \
        binding.Delegate('previous', [security.Anybody])

    # Private attrs
    getResource = binding.Delegate('skin')

    _clone_attrs = (
        'user','policy','skin','rootURL','previous','viewService'
    )

    def __init__(self,name,current,environ,previous=None,**kw):
        if kw: self._setup(kw)
        self.current = current
        self.name = name
        self.environ = environ
        if previous is not None:
            self.previous = previous
        if 'rootURL' in kw and self.previous is not None \
            and kw['rootURL']<>self.previous.rootURL:
                self.previous = self.previous.clone(rootURL=self.rootURL)

    def childContext(self,name,ob):
        return Context(name,ob,self.environ,self)

    def peerContext(self,name,ob):
        return self.clone(name=name,current=ob)

    def parentContext(self):
        return self.previous


    absoluteURL = binding.Make(
        lambda self: IWebTraversable(self.current).getURL(self),
        [security.Anybody]
    )

    traversedURL = binding.Make(
        lambda self: posixpath.join(self.previous.absoluteURL, self.name),
        [security.Anybody]
    )

    def renderHTTP(self):
        return IHTTPHandler(self.current).handle_http(self)

    def clone(self,**kw):
        for attr in 'name','current','environ':
            if attr not in kw:
                kw[attr] = getattr(self,attr)
        kw.setdefault('clone_from',self)
        return self.__class__(**kw)

    def _setup(self,kw):
        if 'clone_from' in kw:
            cfg = kw['clone_from'].__getattribute__
            del kw['clone_from']
            for attr in self._clone_attrs:
                if attr not in kw:
                    kw[attr] = cfg(attr)

        klass = self.__class__
        for k,v in kw.iteritems():
            if hasattr(klass,k):
                setattr(self,k,v)
            else:
                raise TypeError(
                    "%s constructor has no keyword argument %s" %
                    (klass, k)
                )




    def shift(self):
        environ = self.environ
        part = shift_path_info(environ)
        if part or part is None:
            return part

        # We got an empty string, so we just hit a trailing slash;
        # replace it with the default method:
        environ['SCRIPT_NAME'] += self.policy.defaultMethod
        return self.policy.defaultMethod

    def traverseName(self,name,default=NOT_GIVEN):
        ns, nm = parseName(name)
        if ns:
            handler = self.policy.ns_handler(ns,None)
            if handler is None:
                raise errors.NotFound(self,name,self.current)
            return handler(self, self.current, ns, nm, name, default)
        if name=='..':
            return self.parentContext()
        elif not name or name=='.':
            return self
        else:
            return IWebTraversable(self.current).traverseTo(name,self,default)

    def requireAccess(self,qname,*args,**kw):
        result = self.allows(*args,**kw)
        if not result:
            raise errors.NotAllowed(self,qname,
                getattr(result,'message',"Permission denied")
            )


    url = binding.Make(
        lambda self: relativeURL(
            request_uri(self.environ,False), self.absoluteURL
        ),
        [security.Anybody]
    )


    def viewService(self):
        vs = IViewService(self.current,None)
        if vs is not None:
            return vs
        if self.previous is None:
            return None
        return self.previous.viewService

    viewService = binding.Make(viewService)

    default = NOT_GIVEN
    nothing = None

    binding.metadata(default=Anybody, nothing=Anybody)

    def allows(self, subject,
        name=None, permissionNeeded=NOT_GIVEN, user=NOT_GIVEN
    ):
        if permissionNeeded is NOT_GIVEN:
            permissionNeeded = self.policy.permissionFor(subject,name)

        if user is NOT_GIVEN:
            user = self.user

        return self.policy.hasPermission(user,permissionNeeded,subject)
















class StartContext(Context):

    previous = None

    skin        = binding.Require("Traversal skin", adaptTo=ISkin)
    user        = binding.Require("Application user")
    rootURL     = binding.Require("Application root URL")
    absoluteURL = traversedURL = binding.Obtain('rootURL')

    policy       = binding.Require("Interaction policy",
        adaptTo=IInteractionPolicy
    )

    def parentContext(self):
        return self


def simpleRedirect(environ,location):
    if (environ.get("SERVER_PROTOCOL","HTTP/1.0")<"HTTP/1.1"):
        status="302 Found"
    else:
        status="303 See Other"
    return status,[('Location',location)],()


def clientHas(environ, lastModified=None, ETag=None):
    return False    # XXX














def traverseAttr(ctx, ob, ns, name, qname, default=NOT_GIVEN):

    perm = ctx.policy.permissionFor(ob,name)
    if perm is not None:
        # We have explicit permissions defined, so allow access after check
        loc = getattr(ob, name, NOT_FOUND)
        if loc is not NOT_FOUND:
            ctx.requireAccess(qname, ob, name, perm)
            return ctx.childContext(qname,loc)

    if default is NOT_GIVEN:
        raise errors.NotFound(ctx,qname,ob)
    return default


def traverseItem(ctx, ob, ns, name, qname, default=NOT_GIVEN):
    gi = getattr(ob,'__getitem__',None)
    if gi is not None:
        try:
            loc = ob[name]
        except (KeyError,IndexError,TypeError):
            pass
        else:
            ctx.requireAccess(qname, loc)
            return ctx.childContext(qname,loc)

    if default is NOT_GIVEN:
        raise errors.NotFound(ctx,qname,ob)
    return default












[dispatch.generic()]
def traverseView(ctx, ob, ns, name, qname, default=NOT_GIVEN):
    """XXX"""
    
[traverseView.when(default)]
def traverseView(ctx, ob, ns, name, qname, default):
    if default is NOT_GIVEN:
        raise errors.NotFound(ctx,qname,ob)
    return default



def traverseDefault(ctx, ob, ns, name, qname, default=NOT_GIVEN):

    loc = traverseAttr(ctx,ob,ns,name,qname,NOT_FOUND)

    if loc is NOT_FOUND:
        loc = traverseItem(ctx,ob,ns,name,qname,NOT_FOUND)

        if loc is NOT_FOUND:
            return traverseView(ctx,ob,ns,name,qname,default)

    return loc


















def traverseLocationId(ctx, ob, ns, name, qname, default=NOT_GIVEN):

    key = LOCATION_ID(name)
    orig_ctx = ctx

    while ctx is not None:
        cob = ctx.current

        try:
            gcd = cob._getConfigData
        except AttributeError:
            pass
        else:
            result = gcd(cob,key)
            if result is not NOT_FOUND:
                return result.traverse(ctx)

        ctx = ctx.previous

    if default is not NOT_GIVEN:
        return default

    raise errors.NotFound(orig_ctx,qname,ob)


















class TraversableAsHandler(protocols.Adapter):

    protocols.advise(
        instancesProvide=[IHTTPHandler],
        asAdapterForProtocols=[IWebTraversable]
    )

    def handle_http(self,ctx):

        ctx = self.subject.beforeHTTP(ctx)
        name = ctx.shift()

        if name is None:

            if ctx.environ['REQUEST_METHOD'] in ('GET','HEAD'):
                # Redirect to current location + '/'
                url = ctx.traversedURL+'/'
                if ctx.environ.get('QUERY_STRING'):
                    url = '%s?%s' % (url,ctx.environ['QUERY_STRING'])

                return simpleRedirect(ctx.environ,url)

            from errors import UnsupportedMethod
            raise UnsupportedMethod(ctx)

        return ctx.traverseName(name).renderHTTP()















