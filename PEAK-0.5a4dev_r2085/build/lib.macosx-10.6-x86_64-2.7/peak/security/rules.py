from peak.api import *
from interfaces import *
from dispatch import strategy

__all__ = [
    'PermissionType', 'Permission', 'Anybody', 'Nobody',
    'Context', 'hasPermission', 'permissionFor', 'Denial',
]


class PermissionType(type):
    """Metaclass for permissions

    This metaclass is only needed so that we can register metadata hooks in the
    binding system that will record permissions declared via the binding
    metadata API.
    """

class Permission:
    """Abstract base for permission classes"""
    __metaclass__ = PermissionType


class Anybody(Permission):
    """Allow anybody access"""


class Nobody(Permission):
    """Deny everyone access"""












class Context:
    """Context in which security rules apply"""

    protocols.advise(instancesProvide = [ISecurityContext])

    [dispatch.generic()]
    def permissionFor(self,subject,name=None):
        """What permission is needed to access attrib 'name' of 'subject'?"""

    [permissionFor.when("name is None")]
    def __nonAttributeAllowsAnybody(self,subject,name):
        return Anybody

    [permissionFor.when(strategy.default)]
    def __undefinedPermission(self,subject,name):
        return None


    [dispatch.generic()]
    def hasPermission(self,user,perm,subject):
        """Does 'user' have permission 'perm' for 'subject'?"""

    [hasPermission.when(strategy.default)]
    def __denyByDefault(self,user,perm,subject):
        return security.Denial("Access denied.")

    [hasPermission.when("perm==Nobody")]
    def __nobodyGetsNobody(self,user,perm,subject):
        return security.Denial("Access forbidden")

    [hasPermission.when("perm==Anybody")]
    def __anybodyGetsAnybody(self,user,perm,subject):
        return True


hasPermission = Context.hasPermission.im_func
permissionFor = Context.permissionFor.im_func




class Denial(object):

    """Object representing denial of access"""

    __slots__ = 'message'

    def __init__(self,message):
        self.message = message

    def __nonzero__(self):
        # A denial is always a false condition
        return False

    __len__ = __nonzero__

    def __str__(self):
        return str(self.message)

    def __unicode__(self):
        return unicode(self.message)

    def __repr__(self):
        return 'security.Denial(%r)' % self.message


















[binding.declareClassMetadata.when(PermissionType)]
def _declare_existence_permission(classobj,metadata):
    [Context.permissionFor.when(
        "self in Context and subject in classobj and name is None"
    )]
    def declared_existence_permission(self,subject,name):
        return metadata


[binding.declareAttribute.when(PermissionType)]
def _declare_permission(classobj,attrname,metadata):
    [Context.permissionFor.when(
        "self in Context and subject in classobj and name==attrname"
    )]
    def declared_permission(self,subject,name):
        return metadata

























