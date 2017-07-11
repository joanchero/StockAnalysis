from interfaces import IActiveDescriptor
from protocols import adapt, advice
from types import ClassType
import dispatch,protocols

__all__ = [
    'activateClass','classAttr','Activator','declareAttribute','metadata',
    'declareClassMetadata', 'declareMetadata', 'initAttrs',
]


def metadata(*args, **kw):
    """Declare metadata for containing class and its attributes

    Usage::

        class Foo:
            binding.metadata(baz, a=b, x=y)

    is a shortcut for::

        class Foo:
            pass

        binding.declareMetadata(Foo, baz, a=b, x=y)

    See 'binding.declareMetadata()' for more details.
    """
    def callback(klass):
        declareMetadata(klass,*args,**kw)
        return klass

    advice.addClassAdvisor(callback)








try:
    sorted
except NameError:
    def sorted(seq):
        tmp = list(seq)
        tmp.sort()
        return tmp


def declareMetadata(classobj, *args, **kw):
    """Declare metadata for specified class and its attributes

    Usage::

        binding.declareAttributes(SomeClass,
            [AdministratorPermission],
            some_attr=[security.Anybody, options.Set('-v',value=True)],
            other_attr=syntax("foo|bar"),
                # etc...
        )

    The first argument is the class for which metadata is being declared.
    The second and subsequent positional arguments, if any are metadata for
    the class as a whole.  Keyword arguments are treated as attribute names,
    and their values are passed to 'binding.declareAttribute()' in order to
    declare the given metadata for the containing class.

    Please see individual frameworks' documentation for information about what
    metadata they need or provide, and what that metadata's semantics are.
    """
    declareClassMetadata(classobj, args)
    for k,v in sorted(kw.iteritems()):
        declareAttribute(classobj,k,v)








def initAttrs(ob, attrItems):
    """Initialize 'ob' using 'attrItems'

    'ob' can be any object with a '__class__' attribute.  'attrItems' must be
    an iterable of name/value pairs (such as a dictionary's 'items()' or
    'iteritems()').  For each name, if it is a valid attribute of the object's
    class, then the attribute will be set with  'setattr(ob,name,value)'.  If
    the name does not exist as an attribute of the object's class, a 'TypeError'
    will be raised, identifying the incorrect name/constructor keyword.
    """
    klass = ob.__class__
    for k,v in attrItems:
        if hasattr(klass,k):
            setattr(ob,k,v)
        else:
            raise TypeError(
                "%s constructor has no keyword argument %s" % (klass, k)
            )























[dispatch.on('metadata')]
def declareClassMetadata(classobj,metadata):
    """Declare 'metadata' about 'classobj'

    This generic function is used to dispatch metadata declarations.  You do
    not normally call it directly, unless implementing a metadata API or
    special class advisor.  Instead, you add methods to it, in order to support
    a new metadata type you've defined.

    Note that it's up to your methods to define the semantics, such as where
    the metadata will be stored.  The only predefined semantics are for
    metadata of 'None' (which is a no-op), and 'protocols.IBasicSequence' types
    (which recursively invokes 'declareClassMetadata()' on the sequence's
    contents).

    Also note that many metadata frameworks have a notion of context, such
    that different metadata might apply to the class in different contexts.
    If this is the case for your metadata type, the method you add to this
    function should set metadata for whatever your framework's "default
    context" is.
    """

[declareClassMetadata.when(type(None))]
def declareCM_None(classobj,attrname,metadata):
    """Declaring attribute metadata of 'None' is a no-op."""

[declareClassMetadata.when(protocols.IBasicSequence)]
def declareCM_Sequence(classobj,metadata):
    """Declaring attribute w/a sequence declares all contained items"""
    for item in metadata:
        declareClassMetadata(classobj,item)










[dispatch.on('metadata')]
def declareAttribute(classobj,attrname,metadata):
    """Declare 'metadata' about 'attrname' in 'classobj'

    This generic function is used to dispatch metadata declarations.  You do
    not normally call it directly, unless implementing a metadata API or
    attribute descriptor.  Instead, you add methods to it, in order to support
    a new metadata type you've defined.

    Note that it's up to your methods to define the semantics, such as where
    the metadata will be stored.  The only predefined semantics are for
    metadata of 'None' (which is a no-op), and 'protocols.IBasicSequence' types
    (which recursively invokes 'declareAttribute()' on the sequence's contents).

    Also note that many metadata frameworks have a notion of context, such
    that different metadata might apply to the class in different contexts.
    If this is the case for your metadata type, the method you add to this
    function should set metadata for whatever your framework's "default
    context" is.
    """

[declareAttribute.when(type(None))]
def declare_None(classobj,attrname,metadata):
    """Declaring attribute metadata of 'None' is a no-op."""

[declareAttribute.when(protocols.IBasicSequence)]
def declare_Sequence(classobj,attrname,metadata):
    """Declaring attribute w/a sequence declares all contained items"""
    for item in metadata:
        declareAttribute(classobj,attrname,item)











class classAttr(object):

    """Class attribute binding

    This wrapper lets you create bindings which apply to a class, rather than
    to its instances.  This can be useful for creating bindings in a base
    class that will summarize metadata about subclasses.  Usage example::

        class SomeClass(binding.Component):

            CLASS_NAME = binding.classAttr(
                binding.Make(
                    lambda self: self.__name__.upper()
                )
            )

        class aSubclass(SomeClass):
            pass

        assert SomeClass.CLASS_NAME == "SOMECLASS"
        assert aSubclass.CLASS_NAME == "ASUBCLASS"

    Class attributes will only work in subclasses of classes like
    'binding.Component', whose metaclass derives from 'binding.Activator'.

    Implementation note: class attributes actually cause a new metaclass to
    be created on-the-fly to contain them.  The generated metaclass is named
    for the class that contained the class attributes, and has the same
    '__module__' attribute value.  So continuing the above example::

        assert SomeClass.__class__.__name__ == 'SomeClassClass'
        assert aSubClass.__class__.__name__ == 'SomeClassClass'

    Notice that the generated metaclass is reused for subsequent
    subclasses, as long as they don't define any new class attributes."""

    __slots__ = 'binding'

    def __init__(self, binding): self.binding = binding


class Activator(type):

    """Descriptor metadata management"""

    __name__ = 'Activator'    # trick to make instances' __name__ writable


    def __new__(meta, name, bases, cdict):

        meta, stdAttrs = _boostedMeta(meta,name,cdict)

        if stdAttrs is not None:
            cdict = stdAttrs
            return meta(name,bases,cdict)

        klass = supertype(Activator,meta).__new__(meta, name, bases, cdict)
        klass.__name__ = name
        return activateClass(klass)



def supertype(supertype,subtype):

    """Workaround for 'super()' not handling metaclasses well

    Note that this will *skip* any classic classes in the MRO!
    """

    mro = iter(subtype.__mro__)

    for cls in mro:
        if cls is supertype:
            for cls in mro:
                if hasattr(cls,'__mro__'):
                    return cls
            break

    raise TypeError("Not sub/supertypes:", supertype, subtype)



def _boostedMeta(meta,name,cdict):

    classAttrs = dict([
        (k,v.binding) for (k, v) in cdict.items()
            if v is not None and adapt(v,classAttr,None) is v
    ])

    if not classAttrs:
        return meta,None

    stdAttrs = dict(cdict)
    map(stdAttrs.__delitem__, classAttrs)

    classAttrs['__module__'] = stdAttrs.get('__module__')

    if meta is ClassType:
        meta = type

    metameta = type(meta)
    if metameta is type:
        metameta = Activator    # Ensure that all subclasses are activated, too

    meta = metameta( name+'Class', (meta,), classAttrs )
    return meta, stdAttrs

















def activateClass(klass):
    """Activate any 'IActiveDescriptor' or 'classAttr' objects in 'klass'

    Any 'IActiveDescriptor' objects found in the class dictionary will have
    their 'activateInClass()' method called with the target class and attribute
    name.  The return value is then placed in a '__class_descriptors__' mapping
    that maps from attribute names to return values.

    If the class dictionary contains any 'binding.classAttr' instances, these
    are attached to a new metaclass for the class, and the class is rebuilt
    as an instance of the new metaclass.

    'activateClass()' does nothing if the class already possesses a
    '__class_descriptors__' mapping, so it is safe to call it more than once on
    the same class.
    """

    d = klass.__dict__
    if '__class_descriptors__' in d:
        return klass

    meta, stdAttrs = _boostedMeta(type(klass),klass.__name__,d)
    if meta is not type(klass):
        klass = meta(klass.__name__,klass.__bases__,stdAttrs)
        d = stdAttrs

    klass.__class_descriptors__ = cd = {}
    for k,v in sorted(d.items()):
        v = IActiveDescriptor(v,None)
        if v is not None:
            cd[k] = v.activateInClass(klass,k)
    return klass









