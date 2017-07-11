from unittest import TestCase, makeSuite, TestSuite
from peak.util.ConflictManager import ConflictManager

class ConflictResolutionTests(TestCase):

    def testCMLast(self):
        cm = ConflictManager()
        cm[123] = (1,), "xyz"
        cm[123] = (), "abc"       
        self.assertEqual(cm[123],"abc")
        self.assertEqual(cm.values(),["abc"])

    def testCMFirst(self):
        cm = ConflictManager()
        cm[123] = (), "xyz"
        cm[123] = (1,), "abc"       
        self.assertEqual(cm[123],"xyz")
        self.assertEqual(cm.values(),["xyz"])

    def testCMConflicts(self):
        cm = ConflictManager()
        cm['abc'] = (1,), "xyz"        
        self.assertRaises(KeyError, cm.__setitem__, 'abc', ((2,), "def"))

TestClasses = (ConflictResolutionTests,)

def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])

