##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Provide access to Persistent C extension types."""

# All below is modified/added for PEAK

__all__ = ['Persistent', 'PersistentMetaClass', 'isGhost']


from _persistence import Persistent, PersistentMetaClass, simple_new, GHOST

import copy_reg
copy_reg.constructor(simple_new)


import protocols, interfaces
protocols.declareImplementation(
    Persistent, instancesProvide=[interfaces.IPersistent]
)

def isGhost(obj):
    return obj._p_state == GHOST

