"""Simple Objects from XML - quick-and-dirty XML parsing without a DOM

    This module implements most of the overhead needed for turning SAX
    events into a hierarchy of objects.  E.g., stack handling,
    delegation to node classes, etc.

    If all you need is to read an XML file and turn it into objects, you
    came to the right place.  If you need an actual model of the XML file
    that you can manipulate, with absolute fidelity to the original, you
    might be better off with a DOM, since this doesn't retain processing
    instructions or comments.

    SOX is faster than 'minidom' or any other DOM that I know of.  On the
    other hand, SOX is slower than PyRXP, but SOX handles Unicode correctly.

    To use this module, you will need a "document" object that implements
    either 'ISOXNode' or 'ISOXNode_NS', depending on whether you want
    namespace support.  The interfaces are very similar, except that
    the 'NS' version has some enhancements/simplifications that can't be
    added to the non-namespace version for backward-compatibility reasons.

    Once you have your document object, just call
    'SOX.load(filenameOrStream,documentObject,namespaces=flag)' to get back
    the result of your document object's '_finish()' method after it has
    absorbed all of the XML data supplied.

    If you need a simple document or node class, 'Document', 'Document_NS',
    'Node', and 'Node_NS' are available for subclassing or idea-stealing.
"""


from xml.sax.saxutils import XMLGenerator, quoteattr, escape
from protocols import Interface, advise, Adapter

__all__ = [
    'load', 'ISOXNode', 'ISOXNode_NS', 'IXMLBuilder', 'ExpatBuilder',
    'Node', 'Node_NS', 'Document', 'Document_NS', 'IndentedXML',
]



class ISOXNode(Interface):

    """Object mapping from an XML element

        Objects implementing ISOXNode are used to construct object structures
        from XML elements.  Each node gets to control how its subnodes are
        created, and what will be passed back to its parent node once its
        element subtree is complete.  In the simplest possible case, one can
        create a simple DOM-like tree of nodes which closely resemble the
        original XML.  Or, one can create a tree of objects with only minor
        structural similarities, or even use nodes just to do "side-effect"
        processing guided by the XML structures, like an interpretive parser.
    """

    def _newNode(name,attributeMap):
        """Create new child node from 'name' and 'attributeMap'

           Child node must implement the 'ISOXNode' interface."""

    def _acquireFrom(parentNode):
        """Parent-child relationship hook

           Called on newly created nodes to give them a chance to acquire
           context information from their parent node"""

    def _addText(text):
        """Add text string 'text' to node"""

    def _addNode(name,subObj):
        """Add finished sub-node 'subObj' to node"""

    def _finish():
        """Return an object to be used in place of this node in call to the
            parent's '_addNode()' method.  Returning 'None' will result in
            nothing being added to the parent."""






class ISOXNode_NS(Interface):

    def _newNode(name, attributeMap):

        """Create new child node from 'name' and 'attributeMap'

           Child node must implement the 'ISOX2Node' interface."""

    def _setNS(ns2uri):
        """Set namespace declaration map"""

    def _addText(text):
        """Add text string 'text' to node"""


    def _addNode(name,subObj):
        """Add finished sub-node 'subObj' to node"""


    def _finish():
        """Return an object to be used in place of this node in call to the
            parent's '_addNode()' method.  Returning 'None' will result in
            nothing being added to the parent."""


















class IXMLBuilder(Interface):

    def _xml_addChild(data):
        """Add 'data' to element's children"""

    def _xml_finish():
        """Return finished value to be passed to parent's 'addChild()'"""

    def _xml_newTag(name,attrs,newPrefixes,parser):
        """Create and return a subnode for a tag"""

    def _xml_addText(xml):
        """Return a new subnode for text"""

    def _xml_addLiteral(xml):
        """Return a new subnode for literals such as comments, PIs, etc."""

























class SoxNodeAsXMLBuilder(Adapter):

    advise(
        instancesProvide=[IXMLBuilder],
        asAdapterForProtocols=[ISOXNode]
    )

    def _xml_addText(self,text):
        self.subject._addText(text)

    def _xml_addLiteral(self,text):
        pass

    def _xml_finish(self):
        return self.subject._finish()

    def _xml_addChild(self,node):
        self.subject._addNode(self.lastName,node)    # XXX

    def _xml_newTag(self,name,attrs,newPrefixes,parser):
        node = self.subject._newNode(name,dict(attrs))
        node._acquireFrom(self.subject)
        self.lastName = name
        return node

















class NSNodeAsXMLBuilder(Adapter):

    advise(
        instancesProvide=[IXMLBuilder],
        asAdapterForProtocols=[ISOXNode_NS]
    )

    def _xml_addText(self,text):
        self.subject._addText(text)

    def _xml_addLiteral(self,text):
        pass

    def _xml_finish(self):
        return self.subject._finish()

    def _xml_addChild(self,node):
        self.subject._addNode(self.lastName,node)    # XXX

    def _xml_newTag(self,name,attrs,newPrefixes,parser):
        node = self.subject._newNode(name,dict(attrs))
        if newPrefixes:
            ns2uri = dict(
                [(prefix,stack[-1]) for prefix,stack in parser.nsInfo.items()]
            )
            node._setNS(ns2uri)
        self.lastName = name
        return node













class Node:

    """Simple, DOM-like ISOXNode implementation"""

    advise( instancesProvide = [ISOXNode] )

    def __init__(self,name='',atts={},**kw):
        self._name = name
        self._subNodes = []
        self._allNodes = []
        self.__dict__.update(atts)
        self.__dict__.update(kw)

    def _addNode(self,name,node):
        self._allNodes.append(node)
        self._subNodes.append(node)
        d=self.__dict__
        if not d.has_key(name): d[name]=[]
        d[name].append(node)

    def _newNode(self,name,atts):
        return self.__class__(name,atts)

    def _addText(self,text):
        self._allNodes.append(text)

    def _get(self,name):
        return self.__dict__.get(name,[])

    def _findFirst(self,name):
        d=self._get(name)
        if d: return d
        for n in self._subNodes:
            if hasattr(n,'_findFirst'):
                d = n._findFirst(name)
                if d: return d

    def _finish(self):
        return self


    _acquiredAttrs = ()

    def _acquireFrom(self,parentNode):
        d=self.__dict__
        have=d.has_key
        for k in self._acquiredAttrs:
            if not have(k): d[k]=getattr(parentNode,k)


class Document(Node):

    def _finish(self):
        self.documentElement = self._subNodes[0]
        return self

    def _newNode(self,name,atts):
        return Node(name,atts)


class Node_NS(Node):

    advise( instancesProvide = [ISOXNode_NS] )
    ns2uri = {}

    def _newNode(self,name,atts):
        node = self.__class__(
            name, atts, ns2uri=self.ns2uri,
        )
        return node

    def _setNS(self, ns2uri):
        self.ns2uri = ns2uri









class Document_NS(Node_NS):

    _finish = Document._finish.im_func

    def _newNode(self,name,atts):
        return Node_NS(name, atts)

def load(filename_or_stream, documentObject=None, namespaces=False):

    """Build a tree from a filename/stream, rooted in a document object"""

    if namespaces:

        if documentObject is None:
            documentObject = Document_NS()

    else:
        if documentObject is None:
            documentObject = Document()


    if isinstance(filename_or_stream,str):
        filename_or_stream = open(filename_or_stream,'rt')

    elif hasattr(filename_or_stream,'getByteStream'):
        filename_or_stream = filename_or_stream.getByteStream()

    return ExpatBuilder().parseFile(filename_or_stream,documentObject)




















class IndentedXML(XMLGenerator):

    """SAX handler that writes its output to an IndentedStream"""

    def __init__(self, out=None, encoding="iso-8859-1"):
        if out is None:
            from IndentedStream import IndentedStream
            out = IndentedStream()
        XMLGenerator.__init__(self,out,encoding)

    def startElement(self,name,attrs):
        XMLGenerator.startElement(self,name,attrs)
        self._out.push(1)

    def startElementNS(self,name,qname,attrs):
        XMLGenerator.startElementNS(self,name,qname,attrs)
        self._out.push(1)

    def characters(self,content):
        self._out.push()
        self._out.setMargin(absolute=0)
        XMLGenerator.characters(self,content)
        self._out.pop()

    def endElement(self,name):
        self._out.pop()
        XMLGenerator.endElement(self,name)

    def endElementNS(self,name,qname):
        self._out.pop()
        XMLGenerator.endElementNS(self,name,qname)










class INegotiationData(Interface):
    """
    All of the negotiator's behavior is controlled by 'data' dictionaries that
    may contain the following functions:

    * 'start(parser,data)' -- called to create the current element

    * 'finish(parser,data)' -- a function that's called when the current
      element is finished

    * 'child(result)' -- gets passed the return value from each
      child element's 'finish' function, if that child had a 'finish'
      function.

    * 'text(text)' -- a function that's passed any character data within
      the current element

    * 'literal(text)' -- a function that's passed any literal
      (non-character) data within the current element, such as comments,
      processing instructions, etc.

    Negotiation data can be changed at any time by either the negotiator
    functions, or by any of the above functions.
    """

class INegotiatorLookup(Interface):
    def __call__(nsURI, name):
        """Return a negotiator function for the specified element or attribute
        """

class IElementNegotiator(Interface):
    def __call__(parser, data):
        """Alter 'data' as needed to ensure element is processed correctly"""

class IAttributeNegotiator(Interface):
    def __call__(parser, data, name, value):
        """Alter 'data' as needed to ensure element is processed correctly

        'name' and 'value' are the name and value of the applicable attribute.
        """

# Helper routines for negotiated schemas

def invalidElement(parser,data):
    """Use this as an element negotiator for unrecognized elements"""
    parser.err("Unrecognized element "+`data['name']`)

def invalidAttribute(parser,data,name,value):
    """Use this as an element negotiator for unrecognized attributes"""
    parser.err("Unrecognized attribute "+`name`)

def validatedAttributes(parser,data,required=(),optional=()):
    """Filter an element's attributes, w/errors for invalid/missing attributes

    Return a dictionary of unprefixed attributes (i.e. no attributes with ':'
    in them).  If any attributes in 'required' are missing, or if there are
    any attributes present that aren't listed in 'required' or 'optional', a
    SyntaxError is generated.
    """
    attrs = dict([kv for kv in data['attributes'] if ':' not in kv[0]])
    for attr in required:
        if attr not in attrs:
            parser.err("Missing %r attribute" % attr)
    for attr in attrs:
        if attr not in required and attr not in optional:
            parser.err("Unrecognized attribute "+`attr`)
    return attrs















class NegotiatingParser:

    """XML processor that lets elements and attributes "negotiate" w/each other

    Basic usage::

        neg = Negotiator()
        neg.setLookup(elem_lookup_func, attr_lookup_func)
        neg.parseStream(file,root)  # or neg.parseString(text,root)

    """

    _parser = _url = None

    def __init__(self):
        self.element_map = {}
        self.attribute_map = {}
        self.ns_info = {}
        self.stack = [{}]
        self.lookup_element = self.lookup_attribute = lambda ns,name=None:None


    def addNamespace(self,prefix,ns_uri):
        self.ns_info.setdefault(prefix,[]).append(ns_uri)
        self.stack[-1].setdefault('prefixes',[]).append(prefix)
        # We have new XML namespaces, so our caches are invalid until
        # we're done with this element: reset caches for now
        self.resetCaches()


    def splitName(self,name):
        if ':' in name:
            ns,nm = name.split(':',1)
        else:
            ns,nm = '',name
        if self.ns_info.get(ns):
            return self.ns_info[ns][-1], nm
        else:
            return None, name


    def startElement(self,name,attrs):
        if self.stack[-1].get('empty'): self.err("Child elements not allowed")
        a = []; append = a.append; negattrs=[]
        attrs.reverse(); pop = attrs.pop
        data = {'name':name, 'attributes':a, 'previous':self.stack[-1]}
        self.stack.append(data)

        while attrs:
            k=pop(); v=pop()
            append((k,v))
            if k=='xmlns':
                self.addNamespace('',v)
            elif ':' in k:
                if k.startswith('xmlns:'):
                    self.addNamespace(k[6:],v)
                else:
                    negattrs.append((k,v))

        try:
            f = self.element_map[name]
        except KeyError:
            ns,nm = self.splitName(name)
            f = self.element_map[name] = self.lookup_element(ns,nm)
        if f:
            f(self,data)

        # do attrs negotiation
        for k,v in negattrs:
            try:
                f = self.attribute_map[k]
            except KeyError:
                ns,nm = self.splitName(k)
                f = self.attribute_map[k] = self.lookup_attribute(ns,nm)
            if f:
                f(self,data,k,v)

        # execute start function
        start = data.get('start')
        if start:
            start(self,data)

    def endElement(self,name=None):

        data = self.stack.pop()
        assert name==data['name'] or name is None

        finish = data.get('finish')
        if finish:
            result = finish(self,data)
            child = self.stack[-1].get('child')
            if child:
                child(result)
        else:
            result = None

        if 'prefixes' in data:
            for prefix in data['prefixes']:
                self.ns_info[prefix].pop()

        if 'caches' in data:
            self.attribute_map, self.element_map = data['caches']
            if 'lookups' in data:
                self.lookup_element, self.lookup_attribute = data['lookups']
        return result   # for tests


    def resetCaches(self):
        data = self.stack[-1]
        if 'caches' not in data:
            # only save once per stack level
            data['caches'] = self.attribute_map, self.element_map

        self.attribute_map, self.element_map = {}, {}









    def err(self,msg,kind=SyntaxError):
        """Generate an error with current parse location"""
        exc = kind()
        exc.msg = msg
        exc.filename = self._url
        if self._parser:
            exc.text = self._parser.GetInputContext()
            exc.lineno = self._parser.CurrentLineNumber
            exc.offset = self._parser.CurrentColumnNumber
        else:
            exc.lineno = exc.offset = exc.text = None
        exc.args = msg, (exc.filename,exc.lineno,exc.offset,exc.text)
        raise exc


    def setLookups(self,element=None,attribute=None):

        self.resetCaches()
        data = self.stack[-1]

        if 'lookups' not in data:
            # only save once per stack level
            data['lookups'] = (
                self.lookup_element, self.lookup_attribute,
            )

        if element is not None:
            self.lookup_element = element
        if attribute is not None:
            self.lookup_attribute = attribute











    def text(self,text):
        f = self.stack[-1].get('text')
        if f:
            f(text)

    def literal(self,text):
        f = self.stack[-1].get('literal')
        if f:
            f(text)

    def comment(self,text):
        f = self.stack[-1].get('literal')   # comment is literal w/<!--/-->
        if f:
            f(u'<!--%s-->' % text)


    def makeParser(self):
        from pyexpat import ParserCreate
        p = ParserCreate()
        p.ordered_attributes = True
        p.returns_unicode = True
        p.specified_attributes = True
        p.StartElementHandler = self.startElement
        p.EndElementHandler = self.endElement
        p.CommentHandler = self.comment
        p.DefaultHandler = self.literal
        p.CharacterDataHandler = self.text
        return p













    def _beforeParsing(self,root=None,url=None):
        root = root or {}
        self.stack.append(root)
        p = self.makeParser()
        self._parser = p; self._url = url
        start = root.get('start')
        if start:
            start(self,root)
        return p

    def _afterParsing(self):
        data = self.stack.pop()
        finish = data.get('finish')
        try:
            if finish:
                return finish(self,data)
        finally:
            del self._parser, self._url

    def parseString(self,text,root=None,url=None):
        self._beforeParsing(root,url).Parse(text,True)
        return self._afterParsing()

    def parseStream(self,stream,root=None,url=None):
        self._beforeParsing(root,url).ParseFile(stream)
        return self._afterParsing()















class ExpatBuilder:

    """Parser that assembles a document"""

    def __init__(self):
        self.parser = self.makeParser()
        self.stack   = []   # "object being assembled" stack
        self.nsStack = []
        self.nsInfo  = {}   # URI stack for each NS prefix

    def makeParser(self):
        from pyexpat import ParserCreate
        p = ParserCreate()
        p.ordered_attributes = True
        p.returns_unicode = True
        p.specified_attributes = True
        p.StartElementHandler = self.startElement
        p.EndElementHandler = self.endElement
        p.CommentHandler = self.comment
        p.DefaultHandler = self.buildLiteral
        # We don't use:
        # .StartDoctypeDeclHandler
        # .StartNamespaceDeclHandler
        # .EndNamespaceDeclHandler
        # .XmlDeclHandler(version, encoding, standalone)
        # .ElementDeclHandler(name, model)
        # .AttlistDeclHandler(elname, attname, type, default, required)
        # .EndDoctypeDeclHandler()
        # .ProcessingInstructionHandler(target, data)
        # .UnparsedEntityDeclHandler(entityN,base,systemId,publicId,notationN)
        # .EntityDeclHandler(
        #      entityName, is_parameter_entity, value, base,
        #      systemId, publicId, notationName)
        # .NotationDeclHandler(notationName, base, systemId, publicId)
        # .StartCdataSectionHandler()
        # .EndCdataSectionHandler()
        # .NotStandaloneHandler()
        return p



    def parseFile(self, stream, rootNode):
        self.__init__()
        self.stack.append(IXMLBuilder(rootNode))
        self.parser.CharacterDataHandler = self.stack[-1]._xml_addText
        self.parser.ParseFile(stream)
        return self.stack[-1]._xml_finish()


    def comment(self,data):
        self.buildLiteral(u'<!--%s-->' % data)

    def buildLiteral(self,xml):
        self.stack[-1]._xml_addLiteral(xml)




























    def startElement(self, name, attrs):

        prefixes = []; a = []
        pop = attrs.pop
        append = a.append

        while attrs:
            k = pop(0); v=pop(0)
            append((k,v))

            if not k.startswith('xmlns'):
                continue

            rest = k[5:]
            if not rest:
                ns = ''
            elif rest.startswith(':'):
                ns = rest[1:]
            else:
                continue

            self.nsInfo.setdefault(ns,[]).append(v)
            prefixes.append(ns)

        self.nsStack.append(prefixes)
        element = self.stack[-1]._xml_newTag(name, a, prefixes, self)
        self.stack.append(IXMLBuilder(element))
        self.parser.CharacterDataHandler = self.stack[-1]._xml_addText

    def endElement(self, name):
        last = self.stack.pop()
        self.parser.CharacterDataHandler = self.stack[-1]._xml_addText
        self.stack[-1]._xml_addChild(last._xml_finish())
        for prefix in self.nsStack.pop():
            self.nsInfo[prefix].pop()






