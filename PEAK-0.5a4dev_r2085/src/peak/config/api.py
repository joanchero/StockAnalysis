"""Configuration API"""

from interfaces import *
from peak.exceptions import SpecificationError, ModuleInheritanceWarning
from config_components import *
from ini_files import *
from api_impl import *
from registries import *


for item in 'setupObject', 'declareModule':
    exec """def %(item)s(*args,**kw):
    \"""See peak.config.modules.%(item)s\"""
    global %(item)s
    from peak.config.modules import %(item)s
    return %(item)s(*args,**kw)
""" % locals()
    

def setupModule():
    """See peak.config.modules.setupModule()"""
    global setupModule
    from peak.config.modules import setupModule
    return setupModule(2)

def patchModule(moduleName):
    """See peak.config.modules.patchModule()"""
    global patchModule
    from peak.config.modules import patchModule
    return patchModule(moduleName,2)



