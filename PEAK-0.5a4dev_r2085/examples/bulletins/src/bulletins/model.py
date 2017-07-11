"""Bulletin board example: domain model"""

from peak.api import *
from datetime import datetime, timedelta


__all__ = ['User', 'Bulletin', 'Category', 'DateTime', 'SortBy', ]


class DateTime(model.Immutable):

    """PEAK wrapper for Python datetime type"""

    def mdl_normalize(klass, value):
        if hasattr(value,'ticks'):
            # Convert mxDateTime to Python datetime
            value = datetime.fromtimestamp(value.ticks())
        return value    # XXX should convert from mxDateTime/datetime etc.

    def mdl_fromString(klass, value):
        return value    # XXX should parse from string

    def mdl_toString(klass, value):
        return str(value)    # XXX should format value as string


class SortBy(model.Enumeration):
    MOST_RECENTLY_POSTED = model.enum()
    MOST_RECENTLY_EDITED = model.enum()
    ALPHABETICAL         = model.enum()


class PathPart(model.String):
    pass # XXX validate that string has no spaces, or slashes, and is short


class Interval(model.Integer):
    pass    # XXX needs to be date/time interval type



class User(model.Element):

    class loginId(model.Attribute):
        referencedType = model.String

    class fullName(model.Attribute):
        referencedType = model.String

    # XXX need password, and authenticate() method
































class Bulletin(model.Element):

    class id(model.Attribute):
        referencedType = model.Integer

    class category(model.Attribute):
        referencedType = 'Category'
        referencedEnd = 'bulletins'

    class fullText(model.Attribute):
        referencedType = model.String

    class postedBy(model.Attribute):
        referencedType = User

    class postedOn(model.Attribute):
        referencedType = DateTime

    class editedBy(model.Attribute):
        referencedType = User

    class editedOn(model.Attribute):
        referencedType = DateTime

    class hidden(model.Attribute):
        referencedType = model.Boolean
        defaultValue   = False

    # Methods/attrs needed: asHTML(), sortValue(sortType), title, teaser...
    # change(user, text, [date]) ...











class Category(model.Element):

    class pathName(model.Attribute):
        referencedType = PathPart

    class title(model.Attribute):
        referencedType = model.String

    class sortPosn(model.Attribute):
        referencedType = model.Integer
        defaultValue = 0

    class bulletins(model.Collection):
        referencedType = Bulletin
        referencedEnd = 'category'

    class sortBulletinsBy(model.Attribute):
        referencedType = SortBy
        defaultValue   = SortBy.MOST_RECENTLY_EDITED

    class postingTemplate(model.Attribute):
        referencedType = model.String
        defaultValue = ''

    class editingTemplate(model.Attribute):
        referencedType = model.String
        defaultValue = ''

    def post(self, user, text, timestamp=None):

        if timestamp is None:
            timestamp = datetime.now()

        bulletin = config.lookup(self,storage.DMFor(Bulletin)).newItem()
        bulletin.postedBy = bulletin.editedBy = user
        bulletin.postedOn = bulletin.editedOn = timestamp
        bulletin.category = self
        bulletin.fullText = text

        return bulletin


UserDM = storage.DMFor(User)
BulletinDM = storage.DMFor(Bulletin)
CategoryDM = storage.DMFor(Category)


























