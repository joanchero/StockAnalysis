"""Undo-history tests"""

from unittest import TestCase, makeSuite, TestSuite
from peak.storage.interfaces import *
from peak.storage.undo import AbstractDelta, History, UndoManager

class TestDelta(AbstractDelta):

    doneCount = 1
    finishCount = 0
    merges = ()
    
    def _undo(self):
        self.doneCount -= 1
        for item in self.merges:
            item.undo()

    def _redo(self):
        self.doneCount += 1
        for item in self.merges:
            item.redo()

    def _finish(self):
        self.finishCount += 1
        for item in self.merges:
            item.finish()

    def _merge(self,delta):
        if not isinstance(delta,TestDelta):
            raise TypeError("Incompatible delta")
        self.merges += (delta,)


def verify_deltas(case,deltas,**attrs):
    for k,v in attrs.items():
        for d in deltas:
            case.assertEqual(getattr(d,k),v)




class DeltaTests(TestCase):

    def testActive(self):
        d = TestDelta()
        self.failUnless(IDelta(d,None) is d)
        self.failUnless(d.active)
        self.assertEqual(d.doneCount, 1)
        self.assertEqual(d.finishCount, 0)
        d.finish()
        self.assertEqual(d.doneCount, 1)
        self.assertEqual(d.finishCount, 1)
        self.failIf(d.active)
        self.assertRaises(UndoError, d.finish)

    def testUndo(self):
        d = TestDelta()
        self.assertEqual(d.doneCount, 1)
        self.assertEqual(d.finishCount, 0)
        d.undo()
        self.assertEqual(d.doneCount, 0)
        self.assertEqual(d.finishCount, 1)
        self.assertRaises(UndoError, d.finish)
        self.assertRaises(UndoError, d.undo)

    def testRedo(self):
        d = TestDelta()
        self.assertRaises(UndoError, d.redo)
        self.assertEqual(d.doneCount, 1)
        d.undo()
        self.assertEqual(d.doneCount, 0)
        d.redo()
        self.assertEqual(d.doneCount, 1)

    def testUndoable(self):
        d = TestDelta()
        self.failUnless(d.undoable)
        d.undoable = False
        self.assertRaises(UndoError, d.undo)
        self.assertEqual(d.doneCount, 1)


    def testMerge(self):
        d1,d2 = TestDelta(), TestDelta()
        d1.merge(d2)
        d1.finish()
        self.assertRaises(UndoError, d1.merge, TestDelta())
        d1.undo()
        self.assertRaises(UndoError, d1.merge, TestDelta())
        d1.redo()
        self.assertRaises(UndoError, d1.merge, TestDelta())
        self.assertEqual(d1.merges, (d2,))































class HistoryTests(TestCase):

    verify_deltas = verify_deltas
    
    def testHistoryCollection(self):
        d1, d2, d3 = TestDelta(), TestDelta(), TestDelta()
        h = History()
        self.failUnless(IHistory(h,None) is h)
        map(h.merge, [d1,d2,d3])
        l = list(h)
        self.assertEqual(l, [d1,d2,d3])
        self.assertEqual(len(h),3)
        h.undo()
        self.verify_deltas(l,doneCount=0)

        h.redo()
        self.verify_deltas(l,doneCount=1)

    def testHistoryUndoable(self):
        h = History()
        self.failUnless(h.undoable)
        h.merge(TestDelta())
        self.failUnless(h.undoable)
        d = TestDelta()
        d.undoable = False
        h.merge(d)
        self.failIf(h.undoable)
        
    def testMergeByKey(self):
        d1, d2, d3 = TestDelta(), TestDelta(), TestDelta()
        d1.key = d3.key = 'a'; d2.key = 'b'
        h = History()
        map(h.merge, [d1,d2,d3])
        l = list(h)
        self.assertEqual(l, [d1,d2])
        self.assertEqual(len(h),2)
        self.assertEqual(d1.merges, (d3,))
        
        
        
        
    def testMergeHistory(self):

        all = d1,d2,d3,d4 = TestDelta(), TestDelta(), TestDelta(), TestDelta()
        d1.key = d3.key = 'a'; d2.key = 'b'

        h1 = History()
        h2 = History()

        h1.merge(d1); h1.merge(d2)
        h2.merge(d3); h2.merge(d4)
        h1.merge(h2)

        self.assertEqual(list(h1), [d1,d2,d4])
        self.assertEqual(d1.merges, (d3,))
        
        self.failUnless('a' in h1)
        self.failUnless('b' in h1)
        self.failIf('c' in h1)
        
        self.verify_deltas(all,finishCount=0,doneCount=1)

        h1.finish()
        self.verify_deltas(all,finishCount=1,doneCount=1)
        
        h1.undo()
        self.verify_deltas(all,doneCount=0)

        h1.redo()
        self.verify_deltas(all,doneCount=1)












class UndoTests(TestCase):
    
    verify_deltas = verify_deltas
    
    def testBasics(self):
        all = d1,d2,d3,d4 = TestDelta(), TestDelta(), TestDelta(), TestDelta()
        d1.key = d3.key = 'a'; d2.key = 'b'

        m = UndoManager()
        self.failUnless(IUndoManager(m,None) is m)
        map(m.record, all)
        
        self.failUnless(m.has_delta_for('a'))
        self.failUnless(m.has_delta_for('b'))
        self.failIf(m.has_delta_for('c'))

        self.verify_deltas(all,finishCount=0,doneCount=1)

        m.checkpoint()
        self.verify_deltas(all,finishCount=1,doneCount=1)
        
        m.checkpoint()
        m.undoLast()
        m.undoLast()

        self.verify_deltas(all,finishCount=1,doneCount=0)

        for i in 1,2,3:
            m.redoNext()
            self.verify_deltas(all,finishCount=1,doneCount=1)

            m.undoLast()
            self.verify_deltas(all,finishCount=1,doneCount=0)

        d5 = TestDelta()
        m.record(d5)
        self.assertRaises(UndoError,m.redoNext)
        m.revert()
        self.verify_deltas([d5],doneCount=0,finishCount=1)


    def testUndoRedo(self):
        m = UndoManager()
        all = d1,d2,d3,d4 = TestDelta(), TestDelta(), TestDelta(), TestDelta()
        
        m.record(d1)
        self.assertRaises(UndoError, m.undoLast)
        m.checkpoint()
        m.undoLast()    # redo stack is non-empty
        m.checkpoint()  # this should clear it
        self.assertRaises(UndoError, m.redoNext)
        
        d2.undoable = False
        m.record(d2)
        m.checkpoint()
        self.assertEqual(len(m.undos),0)    # XXX shouldn't check internals
        
    # XXX need hosed-ness test, for if an undo/redo fails
    # XXX also need API to reset a hosed undo manager
        

TestClasses = (
    DeltaTests, HistoryTests, UndoTests
)


def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])

































