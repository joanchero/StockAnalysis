from peak.api import *
import sys, os, os.path, posixpath
URL = naming.URL    # XXX can't import an un-loaded lazy module from its parent


class GenericPathURL(URL.Base):

    protocols.advise(
        instancesProvide=[naming.IBaseURL]
    )

    nameAttr = 'path'
    supportedSchemes = 'http','https','ftp','file',

    class user(URL.Field):
        pass

    class passwd(URL.Field):
        pass

    class host(URL.Field):
        defaultValue = None
        syntax = URL.Conversion(
            URL.ExtractQuoted(URL.MatchString(pattern='[^/:]*')),
            defaultValue = None
        )

    class port(URL.IntField):
        pass

    class path(URL.NameField):
        referencedType = naming.CompositeName
        canBeEmpty = True

    class query(URL.Field):
        pass

    class fragment(URL.Field):
        pass


    # Make syntax usable w/subclasses that redefine individual fields

    syntax = binding.classAttr(
        binding.Make(
            lambda s: URL.Sequence(
                '//',
                ( (s.user, (':',s.passwd) ,'@'), s.host, (':',s.port)),
                '/', s.path, ('?',s.query), ('#',s.fragment)
            )
        )
    )

    def joinURL(self,relativeURL):
        from urlparse import urljoin
        return self.mdl_fromString(urljoin(str(self),relativeURL))


class OpenableURL(GenericPathURL):
    defaultFactory = 'peak.naming.factories.openable.URLStreamFactory'






















class FileURL(OpenableURL):

    supportedSchemes = 'file',
    defaultFactory = 'peak.naming.factories.openable.FileFactory'

    # Make syntax usable w/subclasses that redefine individual fields
    syntax = binding.classAttr(
        binding.Make(
            lambda s: URL.Sequence(
                URL.Alternatives(
                    URL.Sequence('//', s.host, s.path),
                    s.path,
                ), ('?', s.querySyntax), ('#', s.fragment),
            )
        )
    )

    querySyntax = GenericPathURL.query._syntax

    def getFilename(self):
        # We need to normalize ourself to match urllib's funky
        # conventions for file: conversion.  :(
        from urllib import url2pathname
        return url2pathname(str(self.path))


    def fromFilename(klass, aName):
        m = naming.URLMatch(aName)
        if m and (m.end()>2 or sys.platform<>'win32'):    # XXX ugh!
            return klass(m.group(1), aName[m.end():])
        else:
            from os.path import abspath
            from urllib import pathname2url
            return klass(None, pathname2url(abspath(aName)))

    fromFilename = classmethod(fromFilename)





class PkgFileURL(URL.Base):

    protocols.advise(
        classProvides=[naming.IObjectFactory],
        instancesProvide=[naming.IBaseURL],
    )

    nameAttr = 'path'
    supportedSchemes = 'pkgfile',
    defaultFactory = 'peak.naming.factories.openable.PkgFileURL'


    class module(URL.Field):
        pass

    class path(URL.NameField):
        referencedType = naming.CompositeName
        canBeEmpty = False

    syntax = URL.Sequence(module, '/', path)

    def joinURL(self,relativeURL):
        path = posixpath.normpath(
            posixpath.join(str(self.path[:-1]),relativeURL)
        )
        if path.startswith('/') or path.startswith('../'):
            raise exceptions.InvalidName(
                "Invalid relative URL for pkgfile: URL",
                    resolvedName=self, remainingName=relativeURL
            )
        return self.__class__(self.scheme, module=self.module,
            path=path
        )

    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        url, = refInfo.addresses
        return config.packageFile(url.module,str(url.path))

    getObjectInstance = classmethod(getObjectInstance)


class DataURL(URL.Base):

    supportedSchemes = 'data',

    defaultFactory = 'peak.naming.factories.openable.ConstantStream'

    class content_type(URL.Field):
        pass

    class parameters(URL.Collection):
        separator = ';'
        
    class data(URL.Field):
        unquote = "all"
    
    syntax = URL.Sequence(
        (content_type, (';', parameters)), ',', data
    )























class URLStreamFactory(object):

    """Stream factory for a 'urllib2.urlopen()'

    This is a pretty lame duck right now.  It's mainly here so we have a
    consistent interface across file-like URLs."""

    protocols.advise(
        classProvides=[naming.IObjectFactory],
        instancesProvide=[naming.IStreamFactory],
    )

    address = binding.Require("urllib2 URL or request", attrName='address')


    def open(self,mode,seek=False,writable=False,autocommit=False):

        if writable:
            raise TypeError("URL not writable", self.address)

        if mode<>'b':
            raise TypeError("URL requires binary read mode", self.address)

        if seek:
            raise TypeError("URL not seekable", self.address)

        from urllib2 import urlopen
        return urlopen(str(self.address))


    def create(self,mode,seek=False,readable=False,autocommit=False):
        raise TypeError("Can't create URL", self.address)

    def update(self,mode,seek=False,readable=False,append=False,autocommit=False):
        raise TypeError("Can't update URL", self.address)

    def delete(self, autocommit=False):
        raise TypeError("Can't delete URL", self.address)



    def exists(self):

        from urllib2 import urlopen, HTTPError

        try:
            urlopen(self.address).close()
        except (HTTPError,IOError):
            return False
        else:
            return True


    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        url, = refInfo.addresses
        self = klass()
        self.address = str(url)
        return self

    getObjectInstance = classmethod(getObjectInstance)






















class ConstantStream(object):
    """Stream factory for a text constant"""

    protocols.advise(
        classProvides=[naming.IObjectFactory],
        instancesProvide=[naming.IStreamFactory],
    )

    def __init__(self,text):
        from urllib import quote
        self.address = "data:,"+quote(text)
        self.text = text

    def open(self,mode,seek=False,writable=False,autocommit=False):

        if writable:
            raise TypeError("Constant data from 'data:' URL is not writable")

        from cStringIO import StringIO
        return StringIO(self.text)

    def exists(self):
        return True

    def create(self,mode,seek=False,readable=False,autocommit=False):
        raise TypeError("Can't create", self.address)

    def update(self,mode,seek=False,readable=False,append=False,autocommit=False):
        raise TypeError("Can't update", self.address)

    def delete(self, autocommit=False):
        raise TypeError("Can't delete", self.address)

    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        url, = refInfo.addresses
        text = url.data
        if 'base64' in url.parameters:
            text = text.decode('base64')
        return klass(text)
    getObjectInstance = classmethod(getObjectInstance)

class ImportLoaderFactory(ConstantStream):
    """Stream factory for data loaded by a PEP 302 import loader"""

    def __init__(self,loader,moduleName,path,fullpath):
        self.address = str(PkgFileURL("pkgfile","%s/%s" % (moduleName,path)))
        self.loader = loader
        self.path = fullpath
    
    def open(self,mode,seek=False,writable=False,autocommit=False):

        if writable:
            raise TypeError("Importer data not writable", self.address)

        from cStringIO import StringIO
        return StringIO(self.loader.get_data(self.path))

    def exists(self):
        try:
            self.loader.get_data(self.path)
            return True
        except (IOError,OSError,ImportError):
            return False
      


















class FileFactory(binding.Component):

    """Stream factory for a local file object"""

    protocols.advise(
        classProvides=[naming.IObjectFactory],
        instancesProvide=[naming.IStreamFactory],
    )

    filename = binding.Require("Filename to open/modify")
    address = binding.Make(lambda s: str(FileURL.fromFilename(s.filename)))

    def open(self,mode,seek=False,writable=False,autocommit=False):
        return self._open(mode, 'r'+(writable and '+' or ''), autocommit)

    def create(self,mode,seek=False,readable=False,autocommit=False):
        return self._open(mode, 'w'+(readable and '+' or ''), autocommit)

    def update(self,mode,seek=False,readable=False,append=False,autocommit=False):
        return self._open(mode, 'a'+(readable and '+' or ''), autocommit)

    def exists(self):
        return os.path.exists(self.filename)

    def _acRequired(self):
        raise NotImplementedError(
            "Files require autocommit for write operations"
        )

    def _open(self, mode, flags, ac):

        if mode not in ('t','b','U'):
            raise TypeError("Invalid open mode:", mode)

        if not ac and flags<>'r':
            self._acRequired()

        return open(self.filename, flags+mode)



    def delete(self,autocommit=False):

        if not autocommit:
            self._acRequired()

        os.unlink(self.filename)


    # XXX def move(self, other, overwrite=True, mkdirs=False, autocommit=False):


    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        url, = refInfo.addresses
        return klass(filename = url.getFilename())

    getObjectInstance = classmethod(getObjectInstance)

























class FileDescriptor(model.ExtendedEnum):

    stdin = model.enum(0)
    stdout = model.enum(1)
    stderr = model.enum(2)


class fdURL(URL.Base):

    """fd.file:fileno

    'fileno' can be an integer, or one of 'stdin', 'stdout', 'stderr'

    Example::

        fd.file:stdout
    """

    supportedSchemes = 'fd.file',

    defaultFactory = 'peak.naming.factories.openable.FDFactory'

    class fileno(naming.URL.Field):
        referencedType = FileDescriptor

    syntax = naming.URL.Sequence(fileno)















class FDFactory(FileFactory):

    """Stream factory for a local file object"""

    protocols.advise(
        classProvides=[naming.IObjectFactory],
        instancesProvide=[naming.IStreamFactory],
    )

    fd = binding.Require("File descriptor to open/modify")
    filename = binding.Require("Operation not possible for file descriptors")
    address = binding.Require("original fdURL")

    def _open(self, mode, flags, ac):

        if mode not in ('t','b','U'):
            raise TypeError("Invalid open mode:", mode)

        if not ac and flags<>'r':
            self._acRequired()

        return os.fdopen(self.fd, flags+mode)


    def getObjectInstance(klass, context, refInfo, name, attrs=None):
        url, = refInfo.addresses
        return klass(fd = url.fileno, address=str(url))

    getObjectInstance = classmethod(getObjectInstance)












