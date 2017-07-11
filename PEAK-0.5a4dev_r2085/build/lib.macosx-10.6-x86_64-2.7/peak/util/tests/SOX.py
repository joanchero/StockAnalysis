"""Tests for SOX"""

from unittest import TestCase, makeSuite, TestSuite
from cStringIO import StringIO
from xml.sax import InputSource
from peak.util import SOX

def stream(str):
    inpsrc = InputSource()
    inpsrc.setByteStream(StringIO(str))
    return inpsrc


class SOXTest(TestCase):

    text = "<nothing/>"

    useNS = False

    def setUp(self):
        self.object = ob = SOX.load(stream(self.text), namespaces=self.useNS)
        self.de = ob.documentElement



















class Simple(SOXTest):

    text = """<top foo="bar" baz="spam">TE<middle/>XT</top>"""

    def testTop(self):
        assert self.de._name == 'top'

    def testNodelist(self):
        object = self.object
        top = object._get('top')
        assert len(top)==1
        assert object.top is top

    def testText(self):
        t = []
        for n in self.de._allNodes:
            if n == str(n): t.append(n)
        assert ''.join(t) == 'TEXT'

    def testAttrs(self):
        assert self.de.foo=='bar'
        assert self.de.baz=='spam'


class NSTest(SOXTest):
    text = """
        <xmi:XMI xmlns:xmi="http://omg.org/XMI/2.0" xmlns="www.zope.org">
            <xmi:model name="MOF" version="1.3"/> [0]
            <Model:Package name="foo" xmlns:Model="http://omg.org/MOF/1.3"/> [1]
            <thingy/> [2]
        </xmi:XMI>"""

    useNS = True

    def testModel(self):
        node = self.de._subNodes[1]
        assert node.ns2uri['Model']=='http://omg.org/MOF/1.3'
        node = self.de._subNodes[2]
        assert 'Model' not in node.ns2uri
        assert node.ns2uri[''] == "www.zope.org"

class NegotiationTests(TestCase):

    def setUp(self):
        self.n = SOX.NegotiatingParser()
        self.attrs = []
        self.log = []
        self.n.element_map['nothing'] = self.nothing

    def nothing(self,neg,data):
        self.failUnless(neg is self.n)
        self.assertEqual(data['name'],       'nothing')
        self.assertEqual(data['attributes'], self.attrs)
        data['finish']=lambda *args: 99
        self.log.append(True)    # we ran

    def lookup_element(self,ns,name):
        self.log.append(name)

    def check_log(self,data):
        self.assertEqual(self.log,data)


    def testElementMatching(self):
        self.n.setLookups(self.lookup_element)
        self.n.element_map['nothing'] = self.nothing
        self.n.startElement("nothing",[])
        self.check_log([True])

        self.log=[]
        self.attrs = [('foo','bar')]
        self.n.startElement('abc',[])
        self.n.startElement('nothing',['foo','bar'])
        self.assertEqual(self.log, ['abc',True])

        self.log=[]
        self.attrs = []
        self.n.startElement('nothing',[])
        self.n.startElement('nothing',[])
        self.check_log([True,True])


    def testElementLookup(self):
        self.n.startElement('xyz',[])
        self.check_log([])
        self.n.setLookups(self.lookup_element)
        self.assertEqual(self.n.element_map,{})   # Cache should be cleared

        self.n.startElement('xyz',[])
        self.check_log(['xyz'])


    def testCachePerNamespace(self):
        e1 = self.n.element_map
        a1 = self.n.attribute_map
        self.n.startElement('nothing',['xmlns','foobly'])
        # Verify that declaring XMLNS clears element cache *before* negotiation
        self.check_log([])
        e2 = self.n.element_map
        a2 = self.n.attribute_map
        self.failIf(e1 is e2 or a1 is a2)

        self.n.startElement('bar',['xmlns:foo','spam'])
        e3 = self.n.element_map
        a3 = self.n.attribute_map
        self.failIf(e2 is e3 or a2 is a3)
        self.failIf(e1 is e3 or a1 is a3)

        # Cache should stay the same if no new namespaces declared
        self.n.startElement('baz',[])
        self.failUnless(self.n.element_map is e3)
        self.failUnless(self.n.attribute_map is a3)
        self.n.endElement('baz')

        self.n.endElement('bar')
        self.failUnless(self.n.element_map is e2)
        self.failUnless(self.n.attribute_map is a2)

        self.n.endElement('nothing')
        self.failUnless(self.n.element_map is e1)
        self.failUnless(self.n.attribute_map is a1)


    def testSingleXMLNamespace(self):
        self.assertEqual(self.n.ns_info, {})
        self.n.startElement('foo',['xmlns','foobly'])
        self.assertEqual(self.n.ns_info, {'':['foobly']})
        self.n.startElement('foo',['xmlns','barbaz'])
        self.assertEqual(self.n.ns_info, {'':['foobly','barbaz']})
        self.n.startElement('bar',['xmlns:baz','spam'])
        self.assertEqual(
            self.n.ns_info, {'':['foobly','barbaz'], 'baz':['spam']}
        )
        self.n.endElement('bar')
        self.assertEqual(self.n.ns_info, {'':['foobly','barbaz'],'baz':[]})
        self.n.endElement('foo')
        self.assertEqual(self.n.ns_info, {'':['foobly'],'baz':[]})


    def testMultipleNS(self):
        self.n.startElement('foo',['xmlns:a','foobly', 'xmlns:b','do'])
        self.assertEqual(self.n.ns_info, {'a':['foobly'],'b':['do']})
        self.n.endElement('foo')
        self.assertEqual(self.n.ns_info, {'a':[],'b':[]})
        self.n.startElement('whee',[])
        self.n.endElement('whee')
        self.assertEqual(self.n.ns_info, {'a':[],'b':[]})


    def testSaveLookups(self):
        el1 = self.n.lookup_element; ec1 = self.n.element_map
        al1 = self.n.lookup_attribute; ac1 = self.n.attribute_map
        self.n.startElement('xyz',[])
        self.n.setLookups(self.lookup_element,self.lookup_element)
        el2 = self.n.lookup_element; ec2 = self.n.element_map
        al2 = self.n.lookup_attribute; ac2 = self.n.attribute_map
        self.failIf(el1 is el2 or al1 is al2 or ec1 is ec2 or ac1 is ac2)
        self.n.endElement('xyz')
        el3 = self.n.lookup_element; ec3 = self.n.element_map
        al3 = self.n.lookup_attribute; ac3 = self.n.attribute_map
        self.failUnless(el1 is el3 and al1 is al3)
        self.failUnless(ec1 is ec3 and ac1 is ac3)


    def testLifecycle(self):

        def do_start(neg,data):
            self.failUnless(neg is self.n)
            self.log.append("started")    # we ran

        def do_finish(neg,data):
            self.failUnless(neg is self.n)
            self.log.append("finished")    # we ran
            return 7

        def do_child(child):
            self.log.append(("child",child))    # we ran

        def tag_one(neg,data):
            self.failUnless(neg is self.n)
            self.assertEqual(data['name'],'tag1')
            data['start'] = do_start
            data['finish'] = do_finish
            data['child'] = do_child

        self.n.element_map['tag1'] = tag_one
        self.n.startElement('tag1',[])
        self.check_log(['started'])

        self.n.startElement('foo',['a','b','c','d'])
        self.n.endElement('foo')
        self.check_log(['started'])

        self.n.endElement('tag1')
        self.check_log(['started','finished'])

        self.log = []
        self.n.startElement('tag1',[])
        self.n.startElement('tag1',[])
        self.n.endElement('tag1')
        self.n.endElement('tag1')
        self.check_log(['started','started','finished',('child',7),'finished'])



    def testAttributeLookup(self):

        self.n.startElement("xyz",['a:b','c', 'd', 'e'])
        self.check_log([])

        # Setting lookup should clear caches
        self.n.setLookups(attribute=self.lookup_element)
        self.assertEqual(self.n.element_map,{})
        self.assertEqual(self.n.attribute_map,{})

        self.n.startElement("xyz",['a:b','c', 'd', 'e'])
        self.check_log(['a:b'])
        self.n.startElement("xyz",['a:b','x', 'c:d', 'e'])
        self.check_log(['a:b','c:d'])

        def got_ef(neg,data,attr,val):
            self.assertEqual(attr,'e:f')
            self.assertEqual(val,'g')
            self.log.append('got it!')
            self.failUnless( ('e:f','g') in data['attributes'])

        self.n.attribute_map['e:f'] = got_ef
        self.attrs = [('e:f','g')]
        self.n.startElement("nothing",['e:f','g'])
        self.check_log(['a:b','c:d', 'got it!'])

        # Verify that declaring XMLNS clears attrib cache *before* negotiation
        self.log=[]
        self.n.startElement("xyz",["xmlns:foo","bar", 'e:f','g'])
        self.check_log(['e:f'])











    def testText(self):

        def tag_one(neg,data):
            self.failUnless(neg is self.n)
            self.assertEqual(data['name'],'tag1')
            data['text'] = do_text
            data['literal'] = do_literal

        def do_text(text):
            self.log.append(('txt',text))

        def do_literal(text):
            self.log.append(('lit',text))

        self.n.element_map['tag1'] = tag_one
        self.n.text("foo")
        self.n.literal("bar")
        self.n.comment("ping")
        self.check_log([])

        self.n.startElement('tag1',[])
        self.n.text("baz")
        self.n.literal("spam")
        self.n.comment("whiz")
        self.check_log([('txt','baz'),('lit','spam'),('lit','<!--whiz-->')])

        self.log = []
        self.n.endElement('tag1')
        self.n.text("baz")
        self.n.literal("spam")
        self.n.comment("ni!")
        self.check_log([])









    def parse(self,data,root,stream=False):
        if stream:
            return self.n.parseStream(StringIO(data),root)
        return self.n.parseString(data,root)


    def testParses(self):
        for mode in True,False:
            self.setUp()    # ensure clean slate between parses           
            result = self.parse('<nothing/>', {
                'start':lambda *args:self.log.append("started"),
                'finish':lambda *args:27
            }, mode)
            self.assertEqual(result,27)
            self.check_log(["started",True])
    
            self.parse(
                '<!--x--><nothing/>',
                {'literal':self.log.append, 'child':self.log.append},
                mode
            )
            self.check_log(["started",True,'<!--x-->',True,99])


    def testNSLookups(self):
        
        def lookup(ns,name):
            self.log.append((ns,name))

        self.n.setLookups(lookup,lookup)
        self.n.startElement('foo',['xmlns:a','foobly','xmlns:b','do'])
        self.check_log([(None,'foo')])

        self.log = []
        self.n.startElement('a:b',['b:c','foo','c:d','bar'])
        self.check_log([('foobly','b'),('do','c'),(None,'c:d')])

        



    def testNSAddAndSplit(self):
        self.n.startElement('foo',[])
        self.n.addNamespace('a','foobly')
        self.n.addNamespace('b','do')
        self.assertEqual(self.n.ns_info, {'a':['foobly'],'b':['do']})
        self.assertEqual(self.n.splitName('a:b'), ('foobly','b'))
        self.assertEqual(self.n.splitName('b:c'), ('do','c'))
        self.assertEqual(self.n.splitName('c:d'), (None,'c:d'))
        self.assertEqual(self.n.splitName('de'), (None,'de'))
        self.n.endElement('foo')

        self.assertEqual(self.n.splitName('a:b'), (None,'a:b'))
        self.assertEqual(self.n.ns_info, {'a':[],'b':[]})

        self.n.startElement('bar',[])
        self.n.addNamespace('','foobly')
        self.assertEqual(self.n.ns_info, {'':['foobly'],'a':[],'b':[]})
        self.n.endElement('bar')


    def testEmptyTag(self):
        def set_empty(neg,data):
            data['empty'] = True
        self.n.element_map['foo'] = set_empty
        self.n.startElement('foo',[])
        self.assertRaises(SyntaxError,self.n.startElement,'bar',[])
        self.n.endElement('foo')
        self.n.startElement('bar',[])
        

        










TestClasses = (
    Simple, NSTest, NegotiationTests
)

def test_suite():
    s = []
    for t in TestClasses:
        s.append(makeSuite(t,'test'))

    return TestSuite(s)































