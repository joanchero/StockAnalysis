"""Template tests

TODO

 - Mixed namespaces

 - DOMlet property redefinition within a component

 - Security used

 - DOCTYPE
"""

from unittest import TestCase, makeSuite, TestSuite
from peak.api import *
from peak.tests import testRoot
from cStringIO import StringIO
import peak.web.templates as pwt
from urllib import quote

class TestApp(web.Location):

    binding.metadata(
        foo = security.Anybody,
        bar = security.Anybody,
        someXML = security.Anybody,
        baz = security.Nobody,
    )

    foo = "The title (with <xml/> & such in it)"
    baz = "can't touch this!"
    bar = 1,2,3

    someXML = "<li>This has &lt;xml/&gt; in it</li>"

    show = binding.Require(
        "Template to dump this out with",
        [security.Anybody]
    )


class BasicTest(TestCase):

    template = "pkgfile:peak.web.tests/template1.pwt"

    rendered = """<html><head>
<title>Template test: The title (with &lt;xml/&gt; &amp; such in it)</title>
</head>
<body>
<h1>The title (with &lt;xml/&gt; &amp; such in it)</h1>
<ul><li>1</li><li>2</li><li>3</li></ul>
<ul><li>This has &lt;xml/&gt; in it</li></ul>
<ul><li>This has &lt;xml/&gt; in it</li></ul>
</body></html>
"""

    def setUp(self):
        r = testRoot()
        app = TestApp(r, show = self.mkTemplate())
        self.policy = web.TestPolicy(app)

    def mkTemplate(self):
        return config.processXML(
            web.TEMPLATE_SCHEMA(testRoot()), self.template,
            pwt_document=web.TemplateDocument(testRoot())
        )

    def render(self):
        return self.policy.simpleTraverse('show')

    def testRendering(self):
        self.assertEqual(self.render(),self.rendered)










class NSTest(BasicTest):

    template = "data:,"+quote("""<body with:page-layout="/default">
<h1 content:replace="foo">Title Goes Here</h1>
<ul content:list="bar">
    <li this:is="listItem" content:replace="."></li>
</ul>
</body>""")

    rendered = """<body>
<h1>The title (with &lt;xml/&gt; &amp; such in it)</h1>
<ul><li>1</li><li>2</li><li>3</li></ul>
</body>"""


class NSTest2(NSTest):

    template = "data:,"+quote("""<body with:page-layout="/default">
<h1 this:unless="no-such-thing" content:replace="foo">Title Goes Here</h1>
<ul><div this:list="bar">
    <li this:is="listItem"><span this:replace=".">foo</span></li>
</div></ul>
</body>""")

class ListHeaderFooterTest(BasicTest):
    template = "data:,"+quote("""<ul
        this:is="page" this:uses="bar" content:list="."
    ><li this:is="header">Header</li><li this:is="listItem" content:replace="."
    ></li><li this:is="footer">Footer</li></ul>""")

    rendered = "<ul><li>Header</li><li>1</li><li>2</li><li>3</li>" \
               "<li>Footer</li></ul>"









class MiscTests(TestCase):

    def setUp(self):
        self.app = TestApp(testRoot())
        self.policy = web.TestPolicy(self.app)
        self.ctx = self.policy.newContext()

    def testParameters(self):

        class MockTemplate:
            protocols.advise(instancesProvide=[web.IDOMletRenderable])
            renderCt = 0
            def renderFor(_self,ctx,state):
                self.assert_(ctx is self.ctx)
                self.assertEqual(state,123)
                _self.renderCt+=1

        t = MockTemplate()
        p = pwt.Parameters(self.ctx,{'t':t, 'p':u'bar', 'd':123})
        ctx = self.ctx.childContext('xyz',p)
        c2 = ctx.traverseName('t')

        # Test a second time to ensure that result is cached
        c2 = ctx.traverseName('t')

        # It should render with the original context
        c2.current.renderFor(c2,123)

        # and the mock 'renderFor' should have been called exactly once:
        self.assertEqual(t.renderCt, 1)

        # Paths should be traversed from the start point
        c2 = ctx.traverseName('p')
        self.assertEqual(c2.current, (1,2,3))

        # And data should just be returned
        c2 = ctx.traverseName('d')
        self.assertEqual(c2.current, (123))



    def renderDoc(self,doc):
        ctx = self.ctx.childContext('x',doc)
        ctx.shift() # get rid of 'index.html'
        return ctx.renderHTTP()

    def renderFragment(self,doc):
        ctx = self.ctx.childContext('x',doc)
        ctx.shift() # get rid of 'index.html'
        data = []
        doc.renderFor(ctx, pwt.DOMletState(doc, write=data.append))
        return ''.join(data)

    def testContentType(self):
        s,h,b = self.renderDoc(
            pwt.TemplateDocument(
                self.app,
                content_type='text/plain', params={'page-layout':'/default'}
            )
        )
        self.assertEqual(h,[('Content-type','text/plain')])


    def testRenderFragment(self):
        doc = pwt.TemplateDocument(self.app,params={'page-layout':'/default'})
        doc.addChild(pwt.Literal(doc,xml="foo"))
        doc.fragment = pwt.Literal(doc,xml="bar")
        doc.addChild(doc.fragment)
        s,h,b = self.renderDoc(doc)
        self.assertEqual(''.join(b), "foobar")
        self.assertEqual(self.renderFragment(doc), "bar")

    def testRenderPage(self):
        doc = pwt.TemplateDocument(self.app)
        doc.addChild(pwt.Literal(doc,xml="foo"))
        doc.page = pwt.Literal(doc,xml="bar")
        doc.addChild(doc.page)
        s,h,b = self.renderDoc(doc)
        self.assertEqual(''.join(b), "bar")



    def testNonRendering(self):
        doc = pwt.TemplateDocument(self.app,fragment=None)
        self.assertRaises(TypeError,self.renderFragment,doc)
        doc = pwt.TemplateDocument(self.app,page=None)
        self.assertRaises(web.UnsupportedMethod,self.renderDoc,doc)


    def testUses(self):
        for kind in pwt.Uses, pwt.Unless:
            for path in "spammity-whiz","foo":
                doc = pwt.TemplateDocument(self.app)
                uses = kind(doc,dataSpec=path,tagName=None,attribItems=())
                uses.addChild(pwt.Literal(uses,xml="foo"))
                doc.addChild(uses)
                txt = self.renderFragment(doc)
                if (path=="foo") == (kind is pwt.Uses):
                    self.assertEqual(txt, "foo")
                else:
                    self.assertEqual(txt, "")






















class ParserTests(TestCase):

    def setUp(self,**kw):
        self.xml_parser = config.XMLParser(
            web.TEMPLATE_SCHEMA(testRoot()),
            pwt_document = web.TemplateDocument(testRoot()),
            **kw
        )
        self.parse = self.xml_parser.parse
        self.nparser = nparser = self.xml_parser.makeParser()
        self.startElement = nparser.startElement
        self.endElement = nparser.endElement
        nparser._beforeParsing(self.xml_parser.parseFunctions())
        self.finish = nparser._afterParsing
        self.policy = web.TestPolicy(TestApp(testRoot()))

    def testInvalidArgs(self):
        self.startElement('ul',['content:list','bar'])

        # Unrecognized argument for 'list'
        self.startElement('li',['this:is','invalid'])
        self.assertRaises(SyntaxError,self.endElement)

        # Multiple 'header' definitions
        self.startElement('li',['this:is','header'])
        self.endElement()
        self.startElement('li',['this:is','header'])
        self.assertRaises(SyntaxError,self.endElement)













    def testLayoutArgs(self):
        doc = self.parse("data:,"+quote(
            """<html with:page-layout="baz" with:foo="bar"
                with:fragment-layout="spam" content:is="fragment"
                this:is="page" with:content-type="text/plain"/>"""))

        self.assertEqual(doc.content_type,"text/plain")
        self.assert_(isinstance(doc.content_type,str))
        self.assert_(isinstance(doc.page,pwt.Replace))
        self.assert_(isinstance(doc.fragment,pwt.Replace))

        page = doc.params['page']
        fragment = doc.params['fragment']
        self.assert_(fragment.getParentComponent() is page)

        # We used 'layout' options, so page/frag attrs will be driven by those
        self.assert_(doc.fragment.getParentComponent() is doc)
        self.assert_(doc.page.getParentComponent() is doc)


    def testNonLayoutArgs(self):
        doc = self.parse("data:,"+quote(
            """<html with:foo="bar"
                this:is="page" content:is="fragment"/>"""))
        self.assert_(isinstance(doc.page,pwt.Element))
        self.assert_(isinstance(doc.fragment,pwt.Element))

        # We used non-layout options, so page/frag attrs will be related
        self.assert_(doc.fragment.getParentComponent() is doc.page)
        self.assert_(doc.page.getParentComponent() is doc)


    def testDefaultLayoutArgs(self):
        doc = self.parse("data:,"+quote("""<html/>"""))
        self.assert_(doc.fragment)
        self.assert_(not doc.page)





TestClasses = (
    MiscTests, ParserTests, BasicTest, NSTest, NSTest2, ListHeaderFooterTest
)

def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])



































