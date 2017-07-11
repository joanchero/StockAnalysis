"""Configuration Management API"""

from config_components import ConfigurationRoot, Value, lookup
from peak.util.EigenData import AlreadyRead
from interfaces import *
from peak.api import *

__all__ = [
    'makeRoot', 'registeredProtocol'
]


def makeRoot(**options):

    """Create a configuration root, suitable for use as a parent component

    This creates and returns a new 'IConfigurationRoot' with its default
    configuration loading from 'peak.ini'.  The returned root component
    will "know" it is a root, so any components that use it as a parent
    will get their 'uponAssembly()' events invoked immediately.

    Normally, this function is called without any parameters, but it will
    also accept keyword arguments that it will pass along when it calls the
    'peak.config.config_components.ConfigurationRoot' constructor.

    Currently, the only acceptable keyword argument is 'iniFiles', which must
    be a sequence of filename strings or '(moduleName,fileName)' tuples.

    The default value of 'iniFiles' is '[("peak","peak.ini")]', which loads
    useful system defaults from 'peak.ini' in the 'peak' package directory.
    Files are loaded in the order specified, with later files overriding
    earlier ones, unless the setting to be overridden has already been used
    (in which case an 'AlreadyRead' error occurs)."""

    return ConfigurationRoot(None, **options)






def registeredProtocol(ob, configKey, baseProtocol=None):

    """Obtain a local protocol object suitable for registering local adapters

    Usage::

        # Register a local adapter from type 'xyz' to the 'foo.bar' named
        # protocol:
        localProto = config.registeredProtocol(ctx,'foo.bar')
        protocols.declareAdapter(someFunc, [localProto], forTypes=[xyz])

        # ...later, obtain a localized adaptation in 'someContext'
        adapt(someObject, config.lookup(ctx,'foo.bar'))

    This function is used to define named and/or contextual protocols,
    which provide functionality similar to Zope 3's named adapters and
    local adapters.  If no local protocol has been created under the specified
    'configKey' for 'ob', this function creates a 'protocols.Variation' of
    the protocol found under 'configKey' in any of the parent components of
    'ob'.  If no parent has a protocol registered under 'configKey', the
    supplied 'baseProtocol' is used as the base for the 'Variation'.  (If
    'None', a new 'protocols.Protocol' is registered instead of a 'Variation'.)

    You only need to use 'registeredProtocol()' when declaring adapters, not
    when looking them up.  Use 'config.lookup()' with the same arguments
    instead, since 'config.lookup()' doesn't attempt to register new protocols,
    and will thus be faster.

    Note that you cannot register a local protocol for a given 'configKey'
    once it has been looked up on 'ob'.  Doing so will result in an
    'AlreadyRead' error.  Also note that this function doesn't check that
    a value already registered for 'configKey' is actually a protocol; if
    there is some other value already registered, it will be returned as long
    as it is not the same value found for 'configKey' on the parent component
    of 'ob' (i.e., so long as it is "local" to 'ob'.)
    """





    key = IConfigKey(configKey)
    parent = binding.getParentComponent(ob)

    if parent is not None:
        oldProtocol = lookup(parent, key, baseProtocol)
    else:
        oldProtocol = baseProtocol

    if oldProtocol is None:
        newProtocol = protocols.Protocol()
    else:
        newProtocol = protocols.Variation(oldProtocol)

    try:
        IConfigurable(ob).registerProvider(key, Value(newProtocol))
    except AlreadyRead:
        pass

    newProtocol = lookup(ob,key,baseProtocol)

    if newProtocol is oldProtocol:
        raise AlreadyRead("Too late to register protocol", configKey, ob)

    return newProtocol

















