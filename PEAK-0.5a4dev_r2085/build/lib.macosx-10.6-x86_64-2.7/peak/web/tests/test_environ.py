from unittest import TestCase, makeSuite, TestSuite
from peak.api import *
from peak.tests import testRoot
from wsgiref.util import request_uri
from test_templates import TestApp

class TestTraversals(TestCase):

    default_url_base = 'http://127.0.0.1'
    script_name = '/x'

    def setUp(self):
        self.url_base = self.default_url_base + self.script_name
        self.ob1 = object()
        self.ob2 = object()
        self.ob3 = object()
        self.root = TestApp(testRoot())
        self.policy = web.TestPolicy(self.root)
        self.ctx = self.policy.newContext({'SCRIPT_NAME':self.script_name})

    def getCurrent(self):
        return self.ctx.current

    def setChild(self,name,ob):
        self.ctx = self.ctx.childContext(name,ob)
        self.failUnless(self.getCurrent() is ob)

    def setPeer(self,name,ob):
        self.ctx = self.ctx.peerContext(name,ob)
        self.failUnless(self.getCurrent() is ob)

    def setParent(self,ob):
        self.ctx = self.ctx.parentContext()
        self.failUnless(self.getCurrent() is ob)

    def checkURLs(self,url):
        self.assertEqual(self.ctx.absoluteURL,self.url_base+url)
        self.assertEqual(self.ctx.traversedURL,self.url_base+url)
        if request_uri(self.ctx.environ,False)==self.url_base:
            self.assertEqual(self.ctx.url,self.script_name[1:]+url)
            
    def setName(self,name,ob,url):
        self.ctx = self.ctx.traverseName(name)
        self.failUnless(self.getCurrent() is ob)
        self.checkURLs(url)

    def testGotoChild(self):
        self.setChild('test',self.ob1)
        self.checkURLs('/test')
        self.setChild('test2',self.ob2)
        self.checkURLs('/test/test2')
        self.setChild('test3',self.ob3)
        self.checkURLs('/test/test2/test3')

    def testGotoPeer(self):
        self.setPeer('test',self.ob1)
        self.checkURLs('')
        self.setChild('test2',self.ob2)
        self.checkURLs('/test2')
        ob3 = object()
        self.setPeer('test3',self.ob3)
        self.checkURLs('/test3')

    def testGotoParent(self):
        self.setParent(self.root)    # test initially-empty case
        self.setChild('test',self.ob1)
        self.setChild('test2',self.ob2)
        self.setChild('test3',self.ob3)
        self.checkURLs('/test/test2/test3')
        self.setParent(self.ob2)
        self.checkURLs('/test/test2')
        self.setParent(self.ob1)
        self.checkURLs('/test')
        self.setParent(self.root)    # test return-to-empty case
        self.checkURLs('')







    def testGotoName(self):
        from test_templates import TestApp
        app = TestApp(self.root,'test')
        self.setChild('test',app)
        self.setName('.',app,'/test')
        self.setName('',app,'/test')
        self.setName('..',self.root,'')
        self.setChild('test',app)
        self.setName('foo',app.foo,'/test/foo')


    def testGetStuff(self):
        self.failUnless(self.ctx.policy is self.policy)

    def diffCtx(self,ctx1,ctx2):
        return [a
            for a in 'name','current','environ','policy','user','skin'
                if getattr(ctx1,a) is not getattr(ctx2,a)
        ]

    def testClone(self):
        ctx = self.ctx.clone()
        self.assertEqual(self.diffCtx(ctx,self.ctx),[])
        ctx1 = ctx.childContext('test',self.ob1)
        ctx2 = ctx1.clone(user = "spam")
        self.assertEqual(self.diffCtx(ctx1,ctx2),['user'])
        ctx3 = ctx2.clone(skin = "foo")
        self.assertEqual(self.diffCtx(ctx2,ctx3),['skin'])
        self.assertRaises(TypeError,ctx3.clone,foo="bar")












    def testChangeRoot(self):
        self.setChild('test',self.ob1)
        self.setChild('test2',self.ob2)
        self.setChild('test3',self.ob3)
        self.checkURLs('/test/test2/test3')
        self.url_base += '/++skin++foo'
        self.ctx = self.ctx.clone(rootURL=self.url_base)
        self.checkURLs('/test/test2/test3')

    def getPath(self,path):
        return web.TraversalPath(path).traverse(self.ctx)

    def checkPath(self,path,ob):
        self.assertEqual(self.getPath(path).current,ob)

       
    def testContextAttrs(self):
        self.failUnless(self.getPath('/').current is self.ctx)
        self.assertRaises(
            (TypeError,AttributeError), lambda: self.getPath('/').traversedURL)
        for attr in """
            url previous environ policy skin rootURL
            traversedURL absoluteURL user default nothing
        """.strip().split():
            self.checkPath('/'+attr, getattr(self.ctx,attr))
        self.assert_(self.getPath('/default').current is NOT_GIVEN)
        self.assert_(self.getPath('/nothing').current is None)

    def testPolicyAttrs(self):
        for attr in "defaultMethod resourcePrefix app".strip().split():
            self.checkPath('/policy/'+attr, getattr(self.policy,attr))
        
    def testEnvironItems(self):
        for key in self.ctx.environ:
            self.checkPath('/environ/'+key, self.ctx.environ[key])






class TestContext(TestCase):

    def setUp(self):
        self.policy = web.TestPolicy(testRoot())
        self.ctx = self.policy.newContext({'SCRIPT_NAME':'/x'})
        self.root = self.ctx.current    # XXX

    def newCtx(self,env={},**kw):
        return self.policy.newContext(env,**kw)

    def checkShift(self,sn_in,pi_in,part,sn_out,pi_out):
        ctx = self.newCtx({'SCRIPT_NAME':sn_in,'PATH_INFO':pi_in})
        self.assertEqual(ctx.shift(),part)
        self.assertEqual(ctx.environ['PATH_INFO'],pi_out)
        self.assertEqual(ctx.environ['SCRIPT_NAME'],sn_out)
        return ctx

    def testNewContext(self):
        d = {}
        ctx = web.StartContext('',None,d,policy=self.policy)
        self.failUnless(ctx.environ is d)
        self.failUnless(web.ITraversalContext(ctx) is ctx)

    def testSingleShift(self):
        dm = self.policy.defaultMethod
        self.checkShift('','/', dm, '/'+dm, '')
        self.checkShift('','/x', 'x', '/x', '')
        self.checkShift('/','', None, '/', '')

        ctx = self.newCtx({})
        self.assertEqual(ctx.shift(),dm)
        self.assertEqual(ctx.environ['PATH_INFO'],'')
        self.assertEqual(ctx.environ['SCRIPT_NAME'],'/'+dm)


    def testDoubleShift(self):
        self.checkShift('/a','/x/y', 'x', '/a/x', '/y')
        self.checkShift('/a','/x/',  'x', '/a/x', '/')



    def testNormalizedShift(self):
        dm = self.policy.defaultMethod
        self.checkShift('/a/b', '/../y', '..', '/a', '/y')
        self.checkShift('', '/../y', '..', '', '/y')
        self.checkShift('/a/b', '//y', 'y', '/a/b/y', '')
        self.checkShift('/a/b', '//y/', 'y', '/a/b/y', '/')
        self.checkShift('/a/b', '/./y', 'y', '/a/b/y', '')
        self.checkShift('/a/b', '/./y/', 'y', '/a/b/y', '/')
        self.checkShift('/a/b', '///./..//y/.//', '..', '/a', '/y/')
        self.checkShift('/a/b', '///', dm, '/a/b/'+dm, '')
        self.checkShift('/a/b', '/.//', dm, '/a/b/'+dm, '')
        self.checkShift('/a/b', '/x//', 'x', '/a/b/x', '/')
        self.checkShift('/a/b', '/.', None, '/a/b', '')

    def assertEmptyNS(self,name):
        self.assertEqual(web.parseName(name), ('',name))

    def testSplitNS(self):
        self.assertEmptyNS('xyz')
        self.assertEmptyNS('++abcdef')
        self.assertEmptyNS('++abc+def')
        self.assertEmptyNS('++++def')
        self.assertEmptyNS('+++def+++')
        self.assertEmptyNS('++abc+foo++def')
        self.assertEmptyNS('++9abc++def')
        self.assertEmptyNS('++9abc++def++')

        self.assertEqual(web.parseName('@@xyz'), ('view','xyz'))
        self.assertEqual(web.parseName('++abc++def'), ('abc','def'))
        self.assertEqual(web.parseName('++abc9++def'), ('abc9','def'))











class TestNamespaces(TestCase):

    def setUp(self):
        from test_templates import TestApp
        self.app = TestApp(testRoot())
        self.policy = web.TestPolicy(self.app)
        self.foo_skin = web.Skin()
        foo_dapter = lambda *args: self
        bar_dapter = lambda *args: "baz"
        foo_handler = lambda ctx,o,ns,nm,qn,d: ctx.childContext(qn,self)
        bar_handler = lambda ctx,o,ns,nm,qn,d: ctx.childContext(qn,"baz")
        self.policy.registerProvider(
            web.NAMESPACE_NAMES+'.foo', config.Value(foo_dapter)
        )
        self.policy.registerProvider(
            web.NAMESPACE_NAMES+'.bar', config.Value(bar_dapter)
        )
        self.policy.registerProvider(
            'peak.web.skins.foo', config.Value(self.foo_skin)
        )
        self.app.registerView(int,'foo',foo_handler)
        self.app.registerView(str,'foo',bar_handler)



    def invokeHandler(self,ctx,handler,qname,check_context=True,fail=False):
        ns, nm = web.parseName(qname)
        if fail:
            self.assertRaises(web.NotFound,handler,ctx,ctx.current,ns,nm,qname)
            self.failUnless(
                handler(ctx,ctx.current,ns,nm,qname,NOT_FOUND) is NOT_FOUND
            )
        else:
            res = handler(ctx,ctx.current,ns,nm,qname)
            if check_context:
                self.failUnless(res.parentContext() is ctx)
                self.assertEqual(res.name, qname)
            return res



    def testRegisteredNS(self):
        ctx = self.policy.newContext(start=123)
        args = ctx, ctx.current, '', '', ''
        self.failUnless(self.policy.ns_handler('foo')(*args) is self)
        self.assertEqual(self.policy.ns_handler('bar')(*args), "baz")

    def testTraverseResource(self):
        RESOURCE_NS = self.policy.resourcePrefix
        ctx = self.policy.newContext(start=123)
        res = self.invokeHandler(ctx, web.traverseResource, RESOURCE_NS)
        self.failUnless(res.current is ctx.skin)
        self.invokeHandler(ctx,web.traverseResource,RESOURCE_NS+"xyz",fail=1)

    def testTraverseView(self):
        ctx = self.policy.newContext().childContext('x',123)
        for handler in web.traverseView, web.traverseDefault:
            for name in '@@foo', '++view++foo':
                res = self.invokeHandler(ctx, handler, name)
                self.failUnless(res.current is self)
            self.invokeHandler(ctx, handler, "@@"+NO_SUCH_NAME, fail=1)
            self.invokeHandler(ctx, handler, "++view++"+NO_SUCH_NAME, fail=1)

    def testTraverseSkin(self):
        ctx = self.policy.newContext(start=123)
        res = self.invokeHandler(ctx, web.traverseSkin, '++skin++foo', False)
        self.failUnless(res.skin is self.foo_skin)
        self.assertEqual(res.rootURL, ctx.rootURL+'/++skin++foo')
        self.invokeHandler(ctx, web.traverseSkin, "++skin++"+NO_SUCH_NAME,fail=1)













    def testTraverseAttr(self):
        ctx = self.policy.newContext(start=self.app)
        for handler in web.traverseAttr, web.traverseDefault:
            res = self.invokeHandler(ctx, handler, '++attr++foo')
            self.failUnless(res.current is self.app.foo)
            self.invokeHandler(ctx, handler, "++attr++"+NO_SUCH_NAME,fail=1)
            self.invokeHandler(ctx, handler, "++attr++__class__",fail=1)
            self.assertRaises(web.NotAllowed,
                self.invokeHandler, ctx, handler, "++attr++baz"
            )

    def testTraverseItem(self):
        ctx = self.policy.newContext(start={'foo':'bar'})
        for handler in web.traverseItem, web.traverseDefault:
            res = self.invokeHandler(ctx, handler, '++item++foo')
            self.failUnless(res.current=='bar')
            self.invokeHandler(ctx, handler, "++item++"+NO_SUCH_NAME, fail=1)
            #self.assertRaises(web.NotAllowed,
            #    self.invokeHandler, ctx, handler, "++item++...?"
            #)

    def testTraverseNames(self):
        ctx = self.policy.newContext().childContext('x',123)
        self.failUnless(ctx.traverseName('++foo++bar') is self)
        self.assertEqual(ctx.traverseName('++bar++baz'), 'baz')
        self.failUnless(ctx.traverseName('@@foo').current is self)
        self.failUnless(ctx.traverseName('++view++foo').current is self)
        self.failUnless(
            ctx.traverseName('++skin++foo').skin is self.foo_skin
        )
        for pfx in '@@','++view++','++skin++':
            self.assertRaises(web.NotFound, ctx.traverseName, pfx+NO_SUCH_NAME)
        ctx = self.policy.newContext(start=self.app)
        foo = self.app.foo
        self.failUnless(ctx.traverseName('++attr++foo').current is foo)
        ctx = self.policy.newContext(start={'foo':'bar'})
        self.assertEqual(ctx.traverseName('++item++foo').current, 'bar')




    def testTraverseLocationId(self):
        ctx  = self.policy.newContext(start=self.app)
        id1  = '++id++spammity'
        id2  = '++id++foo.bar'
        key1 = web.LOCATION_ID('spammity')
        key2 = web.LOCATION_ID('foo.bar')

        # check default/error behavior
        self.invokeHandler(ctx,web.traverseLocationId,id1,fail=1)
        self.assertRaises(web.NotFound, ctx.traverseName, id1)

        # check direct find, no path
        item = binding.Configurable(testRoot())
        ctx1 = ctx.childContext('test',item)
        item.registerProvider(key1,config.Value(web.TraversalPath('.')))
        ctx2 = ctx1.traverseName(id1)
        self.failUnless(ctx2 is ctx1)

        # check indirect find, no path
        ctx3 = ctx1.childContext('test2',binding.Component())
        self.failUnless(ctx3.traverseName(id1) is ctx2)

        # check direct find, with path
        item.registerProvider(key2,config.Value(web.TraversalPath('../foo')))
        self.failUnless(ctx1.traverseName(id2).current is self.app.foo)

        # check indirect find, with path
        self.failUnless(ctx3.traverseName(id2).current is self.app.foo)

        # check object w/no _getConfigData
        ctx4 = ctx1.childContext('test2',None)
        self.failUnless(ctx4.traverseName(id1) is ctx2)
        self.failUnless(ctx4.traverseName(id2).current is self.app.foo)








base_url = "http://a/b/c/d"

relative_urls = [ line.strip().split() for line in """
      g:h         g:h
      d           http://a/b/c/d
      g           http://a/b/c/g
      g/          http://a/b/c/g/
      ../../g     http://a/g
      http://g    http://g
      d?y         http://a/b/c/d?y
      g?y         http://a/b/c/g?y
      g?y/./x     http://a/b/c/g?y/./x
      ./          http://a/b/c/
      ../         http://a/b/
      ../g        http://a/b/g
      ../../      http://a/
      g/h         http://a/b/c/g/h
""".strip().split('\n')]

class RelativeURLTests(TestCase):
    def testRelativeURLs(self):
        for relurl,absurl in relative_urls:
            self.assertEqual(web.relativeURL(base_url,absurl),relurl)

NO_SUCH_NAME = '__nonexistent__$$@'

TestClasses = (
    TestTraversals, TestContext, TestNamespaces, RelativeURLTests
)

def test_suite():
    return TestSuite([makeSuite(t,'test') for t in TestClasses])









