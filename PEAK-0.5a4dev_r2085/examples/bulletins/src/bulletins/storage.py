from peak.api import *
from bulletins.model import *

__all__ = [
    'BulletinsForCategoryDM', 'CategoryDM', 'UserDM', 'BulletinDM',
]

DATABASE = PropertyName('bulletins.db')

class BulletinsForCategoryDM(storage.QueryDM):

    db         = binding.Obtain(DATABASE)
    BulletinDM = binding.Obtain(storage.DMFor(Bulletin))

    def _load(self, oid, ob):

        data = []
        preload = self.BulletinDM.preloadState
        stateFor = self.BulletinDM.stateFromRow

        for row in self.db(
            "select * from bulletins where category = %s", (oid,)
        ):
            data.append(
                preload(row.id, stateFor(row))
            )

        return data













class TrivialSQL_DM(storage.EntityDM):
    """Common behaviors for our entity DM's"""

    db = binding.Obtain(DATABASE)

    pk_format = "%r"

    _selectOne = binding.Make(
        lambda self: (
            "select * from %s where %s = %s"
            % (self.table, self.pk_field, self.pk_format)
        )
    )

    _selectAll = binding.Make(lambda self: "select * from %s" % (self.table,))

    def _load(self, oid, ob):
        try:
            row = ~self.db(self._selectOne, (oid,))
        except exceptions.TooFewResults:
            raise InvalidKeyError(oid)
        else:
            return self.stateFromRow(row)

    def __iter__(self):
        self.flush()
        for row in self.db(self._selectAll):
            yield self.preloadState(
                getattr(row,self.pk_field), self.stateFromRow(row)
            )

    def _check(self,ob):
        if not isinstance(ob,self.defaultClass):
            raise TypeError("Must be a "+self.defaultClass.__name__, ob)

    def _new(self, ob):
        oid = ob._p_oid = getattr(ob,self.pk_field)
        self._save(ob)
        return oid


    def _write(self, **data):
        data = data.items()
        self.db(
            "INSERT OR REPLACE INTO %s (%s) VALUES (%s)"
            % (self.table,
                ','.join([k for k,v in data]),
                ','.join(['%s']*len(data))
            ),
            tuple([v for k,v in data])
        )


class UserDM(TrivialSQL_DM):

    defaultClass = User

    table = "users"
    pk_field = "loginId"

    def stateFromRow(self,row):
        return dict(
            loginId = row.loginId,
            fullName = row.fullName,
            password = row.password,
        )

    def _save(self, ob):
        self._write(
            loginId=ob.loginId, fullName=ob.fullName, password=ob.password
        )











class BulletinDM(TrivialSQL_DM):

    table = "bulletins"
    pk_field = "id"

    CategoryDM   = binding.Obtain(storage.DMFor(Category))
    UserDM       = binding.Obtain(storage.DMFor(User))
    forCategory  = binding.Make(BulletinsForCategoryDM)
    defaultClass = Bulletin

    def stateFromRow(self,row):
        return dict(
            id = row.id,
            category = self.CategoryDM[row.category],
            fullText = row.fullText,
            postedBy = self.UserDM[row.postedBy],
            postedOn = row.postedOn,
            editedBy = self.UserDM[row.editedBy],
            editedOn = row.editedOn,
            hidden = row.hidden <> 0,
        )

    def _save(self, ob):
        self._write(
            id=ob._p_oid, category=self.CategoryDM.oidFor(ob.category),
            fullText=ob.fullText, postedBy=ob.postedBy.loginId,
            postedOn=str(ob.postedOn), editedBy=ob.editedBy.loginId,
            editedOn=str(ob.editedOn), hidden=int(ob.hidden)
        )

    def _new(self,ob):
        # Note: this trick only works w/SQLite *exclusive* transactions
        ct, = ~self.db('SELECT MAX(id) FROM bulletins')
        ct = int(ct or 0) + 1
        ob._p_oid = ob.id = ct
        self._save(ob)
        return ct




class CategoryDM(TrivialSQL_DM):

    table = "categories"
    pk_field = "pathName"

    BulletinDM = binding.Obtain(storage.DMFor(Bulletin))
    bulletinsForCategory = binding.Obtain('BulletinDM/forCategory')
    defaultClass = Category

    def stateFromRow(self,row):
        return dict(
            pathName = row.pathName,
            title = row.title,
            sortPosn = row.sortPosn,
            bulletins = storage.QueryLink(
                self.bulletinsForCategory[row.pathName]
            ),
            sortBulletinsBy = SortBy[row.sortBulletinsBy],
            postingTemplate = row.postingTemplate,
            editingTemplate = row.editingTemplate,
        )

    def _save(self, ob):
        self._write(
            pathName=ob.pathName, title=ob.title, sortPosn=ob.sortPosn,
            sortBulletinsBy=ob.sortBulletinsBy._hashAndCompare,
            postingTemplate=ob.postingTemplate,
            editingTemplate=ob.editingTemplate
        )












