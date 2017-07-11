from peak.api import *
from model import *
from peak.running.commands import AbstractCommand, Bootstrap, InvocationError


class BulletinsApp(binding.Component):

    dbURL = binding.Obtain("./db/address")
    dbDDL = binding.Obtain(PropertyName('bulletins.databaseDDL'))

    db = binding.Obtain(PropertyName('bulletins.db'))
    log = binding.Obtain('logger:bulletins.app')

    Bulletins = binding.Obtain(storage.DMFor(Bulletin))
    Categories = binding.Obtain(storage.DMFor(Category))
    Users = binding.Obtain(storage.DMFor(User))

























class BulletinsCmd(BulletinsApp, Bootstrap):

    usage = """
Usage: bulletins command arguments...


Available commands:

  createdb  -- create an empty bulletins database
  purge     -- purge expired bulletins
  showusers -- list current users
  adduser   -- add a user to the database
"""
    acceptURLs = False


class CreateDB(BulletinsApp, AbstractCommand):

    def _run(self):
        self.log.info("Creating %s using DDL from %s",
            self.dbURL, self.dbDDL
        )
        storage.beginTransaction(self)
        dbDDL = config.getStreamFactory(self,self.dbDDL)
        for ddl in dbDDL.open('t').read().split('\n;\n'):
            if not ddl.strip(): continue
            self.db(ddl)
        storage.commitTransaction(self)













class ShowUsers(BulletinsApp, AbstractCommand):

    def run(self):
        print "User          Name"
        print "------------  -----------------------------------"
        storage.beginTransaction(self)
        for user in self.Users:
            print "%-12s  %s" % (user.loginId, user.fullName)
        storage.commitTransaction(self)


class AddUser(BulletinsApp, AbstractCommand):

    usage = """Usage: bulletins adduser login password [full name]"""

    def _run(self):
        if len(self.argv)<3:
            raise InvocationError("missing argument(s)")

        storage.beginTransaction(self)
        user = self.Users.newItem()
        user.loginId, user.password = self.argv[1:3]
        user.fullName = ' '.join(self.argv[3:]) or user.loginId
        storage.commitTransaction(self)

















class AddCategory(BulletinsApp, AbstractCommand):

    usage = """Usage: bulletins addcat category [title]"""

    def _run(self):
        if len(self.argv)<2:
            raise InvocationError("missing argument(s)")

        storage.beginTransaction(self)

        cat = self.Categories.newItem()
        cat.pathName = self.argv[1]
        cat.title = ' '.join(self.argv[2:]) or cat.pathName

        storage.commitTransaction(self)


























class Post(BulletinsApp, AbstractCommand):

    usage = """Usage: bulletins post userid category <posting.txt"""

    def _run(self):

        if len(self.argv)<>3:
            raise InvocationError("missing or extra argument(s)")

        userId, categoryId = self.argv[1:]
        text = self.stdin.read()

        storage.beginTransaction(self)

        user = self.Users[userId]
        category = self.Categories[categoryId]
        category.post(user, text)

        storage.commitTransaction(self)



class PurgeDB(BulletinsApp, AbstractCommand):

    def run(self):
        print "This would've purged the DB"















