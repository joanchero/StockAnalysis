"""Basic binding tools"""

from __future__ import generators
from peak.api import *

from once import *
from once import _warnIfPermission
from interfaces import *
from attributes import *
from types import ModuleType
from peak.naming.names import toName, AbstractName, COMPOUND_KIND, IName
from peak.naming.syntax import PathSyntax
from peak.util.EigenData import AlreadyRead
from peak.config.interfaces import IConfigKey, IConfigurationRoot, \
    NullConfigRoot, IConfigurable
from peak.config.registries import ImmutableConfig
from peak.util.imports import importString, whenImported


__all__ = [
    'Component', 'Obtain', 'Require', 'Delegate', 'Configurable',
    'getRootComponent', 'getParentComponent', 'lookupComponent',
    'acquireComponent', 'notifyUponAssembly', 'PluginsFor', 'PluginKeys',
    'getComponentName', 'getComponentPath', 'ComponentName', 'iterParents',
    'hasParent',
]

from _once import BaseDescriptor

class _proxy(BaseDescriptor):

    def __init__(self,attrName):
        self.attrName = attrName

    def usageError(self):
        raise AttributeError, self.attrName

    def computeValue(self,ob,d,a): raise AttributeError, a



def iterParents(component,max_depth=100):

    """Iterate over all parents of 'component', up to 'max_depth'"""

    ct = max_depth

    while component is not None:
        yield component
        ct -=1
        if ct:
            component = getParentComponent(component)
        else:
            raise RuntimeError("maximum recursion limit exceeded", component)


def hasParent(component,parent):
    """Is 'component' within the hierarchy of 'parent'?"""
    for c in iterParents(component):
        if c is parent:
            return True
    return False




















def _setupCriterion(strategy):
    global HasParentCriterion, dispatch_by_hierarchy

    def dispatch_by_hierarchy(table, ob):
        for comp in iterParents(ob):
            oid = id(comp)
            if oid in table:
                return table[oid]
        return table[None]

    class HasParentCriterion(strategy.IdentityCriterion):
        __slots__ = ()
        ptr = strategy.IdentityCriterion.subject    # alias
        dispatch_function = staticmethod(dispatch_by_hierarchy)
        matches = strategy.AbstractCriterion.matches.im_func
        def __init__(self,component):
            super(HasParentCriterion,self).__init__(strategy.Pointer(component))
        def parent_criteria(self):
            return [HasParentCriterion(p) for p in iterParents(self.ptr.ref())]
        def __contains__(self,ob):
            if ob is not None:
                for comp in iterParents(ob.ref()):
                    if id(comp) == self.ptr:
                        return True
            return False

def _setupParse(predicates):
    [predicates.expressionSignature.when(
        # matches 'hasParent(expr,Const)'
        "expr in predicates.Call and expr.function == hasParent"
        " and len(expr.argexprs)==2 and expr.argexprs[1] in predicates.Const"
    )]
    def convertHasParentToCriterion(expr,criterion):
        typecheck = HasParentCriterion(expr.argexprs[1].value)
        if not criterion.truth:
            typecheck = ~typecheck
        return dispatch.strategy.Signature([(expr.argexprs[0],typecheck)])

whenImported('dispatch.strategy',_setupCriterion)
whenImported('dispatch.predicates',_setupParse)

def getComponentPath(component, relativeTo=None):

    """Get 'ComponentName' that would traverse from 'relativeTo' to 'component'

    If 'relativeTo' is 'None' or not supplied, the path returned is relative
    to the root component of 'component'.  Note that if supplied, 'relativeTo'
    must be an ancestor (parent, parent's parent, etc.) of 'component'."""

    path = []; root=None

    if relativeTo is None:
        root = getRootComponent(component)

    for c in iterParents(component):

        if c is root:
            path.append(''); break

        elif c is relativeTo:
            break

        path.append(getComponentName(c) or '*')

    path.reverse()
    return ComponentName(path)
















[dispatch.on('component')]
def getParentComponent(component):
    """Return parent of 'component', or 'None' if unknown or non-component

    This also works for module objects, and 'binding.ActiveClass' objects,
    for which the containing module or package is returned.

    This is a generic function, so you can add cases for additional object
    types using 'binding.getParentComponent.when()' as a decorator.
    """

[getParentComponent.when(IComponent)]
def get_parent_of_node(component):
    return component.getParentComponent()

[getParentComponent.when(ModuleType)]
def get_parent_of_module(component):
    m = '.'.join(component.__name__.split('.')[:-1])
    if m: return importString(m)
    return None

[getParentComponent.when(ActiveClass)]
def get_parent_of_ActiveClass(component):
    return component.__parent__[0]

[getParentComponent.when(object)]
def get_parent_of_object(component):
    return None













[dispatch.on('component')]
def getComponentName(component):
    """Return name of 'component', or 'None' if root or non-component

    This also works for module objects, and 'binding.ActiveClass' objects,
    for which the module or class' '__name__' is returned.

    This is a generic function, so you can add cases for additional object
    types using 'binding.getComponentName.when()' as a decorator.
    """

[getComponentName.when(IComponent)]
def get_name_of_node(component):
    return component.getComponentName()

[getComponentName.when(ModuleType)]
def get_name_of_module(component):
    return component.__name__.split('.')[-1]

[getComponentName.when(ActiveClass)]
def get_name_of_ActiveClass(component):
    return component.__cname__

[getComponentName.when(object)]
def get_name_of_object(component):
    return None















def getRootComponent(component):

    """Return the root component of the tree 'component' belongs to"""

    for component in iterParents(component):
        pass

    return component



def notifyUponAssembly(parent,child):

    """Call 'child.uponAssembly()' as soon as 'parent' knows all its parents"""

    try:
        nua = parent.notifyUponAssembly

    except AttributeError:

        parent = getParentComponent(parent)

        if parent is None:
            child.uponAssembly()
        else:
            notifyUponAssembly(parent,child)

    else:
        nua(child)












def acquireComponent(component, name):

    """Acquire 'name' relative to 'component', w/fallback to naming.lookup()

    'name' is looked for as an attribute of 'component'.  If not found,
    the component's parent will be searched, and so on until the root component
    is reached.  If 'name' is still not found, and the root component
    implements 'config.IConfigurationRoot', the name will be looked up in the
    default naming context, if any.  Otherwise, a 'NameNotFound' error will be
    raised."""

    prev = component

    for target in iterParents(component):

        ob = getattr(target, name, NOT_FOUND)

        if ob is not NOT_FOUND:
            return ob

        prev = target

    else:

        return adapt(
            prev, IConfigurationRoot, NullConfigRoot
        ).nameNotFound(
            prev, name, component
        )












class ComponentName(AbstractName):

    """Path between components

    Component Path Syntax

        Paths are '"/"' separated attribute names.  Path segments of '"."' and
        '".."' mean the same as they do in URLs.  A leading '"/"' (or a
        compound name beginning with an empty path segment), will be treated
        as an "absolute path" relative to the component's root component.

        Paths beginning with anything other than '"/"', '"./"', or '"../"' are
        acquired, which means that the first path segment will be looked
        up using 'acquireComponent()' before processing the rest of the path.
        (See 'acquireComponent()' for more details.)  If you do not want
        a name to be acquired, simply prefix it with './' so it is relative
        to the starting object.

        All path segments after the first are interpreted as attribute names
        to be looked up, beginning at the component referenced by the first
        path segment.  '.' and '..' are interpreted the same as for the first
        path segment.
    """

    nameKind = COMPOUND_KIND

    syntax = PathSyntax(
        direction = 1,
        separator = '/',
    )

    protocols.advise(
        instancesProvide=[IComponentKey]
    )







    def findComponent(self, component, default=NOT_GIVEN):

        if not self:  # empty name refers to self
            return component

        parts = iter(self)
        attr = parts.next()                 # first part
        pc = _getFirstPathComponent(attr)


        if pc:  ob = pc(component)
        else:   ob = acquireComponent(component, attr)

        resolved = []
        append = resolved.append

        try:
            for attr in parts:
                pc = _getNextPathComponent(attr)
                if pc:  ob = pc(ob)
                else:   ob = getattr(ob,attr)
                append(attr)

        except AttributeError:

            if default is not NOT_GIVEN:
                return default

            raise exceptions.NameNotFound(
                resolvedName = ComponentName(resolved),
                remainingName = ComponentName([attr] + [a for a in parts]),
                resolvedObj = ob
            )

        return ob






_getFirstPathComponent = dict( (
    ('',   getRootComponent),
    ('.',  lambda x:x),
    ('..', getParentComponent),
) ).get


_getNextPathComponent = dict( (
    ('',   lambda x:x),
    ('.',  lambda x:x),
    ('..', getParentComponent),
) ).get


def lookupComponent(component, name, default=NOT_GIVEN, adaptTo=None,
    creationName=None, suggestParent=True):

    """Lookup 'name' as a component key relative to 'component'

    'name' can be any object that implements or is adaptable to 'IComponentKey'.
    Such objects include 'peak.naming' names, interface objects, property
    names, and any custom objects you may create that implement 'IComponentKey'.
    Strings will be converted to a URL, or to a 'ComponentName' if they have
    no URL prefix.  If the key cannot be found, an 'exceptions.NameNotFound'
    error will be raised unless a 'default' other than 'NOT_GIVEN' is provided.
    """

    result = adapt(name, IComponentKey).findComponent( component, default )

    if adaptTo is not None:
        result = adapt(result,adaptTo)

    if suggestParent:
        suggestParentComponent(component,creationName,result)

    return result





# Declare that strings should be converted to names (with a default class
# of ComponentName), in order to use them as component keys
#
protocols.declareAdapter(
    lambda ob: toName(ob, ComponentName, 1),
    provides = [IComponentKey],
    forTypes = [str, unicode],
)


class ConfigFinder(object):

    """Look up utilities or properties"""

    __slots__ = 'ob'

    protocols.advise(
        instancesProvide = [IComponentKey],
        asAdapterForProtocols = [IConfigKey]
    )

    def __init__(self, ob):
        self.ob = ob

    def findComponent(self, component, default=NOT_GIVEN):
        return config.lookup(component, self.ob, default)

    def __repr__(self):
        return repr(self.ob)












class PluginKeys(object):
    """Component key that finds the keys of plugins matching a given key

    Usage::

        # get a sorted list of the keys to all 'foo.bar' plugins
        pluginNames = binding.Obtain( binding.PluginKeys('foo.bar') )

        # get an unsorted list of the keys to all 'foo.bar' plugins
        pluginNames = binding.Obtain(
            binding.PluginKeys('foo.bar', sortBy=None)
        )

    'sortBy' is either a false value or a callable that will be applied to
    each key to get a value for sorting purposes.  If set to a false value,
    the keys will be in the same order as yielded by 'config.iterKeys()'.
    'sortBy' defaults to 'str', which means the keys will be sorted based
    on their string form.
    """

    protocols.advise(
        instancesProvide = [IComponentKey],
    )

    def __init__(self, configKey, sortBy=str):
        self.configKey = adapt(configKey, IConfigKey)
        self.sortBy = sortBy


    def findComponent(self, component, default=NOT_GIVEN):

        keys = config.iterKeys(component, self.configKey)

        if self.sortBy:
            sortBy = self.sortBy
            keys = [(sortBy(k),k) for k in keys]
            keys.sort()
            return [k for (sortedBy,k) in keys]

        return list(keys)

class PluginsFor(PluginKeys):

    """Component key that finds plugins matching a configuration key

    Usage::

        # get a list of 'my.plugins.X' plugins, sorted by property name
        myPlugins = binding.Obtain( binding.PluginsFor('my.plugins') )

        # get an unsorted list of all 'foo.bar' plugins
        myPlugins = binding.Obtain(
            binding.PluginsFor('foo.bar', sortKeys=False)
        )

    This key type works similarly to 'PluginKeys()', except that it returns the
    plugins themselves, rather than their configuration keys.

    'sortBy' is either a false value or a callable that will be applied to
    each plugin's key to get a value for sorting purposes.  If set to a false
    value,  plugins will be in the same order as their keys are yielded by
    'config.iterKeys()'.  'sortBy' defaults to 'str', which means the plugins
    will be sorted based on the string form of the keys used to retrieve them.
    """

    def findComponent(self, component, default=NOT_GIVEN):
        keys = super(PluginsFor,self).findComponent(component)
        return [adapt(k,IComponentKey).findComponent(component) for k in keys]














class Obtain(Attribute):
    """'Obtain(componentKey,[default=value])' - finds/caches a needed component

    Usage examples::

        class someClass(binding.Component):

            thingINeed = binding.Obtain("path/to/service")
            otherThing = binding.Obtain(IOtherThing)
            aProperty  = binding.Obtain(PropertyName('some.prop'), default=42)

    'someClass' instances can then refer to their attributes, such as
    'self.thingINeed', instead of repeatedly calling
    'self.lookupComponent(someKey)'.

    The initial argument to the 'Obtain' constructor must be adaptable to
    'binding.IComponentKey'.  If a 'default' keyword argument is supplied,
    it will be used as the default in case the specified component key is not
    found.

    XXX need to document IComponentKey translations somewhere... probably
        w/IComponentKey"""

    default = NOT_GIVEN
    targetName = None

    def __init__(self,targetName,metadata=None,**kw):
        self.targetName = adapt(targetName, IComponentKey)
        kw['metadata']=metadata
        _warnIfPermission(kw)
        super(Obtain,self).__init__(**kw)

    def computeValue(self, obj, instanceDict, attrName):
        return self.targetName.findComponent(obj, self.default)

    def __repr__(self):
        if self.__doc__:
            return "binding.Obtain(%r):\n\n%s" % (self.targetName,self.__doc__)
        else:
            return "binding.Obtain(%r)" % (self.targetName,)

class SequenceFinder(object):

    """Look up sequences of component keys"""

    __slots__ = 'ob'

    protocols.advise(
        instancesProvide = [IComponentKey],
        asAdapterForProtocols = [protocols.sequenceOf(IComponentKey)]
    )

    def __init__(self, ob):
        self.ob = ob

    def findComponent(self, component, default=NOT_GIVEN):
        return tuple([ob.findComponent(component, default) for ob in self.ob])

























class Delegate(Make):

    """Delegate attribute to the same attribute of another object

    Usage::

        class PasswordFile(binding.Component):
            shadow = binding.Obtain('config:etc.shadow/')
            checkPwd = changePwd = binding.Delegate('shadow')

    The above is equivalent to this longer version::

        class PasswordFile(binding.Component):
            shadow = binding.Obtain('config:etc.shadow/')
            checkPwd = binding.Obtain('shadow/checkPwd')
            changePwd = binding.Obtain('shadow/changePwd')

    Because 'Delegate' uses the attribute name being looked up, you do not
    need to create a separate binding for each attribute that is delegated,
    as you do when using 'Obtain()'."""

    delegateAttr = None

    def __init__(self, delegateAttr, metadata=None, **kw):
        def delegate(s,d,a):
            return getattr(getattr(s,delegateAttr),a)
        kw['metadata']=metadata
        _warnIfPermission(kw)
        super(Delegate,self).__init__(delegate,delegateAttr=delegateAttr,**kw)

    def __repr__(self):
        if self.__doc__:
            return "binding.Delegate(%r):\n\n%s" % (
                self.delegateAttr,self.__doc__
            )
        else:
            return "binding.Delegate(%r)" % (self.delegateAttr,)




class Require(Attribute):

    """Placeholder for a binding that should be (re)defined by a subclass"""

    description = ''

    def __init__(self, description="", metadata=None, **kw):
        kw['description'] = description
        kw['metadata']=metadata
        _warnIfPermission(kw)
        super(Require,self).__init__(**kw)


    def computeValue(self, obj, instanceDict, attrName):
        raise NameError("Class %s must define %s; %s"
            % (obj.__class__.__name__, attrName, self.description)
        )

    def __repr__(self):
        if self.__doc__:
            return "binding.Require(%r):\n\n%s" % (
                self.description,self.__doc__
            )
        else:
            return "binding.Require(%r)" % (self.description,)
















class _Base(object):

    """Basic attribute management and "active class" support"""

    __metaclass__ = ActiveClass

    protocols.advise(
        instancesProvide = [IBindableAttrs]
    )

    def _setBinding(self, attr, value, useSlot=False):

        self._bindingChanging(attr,value,useSlot)

        if useSlot:
            getattr(self.__class__,attr).__set__(self,value)

        else:
            self.__dict__[attr] = value


    def _getBinding(self, attr, default=None, useSlot=False):

        if useSlot:
            val = getattr(self,attr,default)

        else:
            val = self.__dict__.get(attr,default)

        if val is not default:

            val = self._postGet(attr,val,useSlot)

            if val is NOT_FOUND:
                return default

        return val




    def _getBindingFuncs(klass, attr, useSlot=False):
        if useSlot:
            d = getattr(klass,attr)
        else:
            d = _proxy(attr)
        return d.__get__, d.__set__, d.__delete__

    _getBindingFuncs = classmethod(_getBindingFuncs)


    def _delBinding(self, attr, useSlot=False):

        self._bindingChanging(attr, NOT_FOUND, useSlot)

        if useSlot:
            d = getattr(self.__class__,attr).__delete__

            try:
                d(self)
            except AttributeError:
                pass

        elif attr in self.__dict__:
            del self.__dict__[attr]

    def _hasBinding(self,attr,useSlot=False):

        if useSlot:
            return hasattr(self,attr)
        else:
            return attr in self.__dict__


    def _bindingChanging(self,attr,newval,isSlot=False):
        pass


    def _postGet(self,attr,value,isSlot=False):
        return value


class Component(_Base):

    """Thing that can be composed into a component tree, w/binding & lookups"""

    protocols.advise(
        classProvides = [IComponentFactory],
        instancesProvide = [IComponent]
    )


    def __init__(self, parentComponent=NOT_GIVEN, componentName=None, **kw):

        # Set up keywords first, so state is sensible
        if kw:
            initAttrs(self,kw.iteritems())

        # set our parent component and possibly invoke assembly events
        if parentComponent is not NOT_GIVEN or componentName is not None:
            self.setParentComponent(parentComponent,componentName)

    lookupComponent = lookupComponent


    [dispatch.as(classmethod)]
    def fromZConfig(klass, section):

        """Classmethod: Create an instance from a ZConfig 'section'"""

        # ZConfig uses unicode for keys and defaults unsupplied values to None
        data = dict([(str(k),v) for k,v in section.__dict__.items()
            if v is not None])

        for skip in '_name','_matcher','_attributes':
            if skip in data and not hasattr(klass,skip):
                del data[skip]

        return klass(**data)




    def setParentComponent(self, parentComponent, componentName=None,
        suggest=False):

        pc = self.__parentSetting

        if pc is NOT_GIVEN:
            self.__parentSetting = parentComponent
            self.__componentName = componentName
            self.__parentComponent  # lock and invoke assembly events
            return

        elif suggest:
            return

        raise AlreadyRead(
            "Component %r already has parent %r; tried to set %r"
            % (self,pc,parentComponent)
        )

    __parentSetting = NOT_GIVEN
    __componentName = None

    def __parentComponent(self,d,a):

        parent = self.__parentSetting
        if parent is NOT_GIVEN:
            parent = self.__parentSetting = None

        d[a] = parent
        if parent is None:
            self.uponAssembly()
        elif (self.__class__.__attrsToBeAssembled__
            or self._getBinding('__objectsToBeAssembled__')):
                notifyUponAssembly(parent,self)

        return parent

    __parentComponent = Make(__parentComponent, suggestParent=False)



    def getParentComponent(self):
        return self.__parentComponent

    def getComponentName(self):
        return self.__componentName


    def _configKeysMatching(self, configKey):
        """Iterable over defined keys that match 'configKey'

        A key 'k' in the map is considered to "match" 'configKey' if any of
        'k.parentKeys()' are listed as keys in 'configKey.registrationKeys()'.
        You must not change the configuration map while iterating over the
        keys.  Also, keep in mind that only explicitly-registered keys are
        returned; for instance, load-on-demand rules will only show up as
        wildcard keys."""

        yielded = {}

        for cMap in self._config_maps():
            for key in cMap._configKeysMatching(configKey):
                if key in yielded:
                    continue
                yield key
                yielded[key] = 1


    def _config_maps(self):
        return [self.__class__.__class_offers__]


    def _getConfigData(self, forObj, configKey):

        attr = self.__class__.__class_offers__.lookup(configKey)

        if attr:
            return getattr(self, attr, NOT_FOUND)

        return NOT_FOUND


    def __class_offers__(klass,d,a):

        return ImmutableConfig(
            baseMaps = getInheritedRegistries(klass, '__class_offers__'),
            items = [(adapt(key,IConfigKey), attrName)
                for attrName, descr in klass.__class_descriptors__.items()
                    for key in getattr(descr,'offerAs',())
            ]
        )


    __class_offers__ = classAttr(Make(__class_offers__))


    def notifyUponAssembly(self,child):

        tba = self.__objectsToBeAssembled__

        if tba is None:
            child.uponAssembly()    # assembly has already occurred
        else:
            tba.append(child)       # save reference to child for callback

            if (len(tba)==1 and self.__parentSetting is not NOT_GIVEN
                and len(tba)==1 and not self.__class__.__attrsToBeAssembled__
            ):
                # Make sure our parent calls us, since we need to call a
                # child now, but would not have been registered ourselves.
                notifyUponAssembly(self.getParentComponent(),self)












    def uponAssembly(self):
        """Don't override this unless you can handle the reentrancy issues!"""
        tba = self.__objectsToBeAssembled__

        if tba is None:
            return

        self.__objectsToBeAssembled__ = None

        try:
            while tba:
                ob = tba.pop()
                try:
                    ob.uponAssembly()
                except:
                    tba.append(ob)
                    raise

            for attr in self.__class__.__attrsToBeAssembled__:
                getattr(self,attr)

        except:
            self.__objectsToBeAssembled__ = tba
            raise

    __objectsToBeAssembled__ = Make(list)


    def __attrsToBeAssembled__(klass,d,a):
        aa = {}
        map(aa.update, getInheritedRegistries(klass, '__attrsToBeAssembled__'))

        for attrName, descr in klass.__class_descriptors__.items():
            notify = getattr(descr,'uponAssembly',False)
            if notify: aa[attrName] = True

        return aa

    __attrsToBeAssembled__ = classAttr(Make(__attrsToBeAssembled__))


class Configurable(Component):

    protocols.advise(
        instancesProvide = [IConfigurable]
    )

    __instance_offers__ = Make(
        'peak.config.config_components:ConfigMap', offerAs=[IConfigurable]
    )

    def _getConfigData(self, forObj, configKey):

        value = self.__instance_offers__._getConfigData(forObj, configKey)

        if value is not NOT_FOUND:
            return value

        attr = self.__class__.__class_offers__.lookup(configKey)

        if attr:
            return getattr(self, attr, NOT_FOUND)

        return NOT_FOUND

    registerProvider = Delegate('__instance_offers__')

    def _config_maps(self):
        return [self.__class__.__class_offers__, self.__instance_offers__]













