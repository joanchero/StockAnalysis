from __future__ import generators
from peak.api import *
from peak.util.imports import importString, importObject, whenImported
from peak.binding.components import Component, Make, getParentComponent
from peak.binding.components import iterParents,Configurable,Require,Delegate
from peak.binding.interfaces import IAttachable, IRecipe
from peak.naming.interfaces import IStreamFactory, IAddress
from peak.util.EigenData import EigenCell,AlreadyRead
from peak.util.FileParsing import AbstractConfigParser
from registries import FactoryFor
from interfaces import *
from protocols.advice import getMRO, determineMetaclass
from peak.model.enumerations import enum, Enumeration
import os.path

__all__ = [
    'ConfigMap', 'LazyRule', 'fileNearModule', 'packageFile', 'IniLoader',
    'Value', 'iterKeys', 'Namespace', 'iterValues',
    'CreateViaFactory', 'parentsProviding', 'parentProviding', 'lookup',
    'ServiceArea', 'XMLKey', 'processXML', 'XMLParser', 'getStreamFactory'
]


def _setCellInDict(d,key,value):
    cell = d.get(key)
    if cell is None:
        cell = d[key] = EigenCell()
    cell.set(value)

_emptyRuleCell = EigenCell()
_emptyRuleCell.set(lambda *args: NOT_FOUND)
_emptyRuleCell.exists()


def fileNearModule(moduleName,filename):
    """DEPRECATED: please switch to 'config.packageFile()' or a URL"""
    filebase = importString(moduleName+':__file__')
    import os; return os.path.join(os.path.dirname(filebase), filename)



def packageFile(moduleName,filename):

    """Return 'naming.IStreamFactory' for 'filename' in 'moduleName' package"""

    module = importString(moduleName)

    path = os.path.join(
        os.path.dirname(getattr(module,'__file__','')), *filename.split('/')
    )

    if hasattr(module,'__loader__') and hasattr(module.__loader__,'get_data'):
        from peak.naming.factories.openable import ImportLoaderFactory
        return ImportLoaderFactory(module.__loader__,moduleName,filename,path)

    from peak.naming.factories.openable import FileFactory
    return FileFactory(filename = path)




class XMLKind(Enumeration):
    """Allowed kinds for XMLKey instances"""

    attribute = enum()
    element = enum()
















class XMLKey:
    """XMLKey(kind,xmlns,name) -- key to look up XML elements and attributes

    Usage::

        # Get a key for the 'foo' element in XML namespace 'http://something'
        key = config.XMLKey('element','http://something','foo')

    'kind' must be a string equal to '"element"' or '"attribute"'.  'xmlns'
    should be an XML namespace URI, or an asterisk ('"*"').  'name' should
    be an unqualified XML element or attribute name, or an asterisk.  Asterisks
    indicate wildcards, similar to the way wildcards work in 'PropertyName'
    objects.  When an 'XMLKey' is used as a configuration key, it searches
    first for an exact match, then a wildcard name match with the same XML
    namespace, then a wildcard XML namespace match with the same element or
    attribute name, and finally it looks for a wildcard in both positions.
    (Note, however, that the 'element' and 'attribute' configuration namespaces
    are entirely disjoint, and do not overlap in any way; an XML element lookup
    will never return an XML attribute or vice versa.)

    'kind', 'xmlns', and 'name' are all accessible as attributes of an
    'XMLKey', so you can use them in wildcard rules, e.g.::

        [XML Attributes for http://something]
        * = some_module.someFunc(configKey.name)
    """

    protocols.advise(
        instancesProvide=[IConfigKey],
    )

    def __init__(self,kind,xmlns,name):
        self.kind = XMLKind(kind).name
        self.xmlns = xmlns
        self.name = name
        self.baseKey = (XMLKey,self.kind,xmlns,name)
        self.hashCode = hash(self.baseKey)

    def registrationKeys(self,depth=0):
        return [(self,0)]

    def parentKeys(self):
        return ()

    def lookupKeys(self):
        yield self

        if self.name<>'*':
            yield XMLKey(self.kind,self.xmlns,'*')
            if self.xmlns<>'*':
                yield XMLKey(self.kind,'*',self.name)
                yield XMLKey(self.kind,'*','*')

        elif self.xmlns<>'*':
            yield XMLKey(self.kind,'*',self.name)


    def __hash__(self):
        return self.hashCode

    def __cmp__(self,other):
        return cmp(self.baseKey,other)

    def __repr__(self):
        return "XMLKey%r" % (self.baseKey[1:],)

















class XMLParser(Component):
    """Wrap a SOX.NegotiatingParser for configuration-driven XML parsing

    'XMLParser' instances use their configuration context to obtain XML element
    and attribute defintions, as well as default XML namespaces from
    properties in 'peak.config.xml_namespaces', and parsing functions from
    properties in 'peak.config.xml_functions' (as well as from any keyword
    arguments supplied to the constructor).

    Default namespaces allow an XML document to optionally omit XML namespace
    declarations.  For example, this::

        [peak.config.xml_namespaces]
        pwt = "http://peak.telecommunity.com/DOMlets/"

    establishes that the namespace URI for the 'pwt' prefix will be the DOMlets
    namespace URI, unless the document explicitly defines otherwise.  Also, if
    there should be a default XML namespace for the document as a whole, you
    can set it with the 'peak.config.default_xml_namespace' property.
    Meanwhile, this::

        [peak.config.xml_functions]
        text = some_module.handleTopLevelText
        child = some_module.handleRootElement
        finish = some_module.getResult

    sets up the top-level parsing functions used by the 'SOX.NegotiatingParser'
    that this class uses to do the actual parsing.  You can also override or
    supplement these top-level functions by passing keyword arguments to the
    'XMLParser()' constructor.  (See 'peak.util.SOX.INegotiationData' for info
    on what each parsing function is for.)  Note that these functions are used
    only to parse the top-level document nodes, not any contained XML elements.

    The behavior for the contained XML elements and attributes is determined by
    the XML element and attribute definitions available in the XMLParser's
    configuration context.  These definitions must be 'IElementNegotiator' and
    'IAttributeNegotiator' functions, as defined in 'peak.util.SOX'.  So, for
    example, in::

        [XML Attributes for http://peak.telecommunity.com/DOMlets/]
        domlet = pwt.negotiateDomlet
        define = pwt.negotiateDefine

    the 'negotiateDomlet' and 'negotiateDefine' functions must implement the
    'peak.util.sox.IAttributeNegotiator' interface.
    """

    def __init__(self, parentComponent=NOT_GIVEN, componentName=None, **kw):
        Component.__init__(self,parentComponent,componentName,kwargs=kw)

    kwargs = binding.Make(dict)
    parserClass = binding.Obtain('import:peak.util.SOX.NegotiatingParser')

    def makeParser(self):
        """Return a configured NegotiatingParser"""

        p = self.parserClass()
        nspre = 'peak.config.xml_namespaces.'
        for key in iterKeys(self,nspre[:-1]):
            if '*' not in key:
                prefix = key[len(nspre):]
                p.addNamespace(prefix,lookup(self,key))

        defns = lookup(self,'peak.config.default_xml_namespace',NOT_FOUND)
        if defns is not NOT_FOUND:
            p.addNamespace('',defns)

        def lookupElement(ns,nm):
            if ns is None:
                nm=nm.split(':',1)[-1]
            return lookup(self,XMLKey('element',ns or '*',nm),None)
    
        def lookupAttribute(ns,nm):
            if ns is None:
                nm = nm.split(':',1)[-1]
            return lookup(self,XMLKey('attribute',ns or '*',nm),None)
    
        p.setLookups(lookupElement,lookupAttribute)
        return p


        
    def parseFunctions(self):
        """Return top-level parse function map based on kwargs and props"""
        kw = self.kwargs.copy()
        nspre = 'peak.config.xml_functions.'
        for key in iterKeys(self,nspre[:-1]):
            if '*' not in key:
                kw.setdefault(key[len(nspre):],lookup(self,key))
        return kw


    def parse(self,source):
        """Parse a stream source using the configured parser

        'source' should be a stream source (see 'config.getStreamFactory()')
        for the XML to be parsed.  Note that this method will only return a
        value if a 'finish' function is defined for the top-level document.
        The 'finish' function can be set as a 'peak.config.xml_functions'
        property, passed in via a keyword argument to the constructor, or it
        can be set by a 'start' function.
        """
        
        factory = getStreamFactory(self,source)
        stream = factory.open('t')
        try:
            return self.makeParser().parseStream(
                stream, self.parseFunctions(), factory.address
            )
        finally:
            stream.close()
        











def processXML(context,source,**kw):
    """Return the result of parsing 'source' using 'context' to control parsing

    This is basically a shortcut for 'XMLParser(context,**kw).parse(source)'.
    See 'config.XMLParser' for full documentation.  Also note that this
    function will only return a value if the parser has a 'finish' function
    defined.  See the 'parse' method of 'XMLParser' for more details.
    """
    return XMLParser(context,**kw).parse(source)


[dispatch.on('source')]
def getStreamFactory(context,source):
    """Return a 'naming.IStreamFactory' for 'source'

    Usage::

        factory = config.getStreamFactory(context,source)

    If 'source' is a 'naming.IStreamFactory', it is simply returned.
    If it is a string or Unicode object, it will be interpreted as
    either a filename or URL.  If it is a URL, it will be looked up
    in 'context'.  If it is a filename, a file-based stream factory will
    be returned.  (This is so that the configuration system can use filenames
    without the naming system configuration being bootstrapped yet.)

    This is a generic function, and you may define additional cases for it
    using its 'when()' method; e.g.::

        [config.getStreamFactory.when(MyType)]
        def getStreamFactory(context,source):
            '''Return a stream factory for 'source' (a 'MyType' instance)'''
    """








[getStreamFactory.when(IStreamFactory)]
def getStreamFactory_alreadyFactory(context,source):
    return source


[getStreamFactory.when([str,unicode])]
def getStreamFactory_fromString(context,source):
    from peak.naming.factories.openable import FileFactory,FileURL
    try:
        url = FileURL.fromFilename(source)
    except exceptions.InvalidName:
        url = naming.toName(source, FileURL.fromFilename)
    if isinstance(url,FileURL):
        return FileFactory(filename=url.getFilename())
    return IStreamFactory(naming.lookup(context,url))


[getStreamFactory.when(IAddress)]
def getStreamFactory_fromAddress(context,source):
    return IStreamFactory(naming.lookup(context,source))





















def iterValues(component, configKey):

    """Return iterator over all values of'configKey' for 'component'"""

    forObj = component
    configKey = adapt(configKey,IConfigKey)

    for component in iterParents(component):

        try:
            gcd = component._getConfigData
        except AttributeError:
            continue

        value = gcd(forObj, configKey)
        if value is not NOT_FOUND:
            yield value

    adapt(
        component,IConfigurationRoot,NullConfigRoot
    ).noMoreValues(component, configKey, forObj)



def lookup(component, configKey, default=NOT_GIVEN):

    """Return value for 'configKey' in context of 'component', or 'default'"""

    for value in iterValues(component, configKey):
        return value

    if default is NOT_GIVEN:
        raise exceptions.NameNotFound(configKey, resolvedObj = component)

    return default






def parentsProviding(component, protocol):

    """Iterate over all parents of 'component' that adapt to 'protocol'"""

    for parent in iterParents(component):
        c = adapt(parent,protocol,None)
        if c is not None:
            yield c


def parentProviding(component, protocol, default=NOT_GIVEN):
    """Return first parent providing 'protocol' for 'component', or 'default'"""

    for u in parentsProviding(component, protocol):
        return u

    if default is NOT_GIVEN:
        raise exceptions.NameNotFound(protocol, resolvedObj = component)

    return default


def iterKeys(component, configKey):

    """Iterate sub-keys of 'configKey' that are available from 'component'"""

    yielded = {}

    for ob in parentsProviding(component,IConfigSource):
        for key in ob._configKeysMatching(configKey):
            if key in yielded:
                continue
            yielded[key] = 1
            yield key







class CreateViaFactory(object):

    """'IRule' for one-time creation of target interface using FactoryFor()"""

    protocols.advise(
        classProvides=[IRule]
    )

    __slots__ = 'configKey'


    def __init__(self,configKey):
        self.configKey = adapt(configKey,IConfigKey)


    def __call__(self, propertyMap, configKey, targetObj):

        serviceArea = parentProviding(targetObj, IServiceArea)

        def create():
            factory = lookup(serviceArea, FactoryFor(self.configKey))

            if factory is NOT_FOUND:
                return factory

            instance = factory()
            binding.suggestParentComponent(serviceArea, None, instance)
            return instance

        return serviceArea.getService(self.configKey, create)











class ConfigMap(Component):

    rules = depth = keyIndex = lockedNamespaces = Make(dict)

    protocols.advise(
        instancesProvide=[IConfigurable]
    )

    def registerProvider(self, configKey, provider):
        """Register 'provider' under 'configKey'"""

        for key,depth in adapt(configKey, IConfigKey).registrationKeys():

            if self.depth.get(key,depth)>=depth:
                # The new provider is at least as good as the one we have
                lockedNamespaces = self.lockedNamespaces
                ckey = adapt(key, IConfigKey)
                for k in ckey.parentKeys():
                    if k in lockedNamespaces:
                        raise AlreadyRead(
                            "A namespace containing %r "
                            "has already been examined" % (configKey,)
                        )
                for k in ckey.parentKeys():
                    self.keyIndex.setdefault(k,{})[ckey] = True
                _setCellInDict(self.rules, key, provider)
                self.depth[key]=depth














    def _configKeysMatching(self, configKey):

        """Iterable over defined keys that match 'configKey'

        A key 'k' in the map is considered to "match" 'configKey' if any of
        'k.parentKeys()' are listed as keys in 'configKey.registrationKeys()'.
        You must not change the configuration map while iterating over the
        keys.  Also, keep in mind that only explicitly-registered keys are
        returned; for instance, load-on-demand rules will only show up as
        wildcard keys."""

        index = self._getBinding('keyIndex')

        if not index:
            return

        for key,depth in adapt(configKey,IConfigKey).registrationKeys():
            self.lockedNamespaces[key] = True
            for k in index.get(key,()):
                yield k





















    def _getConfigData(self, forObj, configKey):

        """Look up the requested value"""

        rules  = self.rules
        value  = NOT_FOUND
        xRules = []

        for name in configKey.lookupKeys():

            rule = rules.get(name)

            if rule is None:
                xRules.append(name)     # track unspecified rules

            elif rule is not _emptyRuleCell:

                value = rule.get()(self, configKey, forObj)

                if value is not NOT_FOUND:
                    break

        # ensure that unspecified rules stay that way, if they
        # haven't been replaced in the meanwhile by a higher-level
        # wildcard rule

        for name in xRules:
            rules.setdefault(name,_emptyRuleCell)

        return value











def Value(v):
    """Return an 'IRule' that always returns 'v'"""
    return lambda *args: v


class LazyRule(object):

    loadNeeded = True

    def __init__(self, loadFunc, prefix='*', **kw):
        self.load = loadFunc
        self.prefix = prefix
        self.__dict__.update(kw)


    def __call__(self, propertyMap, propName, targetObj):

        if self.loadNeeded:

            try:
                self.loadNeeded = False
                return self.load(propertyMap, self.prefix, propName)

            except:
                del self.loadNeeded
                raise

        return NOT_FOUND













from peak.naming.interfaces import IState

class NamingStateAsSmartProperty(protocols.Adapter):

    protocols.advise(
        instancesProvide = [ISmartProperty],
        asAdapterForProtocols = [IState],
    )

    def computeProperty(self, propertyMap, name, prefix, suffix, targetObject):

        from peak.naming.factories.config_ctx import PropertyPath
        from peak.naming.factories.config_ctx import PropertyContext

        ctx = PropertyContext(targetObject,
            creationParent = targetObject,
            nameInContext = PropertyPath(prefix[:-1]), # strip any trailing '.'
        )

        result = self.subject.restore(ctx, PropertyPath(suffix))

        rule = adapt(result, ISmartProperty, None)
        if rule is not None:
            result = rule.computeProperty(
                propertyMap, name, prefix, suffix, targetObject
            )

        return result













class IniLoader(Configurable):

    """Component that lazily loads its configuration from .ini file(s)"""

    protocols.advise(
        classProvides=[naming.IObjectFactory],
    )

    def __instance_offers__(self,d,a):
        pm = d[a] = ConfigMap(self)
        self.setupDefaults(pm)
        return pm

    __instance_offers__ = Make(__instance_offers__,
        offerAs=[IConfigurable], uponAssembly = True
    )

    iniFiles = Require("Sequence of filenames/URLs/factories to load")

    def setupDefaults(self, propertyMap):
        """Set up 'propertyMap' with default contents loaded from 'iniFiles'"""

        for file in self.iniFiles:
            if isinstance(file,tuple):
                # XXX do we really want to continue supporting this, now that
                # XXX you can call pkgFile directly?
                file = packageFile(*file)
            config.loadConfigFile(propertyMap, file)


    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        return klass(iniFiles = refInfo.addresses)

    getObjectInstance = classmethod(getObjectInstance)







class ServiceArea(Configurable):

    """Component that acts as a home for "global"-ish services"""

    protocols.advise(instancesProvide=[IServiceArea])

    __services = binding.Make('peak.util.EigenData:EigenDict')

    def getService(self,ruleKey,factory):
        return self.__services.get(ruleKey,NOT_FOUND,factory=factory)



class ConfigurationRoot(IniLoader, ServiceArea):

    """Default implementation for a configuration root.

    If you think you want to subclass this, you're probably wrong.  Note that
    you can have whatever setup code you want, called automatically from .ini
    files loaded by this class.  We recommend you try that approach first."""

    protocols.advise(instancesProvide=[IConfigurationRoot])

    iniFiles = ( packageFile('peak','peak.ini'), )

    def noMoreValues(self,root,configKey,forObj):
        pass

    def nameNotFound(self,root,name,forObj):
        return naming.lookup(forObj, name, creationParent=forObj)











class Namespace(object):
    """Traverse to another property namespace

    Use this in .ini files (e.g. '__main__.* = config.Namespace("environ.*")')
    to create a rule that looks up undefined properties in another property
    namespace.

    Or, use this as a way to treat a property namespace as a mapping object::

        myNS = config.Namespace("some.prefix", aComponent)
        myNS['spam.bayes']              # property 'some.prefix.spam.bayes'
        myNS.get('something',default)   # property 'some.prefix.something'

    Or use this in a component class to allow traversing to a property space::

        class MyClass(binding.Component):

            appConfig = binding.Make(
                config.Namespace('MyClass.conf')
            )

            something = binding.Obtain('appConfig/foo.bar.baz')

    In the example above, 'something' will be the component's value for the
    property 'MyClass.conf.foo.bar.baz'.  Note that you may not traverse to
    names beginning with an '_', and traversing to the name 'get' will give you
    the namespace's 'get' method, not the 'get' property in the namespace.  To
    obtain the 'get' property, or properties beginning with '_', you must use
    the mapping style of access, as shown above.

    NOTE: By default, 'Namespace' instances cache every key that's looked up in
    them.  If you are holding a reference to a namespace, and you expect an
    unbounded number of potential lookups, do not want references held to the
    results, or are looking up dynamically changing or dynamically created
    properties, you should disable caching via the 'cache=False' keyword arg."""

    def __init__(self, prefix, target=NOT_GIVEN, cache=True):
        self._prefix = PropertyName(prefix).asPrefix()
        self._target = target
        self._cache = cache; self._data = {}

    def __call__(self, suffix):
        """Return a sub-namespace for 'suffix'"""
        return self.__class__(
            PropertyName.fromString(self._prefix+suffix),self._target
        )

    def __getattr__(self, attr):
        if not attr.startswith('_'):
            ob = self.get(attr, NOT_FOUND)
            if ob is not NOT_FOUND:
                if self._cache and not hasattr(self.__class__,attr):
                    setattr(self,attr,ob)   # Cache for future use
                return ob
        raise AttributeError,attr


    def __getitem__(self, key):
        """Return the value of property 'key' within this namespace"""
        ob = self.get(key,NOT_FOUND)
        if ob is not NOT_FOUND:
            return ob
        raise KeyError,key


    def get(self,key,default=None):
        """Return property 'key' within this namespace, or 'default'"""

        if self._target is not NOT_GIVEN:
            if key in self._data:
                return self._data[key]

            result = lookup(
                self._target,PropertyName.fromString(self._prefix+key),default
            )
            if self._cache and result is not default:
                self._data[key] = result
            return result

        return default


    def __repr__(self):
        return "config.Namespace(%r,%r)" % (self._prefix,self._target)


    def keys(self):

        items = []

        if self._target is not NOT_GIVEN:

            prel = len(self._prefix)
            append = items.append
            yielded = {}

            for key in iterKeys(self._target,self._prefix+'*'):
                key = key[prel:]
                if key.endswith('?'):
                    key = key[:-1]
                elif key.endswith('*'):
                    continue
                if key not in yielded:
                    append(key)
                    yielded[key]=1

        return items
















class __NamespaceExtensions(protocols.Adapter):

    protocols.advise(
        instancesProvide = [ISmartProperty, IAttachable, IRecipe],
        asAdapterForTypes = [Namespace]
    )

    def computeProperty(self, propertyMap, name, prefix, suffix, targetObject):
        return config.lookup(
            targetObject, self.subject._prefix+suffix, default=NOT_FOUND
        )


    def setParentComponent(self, parentComponent, componentName=None,
        suggest=False
    ):

        pc = self.subject._target

        if pc is NOT_GIVEN:
            self.subject._target = parentComponent
            return

        elif suggest:
            return

        raise AlreadyRead(
            "%r already has target %r; tried to set %r"
                % (self.subject,pc,parentComponent)
        )


    def __call__(self,client,instDict,attrName):
        subject = self.subject
        return subject.__class__(subject._prefix[:-1], client, subject._cache)






