from unittest import TestCase, makeSuite, TestSuite
from peak.api import *
from peak.tests import testRoot
import peak.web.sitemaps as sm
from urllib import quote
from test_resources import ResourceApp1

class ParserTests(TestCase):

    def setUp(self,**kw):
        kw.setdefault('parent',testRoot())
        self.xml_parser = config.XMLParser(
            web.SITEMAP_SCHEMA(testRoot()),
            sm_globals=globals(), **kw
        )
        self.parse = self.xml_parser.parse

        self.nparser = nparser = self.xml_parser.makeParser()
        self.startElement = nparser.startElement
        self.endElement = nparser.endElement
        nparser._beforeParsing(self.xml_parser.parseFunctions())
        self.finish = nparser._afterParsing
        self.policy = web.TestPolicy(ResourceApp1(testRoot()))

    def traverse(self,start,name):
        return self.policy.newContext(start=start).traverseName(name)

    def testRoot(self):
        self.startElement('location',[])
        v = self.endElement('location')
        self.failUnless(web.IPlace(v) is v)
        self.assertEqual(v.place_url,'')









    def testChild(self):
        self.startElement('location',[])
        self.startElement('location',['name','foo'])
        inner = self.endElement('location')
        self.failUnless(web.IPlace(inner) is inner)
        self.assertEqual(inner.place_url,'foo')
        outer = self.endElement('location')
        self.failUnless(inner.getParentComponent() is outer)
        self.assertEqual(outer.place_url,'')
        self.failUnless(self.traverse(outer,'foo').current is inner)

    def testRootIsValid(self):
        self.assertRaises(SyntaxError, self.startElement, 'nosuchthing',[])

    def testRootIsNameless(self):
        self.assertRaises(SyntaxError,
            self.startElement, 'location',['name','foo'])

    def testLocationClassAndGlobals(self):
        self.startElement('location',['class','TestLocation'])
        self.startElement('location',['name','x','class','TestLocation'])
        self.startElement('location',['name','y'])
        self.failIf(isinstance(self.endElement('location'),TestLocation))
        self.failUnless(isinstance(self.endElement('location'),TestLocation))
        self.failUnless(isinstance(self.endElement('location'),TestLocation))

    def testImportElement(self):
        self.startElement('location',[])
        self.startElement('import',['module','peak.web.tests.test_sitemap'])
        self.assertEqual(self.endElement('import'),None)
        self.startElement('location',
            ['class','test_sitemap.TestLocation','name','x'])
        self.failUnless(isinstance(self.endElement('location'),TestLocation))

    def testImportEmpty(self):
        self.startElement('location',[])
        self.startElement('import',['module','peak.web.tests.test_sitemap'])
        self.assertRaises(SyntaxError, self.startElement, 'location',[])



    def testRootIsLocation(self):
        self.assertRaises(SyntaxError, self.startElement,
            'import',['module','peak.web.tests.test_sitemap'])

    def testInvalidAttrs(self):
        self.assertRaises(SyntaxError,
            self.startElement, 'location',['foo','bar'])

    def testMissingAttrs(self):
        self.startElement('location',[])
        self.assertRaises(SyntaxError, self.startElement, 'import',[])

    def testChildLocationMustBeNamed(self):
        self.startElement('location',[])
        self.assertRaises(SyntaxError, self.startElement, 'location',[])

    def testContainer(self):
        self.startElement('location',[])
        self.startElement('location',['name','foo'])
        self.startElement('container',['object','globals()'])
        self.endElement()
        loc = self.endElement()
        self.failUnless(
            self.traverse(loc,'TestLocation').current is TestLocation
        )
        self.startElement('location',['name','bar'])
        self.startElement('container',
            ['object','globals()','permission','security.Nobody']
        )
        self.endElement()
        loc = self.endElement()
        self.assertRaises(web.NotFound, self.traverse, loc, 'TestLocation')

    def testLocationId(self):
        self.startElement('location',['id','outer'])
        self.startElement('location',['id','inner', 'name','xyz'])
        inner = self.endElement()
        outer = self.endElement()
        self.failUnless(self.traverse(outer,'++id++outer').current is outer)
        self.failUnless(self.traverse(outer,'++id++inner').current is inner)

    def testOfferPath(self):
        self.startElement('location',[])
        self.startElement('offer',['path','foo', 'as','bar'])
        self.endElement()
        self.startElement('location',['name','foo'])
        foo = self.endElement()
        loc = self.endElement()
        self.failUnless(
            self.traverse(loc,'++id++bar').current is foo
        )

    def testRequirePermission(self):
        self.startElement('location', [])

        self.startElement('location',['name','foo'])
        self.startElement('require',['permission','security.Anybody'])
        self.startElement('container',['object','globals()',])
        self.endElement('container')
        self.endElement('require')
        foo = self.endElement('location')
        self.failUnless(
            self.traverse(foo,'TestLocation').current is TestLocation
        )

        self.startElement('location',['name','bar'])
        self.startElement('require',['permission','security.Nobody'])
        self.startElement('container',['object','globals()',])
        self.endElement('container')
        self.endElement('require')
        bar = self.endElement('location')
        self.assertRaises(web.NotFound, self.traverse, bar, 'TestLocation')

    def testContainerSuggestion(self):
        global testComponent; testComponent = binding.Component()
        self.startElement('location',[])
        self.startElement('container',['object','testComponent'])
        self.endElement()
        loc = self.endElement()
        self.failUnless(testComponent.getParentComponent() is loc)


    def testNotAllowedInContent(self):
        self.startElement('location', [])
        self.startElement('content', ['type','int'])
        self.assertRaises(SyntaxError, self.startElement,
            'offer',['path','foo', 'as','bar'])
        self.endElement('offer')
        self.assertRaises(SyntaxError, self.startElement,
            'container',['object','{}'])
        self.endElement('container')
        self.assertRaises(SyntaxError, self.startElement,
            'content',['type','int'])
        self.endElement('content')
        self.assertRaises(SyntaxError, self.startElement,
            'location',['name','x'])
        self.endElement('location')


    def testChoice(self):
        choose = lambda names,**kw: sm.choose(self.nparser,names,kw)
        self.assertRaises(SyntaxError, choose, ('a','b'))
        self.assertEqual(choose(['a','b'],b=1), ('b',1))
        self.assertRaises(SyntaxError, choose, ('a','b'), a=1, b=2)


    def testViewWrappers(self):
        ctx = self.policy.newContext()
        permHandler = sm.addPermission(nullHandler,security.Nobody)
        self.assertRaises(web.NotAllowed,permHandler,ctx,None,'','x','x')
        permHandler = sm.addPermission(nullHandler,security.Anybody)
        self.failUnless(permHandler(ctx,None,'','x','x').current is None)
        helpedHandler = sm.addHelper(nullHandler,lambda x: [x])
        c2 = helpedHandler(ctx,None,'','x','x')
        self.assertEqual(c2.current, [None])
        self.assertEqual(c2.previous.current, [None])







    def testBasicViews(self):
        end=self.endElement
        self.startElement('location', ['id','root'])
        self.startElement('content', ['type','int', 'location','baz@root'])
        self.startElement('view',['name','foo','object','"xyz"']); end()
        self.startElement('view',['name','bar','attribute',"__class__"]); end()
        self.startElement('view',['name','baz','expr','ob','helper','repr'])
        end()
        self.startElement('view',['name','fiz','function','nullHandler']);end()
        self.startElement('view',
            ['name','fuz','resource','peak.web.tests/template1']
        );end(); end('content')
        loc = end('location')
        ctx = self.policy.newContext(start=loc).childContext('test',123)
        ctx = loc.beforeHTTP(ctx)
        self.assertEqual(ctx.traverseName("foo").current, "xyz")
        self.assertEqual(ctx.traverseName("bar").current, int)
        self.assertEqual(ctx.traverseName("baz").current, "123")
        self.assertEqual(ctx.traverseName("fiz").current, 123)
        self.assertEqual(ctx.url, "123")
        self.failUnless(isinstance(ctx.traverseName("fuz").current,
                web.TemplateDocument))

    def testViewHandlers(self):
        ctx = self.policy.newContext()
        handler = sm.attributeView('url')
        self.assertEqual(handler(ctx,ctx,'','x','x').current, ctx.url)
        handler = sm.objectView(123)
        self.assertEqual(handler(ctx,ctx,'','x','x').current, 123)
        handler = sm.resourceView('peak.web.tests/template1')
        self.failUnless(isinstance(handler(ctx,ctx,'','x','x').current,
            web.TemplateDocument))

    def testExtendedLocation(self):
        self.setUp(sm_included_from={'name':'foo','class':'TestLocation'},
            parent=web.Location(testRoot()))
        self.startElement('location', [])
        loc = self.endElement('location')
        self.assertEqual(loc.getComponentName(), 'foo')
        self.failUnless(isinstance(loc,TestLocation))

    def testLocationExtends(self):
        start, end = self.startElement, self.endElement
        start('location', ['extends','data:,'+quote("""
                <location id="nested.root">
                <view name="x" object="'spot'"/>
                <content type="object"><view name="bar" object="123"/>
                </content>
                <import module="peak.web.tests.test_sitemap" as="tsm"/>
                <location name="foo" class="tsm.TestLocation"/>
                </location>"""), 'id','root'
            ]
        )
        start('view',['name','x','object','"marksThe"']); end()
        start('container',['object','{"123":123}']); end()
        start('content', ['type','object'])
        start('view',['name','bar','object','"xyz"']); end(); end('content')
        loc = self.endElement('location')
        self.failUnless(
            isinstance(self.traverse(loc,'foo').current,TestLocation)
        )
        self.failUnless(self.traverse(loc,'++id++root').current is loc)
        self.failUnless(self.traverse(loc,'++id++nested.root').current is loc)

        ctx = self.policy.newContext(start=loc)
        self.assertEqual(ctx.traverseName('@@x').current, "marksThe")
        ctx = ctx.traverseName('123')
        self.assertEqual(ctx.traverseName('@@bar').current, "xyz")


    def testAllow(self):
        end=self.endElement
        self.startElement('location', [])
        self.startElement('content', ['type','object'])
        self.startElement('allow',['attributes','__class__,__doc__']); end()
        end(); loc=end()
        ctx = self.policy.newContext(start=loc).childContext('test',123)
        self.assertEqual(ctx.traverseName("__doc__").current,(123).__doc__)
        self.assertEqual(ctx.traverseName("__class__").current,(123).__class__)



    def testLocationConfigure(self):
        self.startElement('location',
            ['config','pkgfile:peak.web.tests/configure-test.ini'])
        loc = self.endElement()
        self.assertEqual(
            config.lookup(loc,'peak.web.resource_packages.peak.web.tests'),
            True
        )


    def testConflictingViews(self):
        end=self.endElement
        self.startElement('location',[])
        self.startElement('content', ['type','object'])
        self.startElement('view',['name','foo','object','"xyz"']); end()
        end('content')
        self.startElement('content', ['type','int'])
        self.startElement('view',['name','foo','object','"xyz"']); end()
        self.assertRaises(SyntaxError, self.startElement,
            'view',['name','foo','object','123'])


    def testLocationView(self):
        self.startElement('location',[])
        self.startElement('view',['name','foo','object','"xyz"'])
        self.endElement()
        loc = self.endElement()
        ctx = self.policy.newContext(start=loc).traverseName('foo')
        self.assertEqual(ctx.current,"xyz")


    def testLocationAllow(self):
        self.startElement('location',[])
        self.startElement('allow',['attributes','__class__'])
        self.endElement()
        loc = self.endElement()
        ctx = self.policy.newContext(start=loc).traverseName('__class__')
        self.assertEqual(ctx.current,web.Location)



    def testLocationConflicts(self):
        self.startElement('location',[])
        self.startElement('allow',['attributes','__class__'])
        self.assertRaises(SyntaxError, self.startElement,
            'view',['name','__class__','object','123'])

    def testContainerSequence(self):
        self.startElement('location',[])
        self.startElement('container',['object','{"foo":"bar"}'])
        self.endElement()
        self.startElement('container',['object','{"foo":"baz"}'])
        self.endElement()
        loc = self.endElement()
        self.assertEqual(self.traverse(loc,'foo').current, "bar")

    def testContainerInheritance(self):
        start, end = self.startElement, self.endElement
        self.startElement('location', ['extends','data:,'+quote(
                """<location><container object="{'foo':'baz'}"/></location>"""
                ), 'id','root'
            ]
        )
        self.startElement('container',['object','{"foo":"bar"}'])
        self.endElement()
        loc = self.endElement()
        self.assertEqual(self.traverse(loc,'foo').current, "bar")

    def testContainerLookup(self):
        self.startElement('location',[])
        self.startElement('container',['lookup','storage.ITransactionService'])
        cnt, loc = self.endElement(), self.endElement()
        self.failUnless(
            cnt is binding.lookupComponent(loc,storage.ITransactionService)
        )

    def testContainerOutsideLoc(self):
        self.assertRaises(SyntaxError,
            self.startElement, 'container',['object','None'])



    def testContainerAttrs(self):
        self.startElement('location', [])
        self.assertRaises(SyntaxError, self.startElement, 'container',
            ['object','None','lookup','None']
        )
        self.assertRaises(SyntaxError, self.startElement, 'container', [])


class TestLocation(web.Location):
    pass


def nullHandler(ctx, ob, namespace, name, qname, default=NOT_GIVEN):
    return ctx.childContext(qname,ob)



























TestClasses = (
    ParserTests,
)

def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])



































