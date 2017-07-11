from protocols import Interface, Attribute
from peak.security.interfaces import ISecurityContext
import protocols
from peak.api import PropertyName, NOT_GIVEN
from peak.binding.interfaces import IComponent

__all__ = [
    'IWebTraversable', 'IInteractionPolicy', 'IAuthService', 'IWebException',
    'RESOURCE_PREFIX', 'DEFAULT_METHOD', 'APPLICATION_LOG', 'NAMESPACE_NAMES',
    'IDOMletState', 'IHTTPHandler', 'IHTTPApplication', 'INamespaceHandler',
    'IDOMletNode',    'IDOMletNodeFactory', 'IPlace', 'ITraversalContext',
    'IDOMletElement', 'IDOMletElementFactory', 'ISkin', 'IPolicyInfo',
    'IConfigurableLocation', 'IViewService',
    'VIEW_NAMES', 'TEMPLATE_SCHEMA', 'SITEMAP_SCHEMA', 'LOCATION_ID',
    'IDOMletRenderable',
]

DEFAULT_METHOD    = PropertyName('peak.web.defaultMethod')
RESOURCE_PREFIX   = PropertyName('peak.web.resourcePrefix')
APPLICATION_LOG   = PropertyName('peak.web.appLog')
NAMESPACE_NAMES   = PropertyName('peak.web.namespaces')
VIEW_NAMES        = PropertyName('peak.web.views')
TEMPLATE_SCHEMA   = PropertyName('peak.web.template_schema')
SITEMAP_SCHEMA    = PropertyName('peak.web.sitemap_schema')
LOCATION_ID       = lambda lid: PropertyName('peak.web.locations.'+lid)
















class IPolicyInfo(Interface):

    """Standard informational attributes for interaction policy"""

    app = Attribute("""The underlying application object""")
    log = Attribute("""Default 'logs.ILogger' for interactions""")

    resourcePrefix = Attribute("""Name that starts path to resources""")
    defaultMethod  = Attribute("""Default method name (e.g. 'index_html')""")


class IAuthService(Interface):

    def getUser(environ):
        """Return a user object for the given WSGI 'environ'"""


class IViewService(Interface):

    def registerView(target,name,handler):
        """Register 'handler' to implement view 'name' for 'target'

        'target' must be a type, protocol, or 'None', and 'handler' must be an
        'INamespaceHandler'.  If 'target' is 'None', then the view is intended
        to apply to the view service itself, rather than to a content type.
        """















class IInteractionPolicy(IAuthService, IPolicyInfo, ISecurityContext):

    """Component holding cross-hit configuration and consolidated services"""

    def getSkin(name, default=None):
        """Return the named skin, or 'default'"""

    def getLayer(name, default=None):
        """Return the named layer, or 'default'"""

    def newContext(environ={},start=NOT_GIVEN,skin=None,user=NOT_GIVEN):
        """Create an initial 'ITraversalContext' based on 'environ', etc.

        If 'start' is not supplied, the policy's application object will be
        used as the 'current' location of the created context.  If 'skin' is
        not supplied, the default skin is used.  If 'user' is not
        supplied, it is looked up via 'getUser()'.
        """

    def beforeTraversal(environ):
        """Begin transaction before traversal"""

    def afterCall(environ):
        """Commit transaction after successful hit"""

    def handleException(environ, exc_info, retry_allowed=1):
        """Convert exception to a handler, and invoke it"""

    def ns_handler(ns,default=None):
        """Return an 'INamespaceHandler' for namespace 'ns', or 'default'"""











class ITraversalContext(Interface):

    """A traversed-to location

    Note: this inherits from 'security.IInteraction', so it also supports
    the 'user' attribute, 'allows()' method, and so on.
    """

    name         = Attribute("""Name of 'current'""")
    current      = Attribute("""Current object location""")
    environ      = Attribute("""WSGI (PEP 333) 'environ' mapping""")
    policy       = Attribute("""'IInteractionPolicy' for this hit""")
    user         = Attribute("""Current user of the application""")
    skin         = Attribute("""Current 'ISkin' for this hit""")
    url          = Attribute("""Current object's standard URL""")
    rootURL      = Attribute("""Application root URL""")
    absoluteURL  = Attribute("""Absolute canonical URL""")
    traversedURL = Attribute("""URL traversed to get to this context""")
    viewService  = Attribute("""Nearest 'IViewService' for this context""")

    def childContext(name,ob):
        """Return a new child context with name 'name' and current->'ob'"""

    def peerContext(name,ob):
        """Return a new peer context with name 'name' and current->'ob'"""

    def parentContext():
        """Return this context's parent, or self if no parent"""

    def traverseName(name, default=NOT_GIVEN):
        """Return a new context obtained by traversing to 'name'"""

    def renderHTTP():
        """Equivalent to 'IHTTPHandler(self.current).handle_http()'"""

    def getResource(path):
        """Return the named resource"""




    def shift():
        """Shift a path component from 'PATH_INFO' to 'SCRIPT_NAME'

        This modifies the context's (possibly shared) environment such that
        one path component is moved from the beginning of 'PATH_INFO' to the
        end of 'SCRIPT_NAME'.  The shifted path component is returned, or
        'None' if 'PATH_INFO' is empty.

        Before the shift, 'PATH_INFO' is normalized to eliminate empty path
        components and path components that contain a single dot, so these
        should never be returned.  Double-dot components, however, *are*
        returned, and 'SCRIPT_NAME' is adjusted accordingly (i.e., the trailing
        path component of 'SCRIPT_NAME' is stripped, if one is present).

        Note that this changes the 'environ' being used by this context and
        any parent or child contexts that share it.  Thus, it's usually only
        safe to use this method from within a 'handle_http()' method, such as
        when determining the next object to traverse to, if any.
        """

    def clone(**kw):
        """Create a duplicate context, using supplied keyword arguments

        Acceptable keyword arguments include: 'name', 'current', 'environ',
        'policy', 'skin', 'rootURL', 'user', 'previous', and
        'clone_from'.  Most of these just set the corresponding attribute on
        the new context, but the following names are special:

         'clone_from' -- an existing context to clone.  If supplied, its
           'user', 'skin', 'policy', and 'previous' attributes will
           be used as defaults for the corresponding keyword arguments, if
           they are not supplied.

         'previous' -- an existing context that will be used as the new
           context's parent context.
        """





    def requireAccess(qname, subject,
        name=None, permissionNeeded=NOT_GIVEN,user=NOT_GIVEN
    ):
        """'NotAllowed' unless 'user' has 'permissionNeeded' for 'subject'

        'qname' is used only for generating an appropriate error if permission
        isn't granted.  The other arguments are per the 'allows()' method of
        'security.IInteraction'.  There is no return value.
        """


    def allows(subject,name=None,permissionNeeded=NOT_GIVEN,user=NOT_GIVEN):
        """Return true if 'user' has 'permissionNeeded' for 'subject'

        If 'user' is not supplied, the traversal context's current user
        is checked.  If the permission is not supplied, the 'policy'
        object's 'permissionFor()' method is used to determine one.

        This method should return a true value, or a 'security.Denial()' with
        an appropriate 'message' value."""





















class IWebTraversable(Interface):

    """A component that supports path traversal"""

    def beforeHTTP(context):

        """Invoked before publication by 'IHTTPHandler' adapter

        This can be used to enforce any preconditions for interacting with this
        object via the web.  For example, an e-commerce "checkout" traversable
        might want to ensure that there is an active session and there are
        items in the user's cart, or that the connection is secure.

        This method is only invoked when the traversable is about to be
        traversed into via a web request, AND the target object does
        not have any other adaptation to 'IHTTPHandler'.  It is not invoked
        when app-server code traverses a location (e.g. by paths in page
        templates, including '++id++' paths that pass through a location but
        don't "stop" there).

        Traversables can take advantage of this to have different security
        restrictions for app-server code and via-the-web URL traversal.
        Resources, for example, do not do security checks in 'traverseTo()',
        only in 'beforeHTTP()', thus ensuring that app-server code can access
        all available resources, whether they are available to the user or not.

        This method must return either the passed-in context, or a new
        traversal context to be used in its place.  Note also that if your
        object implements 'IHTTPHandler', or you are implementing an adapter
        to 'IHTTPHandler', you must call this method yourself, since it is
        normally only invoked by PEAK's adapter from 'IWebTraversable' to
        'IHTTPHandler'.
        """

    def traverseTo(name, context, default=NOT_GIVEN):
        """Return next 'ITraversalContext', or raise 'NotAllowed'/'NotFound'"""

    def getURL(context):
        """Return this object's URL in traversal context 'context'"""


class IPlace(Interface):
    """Traversable component with a fixed location"""

    place_url = Attribute("Relative URL (no leading '/') from skin")


class IHTTPHandler(Interface):
    """A component for rendering an HTTP response"""

    def handle_http(ctx):
        """Return '(status,headers,output_iterable)' tuple

        For the definition of 'status', 'headers', and 'output_iterable',
        see PEP 333.
        """


class IHTTPApplication(IHTTPHandler):
    """An IHTTPHandler that handles exceptions, transactions, etc."""


class IWebException(Interface):
    """An exception that knows how it should be handled for a web app"""

    def handleException(environ,exc_info,retry_allowed=1):
        """Perform necessary recovery actions"""


class IResourceService(Interface):

    def getResource(path):
        """Return the named resource"""


class ISkin(IResourceService):
    """A resource container, and the root resource for its contents"""





class INamespaceHandler(Interface):
    """A function returning a new context for a given context/ns/name"""

    def __call__(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        """Return a new context relative to 'ctx' for 'namespace' and 'name'

        'qname' is the original URL path component that was being traversed.
        'ctx' is an 'ITraversalContext', and 'ob' is the target object (which
        may not be the same as 'ctx.current', if the handler is being reused
        as part of another handler).  'namespace' is the namespace
        identifier of 'qname', and 'name' is the remainder of 'qname'.

        The handler must return an appropriate new 'ITraversalContext', or
        raise an appropriate error.  If a 'default' other than 'NOT_GIVEN'
        is supplied, the handler should return the default instead of
        raising 'NotFound' when the target cannot be located.  Note: the
        handler must *not* wrap 'default' in a traversal context: checking
        for the returned default is the caller's responsibility."""























class IConfigurableLocation(IWebTraversable,IPlace,IViewService):

    """Location that can be configured via a sitemap file"""

    def addContainer(container,permissionNeeded=None):
        """Register 'container' for item lookups

        If 'permissionNeeded' is not None, then the container will not be
        checked when the user does not have the appropriate permission.
        Containers added later take precedence over containers added earlier,
        so in the sequence::

            loc.addContainer(x)
            loc.addContainer(y)

        items will be looked up in container 'y' before container 'x', so if
        there is an item with the same name in both, the one from 'y' will be
        used.

        Note that this is the opposite order from the order of appearance in
        a sitemap file!  This is because an included sitemap (using
        <location extends="otherfile">) is processed before the including
        sitemap's contents for the same location.  Thus, the sitemap parser
        reverses the order of items in a given file, so that lookup order
        matches the order in which items are read, but items in containers
        defined by an included sitemap are looked up after those in the
        containers defined by the including sitemap.
        """

    def registerLocation(location_id,path):
        """Register 'path' (relative to location) as target of 'location_id'

        The registered location can then be accessed using the '++id++'
        namespace."""







class IDOMletState(IComponent):

    """A component representing a DOMlet's current execution state"""

    def write(unicodeData):
        """Call this to write data to the output stream"""

    def findState(interface):
        """Return the nearest object supporting 'interface', or 'None'

        If the state supports the interface, the state is returned, otherwise
        the state's parent components are searched and the first parent
        supporting the interface is returned.  'None' is returned if no parent
        supports the requested interface."""

    def __getitem__(key):
        """Return variable named 'key', or raise 'KeyError'"""

    def withData(**data):
        """Return a new child state, with 'data' added to its variables"""

    def wrapContext(ctx):
        """Wrap 'ctx' in a decorator that adds this state's variables"""


















class IDOMletRenderable(Interface):

    """Something that can be rendered in a template"""

    def renderFor(ctx, state):
        """Write template's output by calling 'state.write()' 0 or more times

        'ctx' is an 'ITraversalContext' for the object being rendered  (e.g.
        the object the template is a method of).  'state' is an 'IDOMletState'
        component used to supply arbitrary properties/utilities to child
        DOMlets during template execution, and to provide access to the
        current output stream and 'IWebInteraction'.  Both of these
        parameters should be supplied to executed child nodes as-is, unless
        the current DOMlet wishes to change them.  (For example, a
        'TemplateDocument' will normally change the context to point to its
        traversal predecessor, rather than using itself as the target of
        rendering.)

        If a node wishes to add properties to the 'state' for its children,
        it should create a new 'IDOMletState' with the old 'state' as
        its parent, then supply the new state to child nodes's 'renderFor()'
        method.
        """


class IDOMletNode(IDOMletRenderable):

    """A component of a page template"""

    staticText = Attribute(
        """The static XML text that represents this node, or None if
        the node contains any dynamic content."""
    )

    # XXX should be some kind of parseInfo w/source file/line/column






class IDOMletNodeFactory(Interface):

    """Factory to produce a literal or text node"""

    def __call__(parentComponent, componentName=None, xml=u'',
        # XXX parse info
    ):
        """Create an IDOMletNode w/specified XML text

        'xml' will contain the text as it would appear in an XML document;
        i.e., it is already XML-escaped, so no further processing is required
        on output.

        Note that only the first two arguments are positional; the 'xml'
        argument must be supplied as a keyword."""


























class IDOMletElement(IDOMletNode):

    """A component representing an XML/HTML element"""

    def addChild(node):
        """Add 'node' (an 'IDOMletNode') to element's direct children"""

    def addParameter(name, element):
        """Declare 'element' (an 'IDOMletElement') as part of parameter 'name'

        Note that 'element' is not necessarily a direct child of the current
        element, and that this method may be called multiple times for the
        same 'name', if multiple 'define' nodes use the same name.
        It's up to the element to do any validation/restriction of parameter
        names/values."""


    tagFactory = Attribute(
        """'IDOMletElementFactory' to be used for non-DOMlet child tags"""
    )

    textFactory = Attribute(
        """'IDOMletNodeFactory' to be used for plain text child nodes"""
    )

    literalFactory = Attribute(
        """'IDOMletNodeFactory' to be used for literals (e.g. comments,
        processing instructions, etc.) within this element"""
    )












class IDOMletElementFactory(Interface):

    """Produce an 'IDOMletElement' from a source document element"""

    def __call__(parentComponent, componentName,
        tagName=u'', attribItems=(), nonEmpty=False,
        domletProperty=None, dataSpec=None, paramName=None,
        # XXX xmlns maps, parse info
    ):
        """Create an IDOMletElement w/specified attribs, etc.

        'tagName' -- the element tag name, exactly as it appeared in the source
        document

        'attribItems' -- a list of '(name,value)' tuples representing the
        source document attributes for this element, in the order they were
        defined, and only the supplied attributes (i.e. no DTD-implied default
        values).  Template markup attributes (domlet and define) are
        excluded.

        'nonEmpty' -- indicates that this element should always have an open
        and close tag, even if it has no children.  This is to support HTML.

        'domletProperty' -- the 'PropertyName' used to retrieve this factory
        (minus the 'peak.web.DOMlets.' prefix), or None if the source document
        didn't specify a DOMlet factory.

        'dataSpec' -- the data specifier from the source document's 'domlet'
        attribute, or an empty string.

        'paramName' -- the value of the 'define' attribute in the source
        document, or 'None' if not supplied.

        Note that only the first two arguments are positional; all others must
        be supplied as keywords."""






