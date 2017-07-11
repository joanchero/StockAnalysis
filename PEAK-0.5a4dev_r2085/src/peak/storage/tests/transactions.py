"""Transaction and Persistence tests"""

from unittest import TestCase, makeSuite, TestSuite
from peak.api import *
from peak.util.MiniTable import Table
from peak.persistence import Persistent
from peak.tests import testRoot

class TxnStateTest(TestCase):

    def setUp(self):
        self.ts = storage.TransactionService()
        self.p  = LogParticipant()
        self.log = self.p.log = []

    def checkOutside(self):

        ts = self.ts

        for op in ts.commit, ts.abort, ts.fail:
            self.assertRaises(exceptions.OutsideTransaction, op)

        self.assertRaises(exceptions.OutsideTransaction, ts.join, self.p)
        assert self.log == []


    def checkFail(self):

        ts = self.ts

        ts.begin()
        ts.fail()

        self.assertRaises(exceptions.BrokenTransaction, ts.join, self.p)
        self.assertRaises(exceptions.BrokenTransaction, ts.commit)

        ts.abort()
        assert self.log == []



    def checkStampAndActive(self):

        ts = self.ts

        assert not ts.isActive()
        assert ts.getTimestamp() is None

        for fini in ts.commit, ts.abort:

            ts.begin()
            assert ts.isActive()

            from time import time
            assert abs(time() - ts.getTimestamp()) < 5

            fini()

            assert not ts.isActive()
            assert ts.getTimestamp() is None

        assert self.log ==[]


    def checkSimpleUse(self):

        ts = self.ts
        ts.begin()
        ts.join(self.p)
        ts.commit()

        ts.begin()
        ts.join(self.p)
        ts.abort()

        assert self.log == [
            ('readyToVote',ts), ('voteForCommit',ts), ('commit',ts),
            ('finish',ts,True), ('abort',ts), ('finish',ts,False),
        ]



class LogParticipant(storage.AbstractParticipant):

    def readyToVote(self, txnService):
        self.log.append(("readyToVote", txnService))
        return True

    def voteForCommit(self, txnService):
        self.log.append(("voteForCommit", txnService))


    def commitTransaction(self, txnService):
        self.log.append(("commit", txnService))

    def abortTransaction(self, txnService):
        self.log.append(("abort", txnService))

    def finishTransaction(self, txnService, committed):
        self.log.append(("finish", txnService, committed))























class UnreadyParticipant(LogParticipant):

    def readyToVote(self, txnService):
        self.log.append(("readyToVote", txnService))
        return False

class ProcrastinatingParticipant(LogParticipant):

    status = 0

    def readyToVote(self, txnService):
        self.log.append(("readyToVote", txnService))
        old = self.status
        self.status += 1
        return old


class VotingTest(TestCase):

    def setUp(self):
        self.ts = storage.TransactionService()
        self.p_u  = UnreadyParticipant()
        self.p_p  = ProcrastinatingParticipant()
        self.p_n  = LogParticipant()
        self.log = self.p_u.log = self.p_p.log = self.p_n.log = []

    def checkUnready(self):

        ts = self.ts

        ts.begin()
        ts.join(self.p_u)
        ts.join(self.p_p)
        ts.join(self.p_n)

        self.assertRaises(exceptions.NotReadyError, ts.commit)

        # just a lot of ready-to-vote attempts
        assert self.log == [('readyToVote',ts)]*len(self.log)


    def checkMixed(self):

        ts = self.ts

        ts.begin()
        ts.join(self.p_p)
        ts.join(self.p_n)

        ts.commit()


        # 2 participants * 1 retry for first, rest are all * 2 participants

        assert self.log == \
            [('readyToVote',ts)]   * 4 + \
            [('voteForCommit',ts)] * 2 + \
            [('commit',ts)]        * 2 + \
            [('finish',ts,True)]   * 2


    def checkNormal(self):

        ts = self.ts

        ts.begin()
        ts.join(self.p_n)
        ts.commit()

        assert self.log == [
            ('readyToVote',ts),
            ('voteForCommit',ts),
            ('commit',ts),
            ('finish',ts,True),
        ]







class TxnTable(storage.TransactionComponent):

    stableState = ()
    colNames = ()

    table = binding.Make(lambda self: Table(self.colNames, self.stableState))

    def dump(self):
        colNames = self.colNames
        return [row.dump(colNames) for row in self.table]

    def commitTransaction(self, txnService):
        self.stableState = self.dump()

    def abortTransaction(self, txnService):
        self._delBinding('table')

    def DELETE(self, whereItems):
        self.joinedTxn
        self.table.DELETE(whereItems)

    def INSERT(self, items):
        self.joinedTxn
        self.table.INSERT(items)

    def INSERT_ROWS(self, rowList):
        self.joinedTxn
        self.table.INSERT_ROWS(self.colNames, rowList)

    def SELECT(self, whereItems=()):
        return self.table.SELECT(whereItems)

    def SET(self, whereItems, setItems):
        self.joinedTxn
        self.table.SET(whereItems, setItems)

    def __iter__(self):
        return iter(self.table)



class Harness(binding.Component):
    class sampleTable(TxnTable):
        colNames = 'a', 'b'

    sampleTable = binding.Make(sampleTable)

    class testDM(storage.EntityDM):
        table = binding.Obtain('sampleTable')
        class defaultClass(model.Element):
            class a(model.Attribute): pass
            class b(model.Attribute): pass

        def _load(self, oid, ob):
            rows = self.table.SELECT(Items(a=oid))
            if rows:
                return dict(rows[0].items())
            else:
                raise storage.InvalidKeyError, oid

        def _save(self, ob):
            self.table.SET(Items(a=ob._p_oid),Items(b=ob.b))

        def _new(self,ob):
            self.table.INSERT(Items(a=ob.a,b=ob.b))
            return ob.a

        def _delete_oids(self, oidList):
            for oid in oidList:
                self.table.DELETE(Items(a=oid))

        def _check(self,ob):
            assert isinstance(ob, self.defaultClass)

        def _defaultState(self,ob):
            return {}

        def __iter__(self):
            for row in self.table:
                yield self.preloadState(row['a'],row.items())
    testDM = binding.Make(testDM)

class TableTest(TestCase):

    def setUp(self):
        self.harness = Harness(testRoot())
        self.table = self.harness.sampleTable

    def tearDown(self):
        if storage.getTransaction(self.harness).isActive():
            storage.abort(self.harness)

    def checkNoChangeOutsideTxn(self):
        self.assertRaises(exceptions.OutsideTransaction,
            self.table.INSERT, Items(a=1,b=2)
        )

    def checkRollback(self):
        assert self.table.dump()==[]

        storage.begin(self.harness)
        self.table.INSERT(Items(a=1,b=2))
        assert self.table.dump()==[(1,2)]
        storage.abort(self.harness)

        assert self.table.dump()==[]

    def checkCommit(self):
        assert self.table.dump()==[]

        storage.begin(self.harness)
        self.table.INSERT(Items(a=1,b=2))
        assert self.table.dump()==[(1,2)]
        storage.commit(self.harness)

        assert self.table.dump()==[(1,2)]

        storage.begin(self.harness)
        self.table.INSERT(Items(a=3,b=4))
        assert self.table.dump()==[(1,2),(3,4)]
        storage.abort(self.harness)
        assert self.table.dump()==[(1,2)]

class DMTest(TestCase):

    def setUp(self):
        self.harness = Harness(testRoot())
        self.table = self.harness.sampleTable
        self.dm  = self.harness.testDM

    def tearDown(self):
        if storage.getTransaction(self.harness).isActive():
            storage.abort(self.harness)

    def _addData(self):
        storage.begin(self.harness)
        self.table.INSERT(Items(a=1,b=2))

    def checkExistence(self):

        self._addData()

        ob = self.dm[1]
        assert ob.b==2
        storage.abort(self.harness)

        storage.begin(self.harness)
        self.assertRaises(storage.InvalidKeyError, lambda: ob.b)

    def checkFlush(self):

        self._addData()
        assert self.table.dump()==[(1,2)]
        storage.commit(self.harness)

        storage.begin(self.harness)
        ob = self.dm[1]
        ob.b = 4
        self.dm.flush()
        assert self.table.dump()==[(1,4)]

        storage.abort(self.harness)
        assert self.table.dump()==[(1,2)]

    def checkModify(self):
        self._addData()
        ob = self.dm[1]
        ob.b = 4
        assert self.table.dump()==[(1,2)]
        storage.commit(self.harness)
        assert self.table.dump()==[(1,4)]


    def checkNew(self):
        storage.begin(self.harness)
        ob = self.dm.newItem()
        ob.a = 1
        ob.b = 2
        assert self.table.dump()==[]
        storage.commit(self.harness)
        assert self.table.dump()==[(1,2)]

    def checkAddRemoveGet(self):
        storage.begin(self.harness)
        ob = self.dm.defaultClass(a=1,b=2)
        self.dm.add(ob)
        assert self.table.dump()==[]
        assert ob in self.dm
        assert 1 not in self.dm
        assert self.dm.get(1) is None
        self.dm.flush()
        assert 1 in self.dm
        assert self.dm.get(1) is ob
        assert self.table.dump()==[(1,2)]
        assert list(self.dm)==[ob]
        self.dm.remove(ob)
        assert 1 not in self.dm
        assert ob not in self.dm
        self.dm.flush()
        assert self.table.dump()==[]
        storage.abort(self.harness)




    def checkKeyDupe(self):
        storage.begin(self.harness)
        ob1 = self.dm.defaultClass(a=1,b=2)
        ob1._p_oid = 1
        ob2 = self.dm.defaultClass(a=1,b=2)
        ob2._p_oid = 1
        self.dm.add(ob1)
        self.assertRaises(storage.InvalidKeyError, self.dm.add, ob2)
        storage.abort(self.harness)


















TestClasses = (
    TxnStateTest, VotingTest, TableTest, DMTest
)


def test_suite():
    return TestSuite([makeSuite(t,'check') for t in TestClasses])


































