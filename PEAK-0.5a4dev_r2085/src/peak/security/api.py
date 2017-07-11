from interfaces import *
from rules import *

def allow(basePerm=None, **nameToPerm):

    """DEPRECATED: Use 'binding.metadata()' to declare permissions instead"""

    import warnings
    warnings.warn(
        "'security.allow()' is deprecated; use 'binding.metadata()' instead",
        DeprecationWarning, stacklevel=2
    )

    def callback(klass):
        from peak.api import binding
        binding.declareMetadata(klass, basePerm, **nameToPerm)
        return klass

    from protocols.advice import addClassAdvisor
    addClassAdvisor(callback)

