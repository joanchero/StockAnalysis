import protocols

__all__ = ['ISecurityContext']

class ISecurityContext(protocols.Interface):

    """Object controlling security checks"""

    def permissionFor(subject,name=None):
        """What permission is needed to access attrib 'name' of 'subject'?"""

    def hasPermission(user,perm,subject):
        """Does 'user' have permission 'perm' for 'subject'?"""


