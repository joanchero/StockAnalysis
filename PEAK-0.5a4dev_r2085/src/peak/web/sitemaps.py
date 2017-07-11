from peak.api import *
from interfaces import *
from places import Location
from peak.util.imports import lazyModule
from peak.util import SOX
from peak.util.ConflictManager import ConflictManager


def isRoot(data):
    return 'previous' not in data

def acquire(data,key,default=None):
    """Find 'key' in 'data' or its predecessors"""
    while data is not None:
        if key in data:
            return data[key]
        data = data.get('previous')
    else:
        return default

def finishComponent(parser,data):
    if 'sm.component' in data:
        stack = data['sm_container_stack']
        while stack:
            stack.pop()()
        if not isRoot(data) and 'no_resolve' not in data:
            cm = data['sm_conflict_manager']
            for setting in cm.values(): setting()
        return data['sm.component']

def getGlobals(data):
    return data.setdefault('sm_globals',acquire(data,'sm_globals').copy())

def findComponentData(data):
    prev = data['previous']
    while 'sm.component' not in prev:
        prev = prev.get('previous')
    return prev



def assertNotTop(parser,data):
    if isRoot(data['previous']):
        parser.err(
            "%(name)r element cannot be top-level in the document" % data
        )

def acquirePermission(data,attrs):
    if 'permission' in attrs:
        perm = data['sm.permission'] = evalObject(data,attrs['permission'])
        return perm
    return acquire(data,'sm.permission',security.Anybody)

def acquireHelper(data,attrs):
    if 'helper' in attrs:
        helper = data['sm.helper'] = evalObject(data,attrs['helper'])
        return helper
    return acquire(data,'sm.helper')

def assertOutsideContent(parser,data):
    content = acquire(data,'sm.content_type',NOT_GIVEN)
    if content is not NOT_GIVEN:
        parser.err(
            "%(name)r element cannot be nested inside 'content' block" % data
        )

def choose(parser, names, attrs):
    found = False
    for name in names:
        if name in attrs:
            if found:
                break
            found = True
            result = name,attrs[name]
    else:
        if found:
            return result
    parser.err(
        "Element must include *exactly* one of these attributes: "
        + ', '.join(names)
    )

def addPermission(handler,permission):
    def guarded_handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        ctx.requireAccess(qname,ob,permissionNeeded=permission)
        return handler(ctx, ob, namespace, name, qname, default)
    return guarded_handler

def addHelper(handler,helper):
    def helped_handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        ob = helper(ob)
        return handler(ctx.clone(current=ob),ob,namespace,name,qname,default)
    return helped_handler

def attributeView(attr):
    from environ import traverseAttr
    def handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        loc = getattr(ob, attr, NOT_FOUND)
        if loc is not NOT_FOUND:
            return ctx.childContext(qname,loc)
        if default is NOT_GIVEN:
            raise web.NotFound(ctx,qname,ob)
        return default
    return handler

def objectView(target):
    def handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        return ctx.childContext(qname,target)
    return handler

def resourceView(path):
    def handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        return ctx.childContext(qname,ctx.getResource(path))
    return handler









def locationView(spec):
    keyPath,locId = str(spec).split('@',1)
    locId = '++id++'+locId
    def handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
        path = str(ctx.clone(current=ob).traverseName(keyPath).current)
        base = ctx.traverseName(locId).absoluteURL
        return ctx.childContext(qname,base+'/'[:not base.endswith('/')]+path)
    return handler

def registerView(parser,data,attrs,name,handler):

    perm = acquirePermission(data,attrs)
    helper = acquireHelper(data,attrs)
    loc = acquire(data,'sm.component')
    typ = acquire(data,'sm.content_type')

    if helper is not None:
        handler = addHelper(handler,helper)

    if perm is not security.Anybody:
        handler = addPermission(handler,perm)

    addSetting(parser, data, (typ,name),
        lambda: loc.registerView(typ,str(name),handler))


def addSetting(parser,data,key,setting):
    cm = acquire(data,'sm_conflict_manager')
    try:
        cm[key] = acquire(data,'sm_include_path',()), setting
    except KeyError:
        parser.err("Conflicting settings for %r" % (key,))


def evalObject(data,expr):
    g = getGlobals(data['previous'])
    return eval(expr,g,g)




def doAllow(parser,data):
    attrs = SOX.validatedAttributes(
        parser,data,('attributes',),('permission','helper')
    )
    for attr in attrs['attributes'].split(','):
        registerView(parser,data,attrs,attr,attributeView(attr.strip()))


def defineAllow(parser,data):
    assertNotTop(parser,data)    #assertInsideContent(parser,data)?
    data['start'] = doAllow
    data['empty'] = True





























locRequired = ()
locOptional = 'name','class','id','permission', 'extends', 'config'

def makeLocation(parser,data,attrs,parent,name):
    if 'extends' in attrs:
        factory = naming.lookup(parent,
            naming.parseURL(parent, attrs['extends'], parser._url)
        )
        loc = config.processXML(
            web.SITEMAP_SCHEMA(parent),
            relativeResource(parser,attrs['extends'],parent),
            parent=parent, sm_included_from=attrs, sm_globals=globals(), #XXX
            sm_include_path=acquire(data,'sm_include_path',())+(parser._url,),
            sm_conflict_manager=data['sm_conflict_manager'],
        )
    elif 'class' in attrs:
        loc = evalObject(data,attrs['class'])(parent,name)
    else:
        loc = Location(parent,name)

    if 'id' in attrs:
        registry = IConfigurableLocation(parent,None)
        if registry is not None:
            registry.registerLocation(str(attrs['id']),name)
        else:
            loc.registerLocation(str(attrs['id']),'.')

    if 'config' in attrs:
        config.loadConfigFile(
            loc,relativeResource(parser,attrs['config'],parent)
        )
    if name:
        registerView(parser,data,attrs,name,objectView(loc))
    return loc

def relativeResource(parser, attr, parent):
    return naming.lookup(parent,
        # Might be a relative URL, so parse w/parser URL as base
        naming.parseURL(parent, attr, parser._url)
    )

def startLocation(parser,data):
    attrs = SOX.validatedAttributes(parser,data,locRequired,locOptional)
    acquirePermission(data,attrs)
    prev = findComponentData(data)
    parent = prev['sm.component']
    name = attrs.get('name')

    if data['previous'] is not prev:
        parser.err("Locations must be directly inside other locations")

    if isRoot(prev):
        if name is not None:
            parser.err("Root location cannot have a 'name'")

        if 'sm_included_from' in prev:
            inclattrs = prev['sm_included_from']
            name = inclattrs.get('name')
            if 'class' in inclattrs:
                attrs['class'] = inclattrs['class']
            if 'sm_conflict_manager' in prev:
                data['sm_conflict_manager'] = prev['sm_conflict_manager']
                data['no_resolve'] = True   # let the including file do it

    elif not name:
        parser.err("Non-root locations must have a 'name'")

    data.setdefault('sm_conflict_manager',ConflictManager())
    loc = makeLocation(parser,data,attrs,parent,name)
    data['sm.component'] = loc
    data['sm_container_stack'] = []

def defineLocation(parser,data):
    data['finish'] = finishComponent
    data['start'] = startLocation
    prev = findComponentData(data)






content_req = ('type',)
content_opt = ('permission','helper','location')

def doContent(parser,data):
    attrs = SOX.validatedAttributes(parser,data,content_req,content_opt)
    acquirePermission(data,attrs)
    acquireHelper(data,attrs)
    data['sm.content_type'] = evalObject(data,attrs['type'])
    if 'location' in attrs:
        registerView(
            parser,data,attrs,'peak.web.url',locationView(attrs['location'])
        )

def defineContent(parser,data):
    assertNotTop(parser,data)
    assertOutsideContent(parser,data)
    data['start'] = doContent


def doImport(parser,data):
    attrs = SOX.validatedAttributes(parser,data,('module',),('as',))
    module = str(attrs['module'])
    as_ = attrs.get('as', module.split('.')[-1])
    getGlobals(data['previous'])[as_] = lazyModule(module)

def defineImport(parser,data):
    assertNotTop(parser,data)
    data['start'] = doImport
    data['empty'] = True












def doContainer(parser,data):
    attrs = SOX.validatedAttributes(
        parser, data, (), ('lookup','object','permission',)
    )
    prev = findComponentData(data)
    perm = acquirePermission(data,attrs)
    loc = prev['sm.component']

    if ('object' in attrs)==('lookup' in attrs):
        parser.err("container must have a 'lookup' or 'object'")
    elif 'object' in attrs:
        container = evalObject(data,attrs['object'])
    else:
        container = binding.lookupComponent(
            loc,evalObject(data,attrs['lookup'])
        )

    prev['sm_container_stack'].append(lambda: loc.addContainer(container,perm))
    data['container'] = container

def finishContainer(parser,data):
    return data['container']
   
def defineContainer(parser,data):
    assertNotTop(parser,data)
    assertOutsideContent(parser,data)
    data['start'] = doContainer
    data['finish'] = finishContainer
    data['empty'] = True












view_required = 'name',
view_one_of   = 'resource','attribute','object', 'function', 'expr'
view_optional = view_one_of + ('permission','helper')

def doView(parser,data):
    attrs = SOX.validatedAttributes(parser,data,view_required,view_optional)

    mode,expr = choose(parser,view_one_of,attrs)
    if mode=='object':
        handler = objectView(evalObject(data,expr))
    elif mode=='function':
        handler = evalObject(data,expr)
    elif mode=='expr':
        g = getGlobals(data['previous'])
        def handler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
            return ctx.childContext(qname, eval(expr,locals(),g))
    elif mode=='attribute':
        handler = attributeView(expr)
    elif mode=='resource':
        handler = resourceView(expr)

    registerView(parser,data,attrs,attrs['name'],handler)

def defineView(parser,data):
    assertNotTop(parser,data)
    data['start'] = doView
    data['empty'] = True


def doOffer(parser,data):
    attrs = SOX.validatedAttributes(parser,data,('path','as',))
    prev = findComponentData(data)
    prev['sm.component'].registerLocation(attrs['as'],attrs['path'])

def defineOffer(parser,data):
    assertNotTop(parser,data)
    assertOutsideContent(parser,data)
    data['start'] = doOffer
    data['empty'] = True


def doRequire(parser,data):
    attrs = SOX.validatedAttributes(parser,data,('permission',),('helper',))
    acquirePermission(data,attrs)
    acquireHelper(data,attrs)

def defineRequire(parser,data):
    assertNotTop(parser,data)
    data['start'] = doRequire


def setupDocument(parser,data):
    def setRoot(ob):
        data['sm.component'] = ob

    data['child'] = setRoot
    data['finish'] = finishComponent
    data['sm.component'] = data['parent']
    data['sm_container_stack'] = []

class SiteMap(binding.Singleton):
    protocols.advise(classProvides=[naming.IObjectFactory])
    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        url, = refInfo.addresses
        return config.processXML(
            web.SITEMAP_SCHEMA(context), str(url),
            parent=context, sm_globals=globals(), #XXX
        )














