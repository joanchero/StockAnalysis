from unittest import TestCase, makeSuite, TestSuite
from peak.api import *
from peak.tests import testRoot

from test_templates import TestApp, BasicTest

class ResourceApp1(TestApp):

    # This makes all 'peak.*' package resources available for testing;
    # Ordinarily, you'd do this via a config file, but this is quick and easy

    __makePkgAvailable = binding.Make(lambda: True,
        offerAs = ['peak.web.resource_packages.peak.*']
    )

    show = web.bindResource('template1')

class MethodTest1(BasicTest):

    appClass = ResourceApp1

    def setUp(self):
        r = testRoot()
        self.policy = web.TestPolicy(self.appClass(r))

















class ResourceApp2(ResourceApp1):

    show = web.bindResource('template2')

    xml = web.bindResource(
        '/peak.running/EventDriven', metadata=[security.Anybody]
    )

class MethodTest2(MethodTest1):
    appClass = ResourceApp2

    rendered = """<body xmlns:this="mid:pwt-this@peak-dev.org">
<h1>The title (with &lt;xml/&gt; &amp; such in it)</h1>

<ul><li>1</li><li>2</li><li>3</li></ul>

<a href="++resources++/peak.running/EventDriven.xml">
The EventDriven.xml file, found at
http://127.0.0.1/++resources++/peak.running/EventDriven.xml
</a>

</body>
"""


















class LocationTests(TestCase):

    def setUp(self):
        self.root = web.Location(testRoot())
        self.policy = web.TestPolicy(self.root)
        self.ctx = self.policy.newContext()

    def testBasics(self):
        self.failUnless(web.IConfigurableLocation(self.root) is self.root)
        self.assertEqual(self.root.place_url, '')

    def testContainers(self):
        c1 = {'bar':'baz'}; c2={'foo':'bar'}
        self.assertEqual(self.ctx.traverseName('foo',None), None)
        self.assertEqual(self.ctx.traverseName('bar',None), None)
        self.root.addContainer(c1,security.Nobody)
        self.assertEqual(self.ctx.traverseName('foo',None), None)
        self.assertEqual(self.ctx.traverseName('bar',None), None)
        self.root.addContainer(c2)
        self.assertEqual(self.ctx.traverseName('foo',None).current, 'bar')
        self.assertEqual(self.ctx.traverseName('bar',None), None)
        self.root.addContainer(c1,security.Anybody)
        self.assertEqual(self.ctx.traverseName('foo',None).current, 'bar')
        self.assertEqual(self.ctx.traverseName('bar',None).current, 'baz')
        self.failUnless(
            web.TraversalPath('bar/..').traverse(self.ctx).current is self.root
        )

    def testOffers(self):
        self.root.addContainer({'bar':'baz'})
        self.root.registerLocation('test.1','bar')
        self.assertEqual(
            self.ctx.traverseName('++id++test.1',None).current,'baz'
        )
        self.root.registerLocation('test2','.')
        self.failUnless(self.ctx.traverseName('++id++test2') is self.ctx)

    def testAppViews(self):
        self.checkView(self.root,int,123)
        self.checkView(self.root,protocols.IOpenProtocol,web.IWebTraversable)

    def checkView(self,loc,tgt,src):
        bar_handler = lambda ctx,o,ns,nm,qn,d: ctx.childContext(qn,"baz")
        subLoc = web.Location(loc)
        loc.addContainer({'spam':subLoc})
        subLoc.registerView(tgt,'bar',bar_handler)
        subLoc.addContainer({'foo':src})
        ctx = web.TraversalPath('spam/foo/@@bar').traverse(
            self.ctx.clone(current=loc)
        )
        self.assertEqual(ctx.current,'baz')

    def testNestedViews(self):
        loc = web.Location(self.root)
        self.checkView(loc,int,123)
        loc = web.Location(self.root)
        self.checkView(loc,protocols.IOpenProtocol,web.IWebTraversable)

    def testLocationView(self):
        loc = web.Location(self.root)
        bar_handler = lambda ctx,o,ns,nm,qn,d: ctx.childContext(qn,"baz")
        loc.registerView(None,'bar',bar_handler)
        loc.addContainer({'foo':loc})
        ctx = web.TraversalPath('foo/@@bar').traverse(
            self.ctx.clone(current=loc)
        )
        self.assertEqual(ctx.current,'baz')

    def testContainerSequence(self):
        c1 = {'foo':'baz'}; c2={'foo':'bar'}
        self.assertEqual(self.ctx.traverseName('foo',None), None)
        self.root.addContainer(c1)
        self.assertEqual(self.ctx.traverseName('foo',None).current, 'baz')
        self.root.addContainer(c2)
        self.assertEqual(self.ctx.traverseName('foo',None).current, 'bar')







class ResourceTests(TestCase):

    def testSubObjectRejection(self):
        # Files and templates shouldn't allow subitems in PATH_INFO
        paths = 'peak.web/resource_defaults.ini', 'peak.web.tests/template1'
        policy = web.TestPolicy(ResourceApp1(testRoot()))
        for path in paths:
            try:
                policy.simpleTraverse('/++resources++/%s/subitem' % path, True)
            except web.NotFound,v:
                self.assertEqual(v.args[0], "subitem")
            else:
                raise AssertionError("Should have raised NotFound:", path)

    def testURLcalculations(self):

        # Root locations: direct children of a non-IPlace parent
        r=web.Resource(testRoot())
        self.assertEqual(r.place_url,'')
        r=web.Resource(testRoot(),'foo')
        self.assertEqual(r.place_url,'')

        # Skin path is resource prefix
        policy = web.TestPolicy(ResourceApp1(testRoot()))
        ctx = policy.simpleTraverse('/++resources++', False)
        self.assertEqual(ctx.current.place_url, '++resources++')

        # Skin children should include resource prefix
        ctx2 = ctx.traverseName('peak.web')
        self.assertEqual(ctx2.current.place_url, '++resources++/peak.web')

        # check absolute ("mount point") URL
        r=web.Resource(testRoot(),'foo',place_url="http://example.com/foo")
        ctx = policy.newContext()
        ctx = ctx.childContext('foo',r)
        self.assertEqual(ctx.absoluteURL, ctx.current.place_url)





class IntegrationTests(TestCase):
    def setUp(self):
        self.policy = web.TestPolicy(
            testRoot().lookupComponent(
                'ref:sitemap@pkgfile:peak.web.tests/test-sitemap.xml'
            )
        ); self.traverse = self.policy.simpleTraverse

    def testIntView(self):
        self.assertEqual(self.traverse('123/index_html'),
            "<html>\n" " <head>\n" "  <title>Python Object 123</title>\n"
            " </head>\n"
            " <body>\n"
            "<h1>Python Object 123</h1>\n" "<hr />\n"
            "My URL is http://127.0.0.1/123.\n"
            "The server name as a property: "
            "<span>PropertyName('127.0.0.1')</span>\n"
            "<hr />\n" "</body></html>\n"
        )

    def testListView(self):
        self.assertEqual(self.traverse('both/index_html'),
            "<html>\n" " <head>\n"
            "  <title>Python Object [123, 'abc']</title>\n"
            " </head>\n"
            " <body>\n" "<h1>Python Object [123, 'abc']</h1>\n" "<hr />\n"
            "<table><tr>\n" "<td>Name</td><td>Last modified</td><td>Size</td>"
            "<td>Description</td>\n" "</tr><tr>\n"
            "<td><a href=\"../123\">123</a></td>\n" "<td /><td /><td />\n"
            "</tr><tr>\n" "<td><a href=\"../abc\">'abc'</a></td>\n"
            "<td /><td /><td />\n" "</tr></table>\n" "<hr />\n"
            "</body></html>\n"
        )

    def testViewDef(self):
        self.assertEqual(self.traverse('/@@index_html', False).current, 1)

    def testLayout(self):
        self.assertEqual(self.traverse('123/layout-test'),
            "<html><div>123</div></html>\n")

TestClasses = (
    LocationTests, MethodTest1, MethodTest2, ResourceTests, IntegrationTests
)

def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])



































