from unittest import TestCase, makeSuite, TestSuite
from peak.util.expr import *

class ProxyTests(TestCase):

    proxy = proxyType(lambda *args: args)

    def testProxyUnProxy(self):
        for ob in [None,1,"xyz"]:
            p = self.proxy(ob)
            self.failUnless( unproxy(p) is ob )
            self.failUnless( unproxy(ob) is ob )

    def testGetAttr(self):
        p = self.proxy("abc").xyz
        self.assertEqual( unproxy(p), ('.','abc','xyz') )
        q = p.qrs
        self.assertEqual( unproxy(q), ('.',unproxy(p),'qrs') )
        z = p.zimmish
        self.assertEqual( unproxy(z), ('.',unproxy(p),'zimmish') )

    def testRichComps(self):
        one, two = self.proxy(1), self.proxy(2)
        self.assertEqual(unproxy(one<two), ('<',1,2))
        self.assertEqual(unproxy(one<=two), ('<=',1,2))
        self.assertEqual(unproxy(one==two), ('==',1,2))
        self.assertEqual(unproxy(one!=two), ('!=',1,2))
        self.assertEqual(unproxy(one>two), ('>',1,2))
        self.assertEqual(unproxy(one>=two), ('>=',1,2))

    def testCall(self):
        one, two = self.proxy(1), self.proxy(2)
        self.assertEqual( unproxy(one(two)), ('()',1,(2,),{}) )
        self.assertEqual( unproxy(one(one,two)), ('()',1,(1,2,),{}) )
        self.assertEqual(
            unproxy(one(one,two,3,four=5,one=one)),
            ('()',1,(1,2,3),{'four':5,'one':1})
        )



    def testGetItem(self):
        one, two = self.proxy(1), self.proxy(2)
        self.assertEqual( unproxy( one[two] ),  ('[]',1,2) )
        self.assertEqual( unproxy( one[two.three] ), ('[]',1,('.',2,'three')) )
        self.assertEqual( unproxy( one.three[two] ), ('[]',('.',1,'three'),2) )

    def testArithmeticOps(self):
        one, two = self.proxy(1), self.proxy(2)

        self.assertEqual( unproxy( one + two ), ('+',1,2) )
        self.assertEqual( unproxy( one + 2.0 ), ('+',1,2) )
        self.assertEqual( unproxy( 1 + two ),   ('+',1,2) )

        self.assertEqual( unproxy( one - two ), ('-',1,2) )
        self.assertEqual( unproxy( one - 2 ),   ('-',1,2) )
        self.assertEqual( unproxy( 1.0 - two ), ('-',1,2) )

        self.assertEqual( unproxy( one * two ), ('*',1,2) )
        self.assertEqual( unproxy( one * 2.0 ), ('*',1,2) )
        self.assertEqual( unproxy( 1 * two ),   ('*',1,2) )

        self.assertEqual( unproxy( "one" * two ), ('*','one',2) )
        self.assertEqual( unproxy( one * "two" ), ('*',1,'two') )

        self.assertEqual( unproxy( one // two ), ('//',1,2) )
        self.assertEqual( unproxy( one // 2 ),   ('//',1,2) )
        self.assertEqual( unproxy( 1.0 // two ), ('//',1,2) )

        self.assertEqual( unproxy( one % two ), ('%',1,2) )
        self.assertEqual( unproxy( one % 2.0 ), ('%',1,2) )
        self.assertEqual( unproxy( 1 % two ),   ('%',1,2) )

        self.assertEqual( unproxy( one ** two ), ('**',1,2) )
        self.assertEqual( unproxy( one ** 2 ),   ('**',1,2) )
        self.assertEqual( unproxy( 1.0 ** two ), ('**',1,2) )

        self.assertEqual( unproxy( one / two ), ('/',1,2) )
        self.assertEqual( unproxy( one / 2.0 ), ('/',1,2) )
        self.assertEqual( unproxy( 1 / two ),   ('/',1,2) )


    def testBitwiseOps(self):
        one, two = self.proxy(1), self.proxy(2)

        self.assertEqual( unproxy( one << two ), ('<<',1,2) )
        self.assertEqual( unproxy( one << 2.0 ), ('<<',1,2) )
        self.assertEqual( unproxy( 1 << two ),   ('<<',1,2) )

        self.assertEqual( unproxy( one >> two ), ('>>',1,2) )
        self.assertEqual( unproxy( one >> 2 ),   ('>>',1,2) )
        self.assertEqual( unproxy( 1.0 >> two ), ('>>',1,2) )

        self.assertEqual( unproxy( one & two ), ('&',1,2) )
        self.assertEqual( unproxy( one & 2.0 ), ('&',1,2) )
        self.assertEqual( unproxy( 1 & two ),   ('&',1,2) )

        self.assertEqual( unproxy( one | two ), ('|',1,2) )
        self.assertEqual( unproxy( one | 2 ),   ('|',1,2) )
        self.assertEqual( unproxy( 1.0 | two ), ('|',1,2) )

        self.assertEqual( unproxy( one ^ two ), ('^',1,2) )
        self.assertEqual( unproxy( one ^ 2.0 ), ('^',1,2) )
        self.assertEqual( unproxy( 1 ^ two ),   ('^',1,2) )


    def testUnaryOps(self):
        one, two = self.proxy(1), self.proxy(2)

        self.assertEqual( unproxy(+two), ('u+',2) )
        self.assertEqual( unproxy(++two), ('u+',('u+',2)) )
        self.assertEqual( unproxy(+-two), ('u+',('u-',2)) )
        self.assertEqual( unproxy(-+two), ('u-',('u+',2)) )

        self.assertEqual( unproxy(~one), ('~',1) )
        self.assertEqual( unproxy(~~one), ('~',('~',1)) )







TestClasses = (
    ProxyTests,
)

def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])



































