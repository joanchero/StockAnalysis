from __future__ import generators
from peak.api import *
from interfaces import *
from peak.util.Struct import makeStructType
from peak.util.imports import importObject
from connections import ManagedConnection, AbstractCursor, RowBase
from new import instancemethod

__all__ = [
    'SQLCursor', 'GenericSQL_URL', 'SQLConnection', 'SybaseConnection',
    'GadflyURL', 'GadflyConnection'
]


def sqlsafestr(s):
    return s.replace("'", "''")

def _nothing():
    pass

def NullConverter(descr,value):
    return value



















class SQLCursor(AbstractCursor):

    """Iterable cursor bridge/proxy"""

    conn = binding.Obtain('..')
    multiOK = False
    defaultFormat = "sql"

    _cursor = binding.Make(lambda self: self._conn.cursor())


    def close(self):

        if self._hasBinding('_cursor'):
            self._cursor.close()
            del self._cursor

        super(SQLCursor,self).close()


    def __setattr__(self,attr,val):

        if hasattr(self.__class__,attr):
            super(SQLCursor,self).__setattr__(attr,val)

        elif self._hasBinding(attr):
            self._setBinding(attr,val)

        else:
            setattr(self._cursor,attr,val)


    def __getattr__(self,attr):
        if not attr.startswith('_'):
            return getattr(self._cursor,attr)
        raise AttributeError,attr





    def nextset(self):
        try:
            return getattr(self._cursor, 'nextset', _nothing)()
        except self.conn.NotSupportedError:
            pass


    outsideTxn = False

    logger = binding.Obtain('logger:sql')

    __path = binding.Make(lambda self: binding.getComponentPath(self))

    def execute(self, *args):

        self.conn.setTxnState(self.outsideTxn)

        try:

            # XXX need some sort of flags for timing/logging here
            # XXX perhaps best handled as cursor subclass(es) set on
            # XXX the SQLConnection?

            return self._cursor.execute(*args)

        except self.conn.Exceptions:

            __traceback_info__ = args

            self.logger.exception(
                "%s: error executing SQL query: %s\n"
                "Traceback:",
                self.__path, args
            )

            self.conn.closeASAP()    # close connection after error
            raise




    def __iter__(self):
        if not self._cursor.description:
            return

        fetch = self._cursor.fetchmany
        rows = fetch()

        if rows:
            descr = self._cursor.description

            rowStruct = makeStructType('rowStruct',
                [d[0] for d in descr], RowBase,
                __module__ = __name__,
            )

            # mkTuple is a curried constructor for our new 'rowStruct' type
            mkTuple = instancemethod(tuple.__new__,rowStruct,None)

            # Now get a row conversion function for our description, using
            # our rowStruct constructor as a postprocessor
            converter = self.conn.getRowConverter(descr,mkTuple)

        while rows:

            for row in rows:
                yield converter(row)

            rows = fetch()


        if not self.multiOK and self.nextset():
            raise exceptions.TooManyResults









class SQLConnection(ManagedConnection):

    protocols.advise(
        instancesProvide=[ISQLConnection]
    )

    def commitTransaction(self, txnService):
        self.connection.commit()

    def abortTransaction(self, txnService):
        self.closeCursors()
        self.connection.rollback()

    cursorClass = SQLCursor

    DRIVER = binding.Require("DBAPI module name")  # Replace in subclasses

    API = binding.Make(lambda self: importObject(self.DRIVER))

    Error               = \
    Warning             = \
    NotSupportedError   = \
    Date                = \
    Time                = \
    Binary              = \
    Timestamp           = \
    DateFromTicks       = \
    TimeFromTicks       = \
    TimestampFromTicks  = binding.Delegate("API")
    Exceptions          = binding.Obtain(["Error", "Warning"])

    supportedTypes      = 'STRING','BINARY','NUMBER','DATETIME','ROWID'

    TYPES_NS = binding.Make(
        lambda self: config.Namespace('%s.sql_types' % self.DRIVER)
    )

    appConfig = binding.Make(
        lambda self: config.Namespace('%s.appConfig' % self.DRIVER)
    )

    twoPhaseProp = binding.Make(
        lambda self: PropertyName(self.DRIVER+'.twoPhaseCommit')
    )

    serialProp = binding.Make(
        lambda self: PropertyName(self.DRIVER+'.serializable')
    )

    twoPhase = binding.Obtain(naming.Indirect('twoPhaseProp'),default=False)

    serializable = binding.Obtain(naming.Indirect('serialProp'),default=False)

    log = binding.Obtain('logger:sql')

    def voteForCommit(self, txnService):
        super(SQLConnection,self).voteForCommit(txnService)
        if self.twoPhase:
            self._prepare()


    def typeMap(self):
        tm = {}
        ps = self.TYPES_NS
        api = self.API

        for k in self.supportedTypes:
            tm[getattr(api,k)] = importObject(ps.get(k,NullConverter))

        return tm

    typeMap = binding.Make(typeMap)


    def _prepare(self):
        raise NotImplementedError("Two-phase commit not implemented", self)






    def getRowConverter(self,description,post=None):
        """See ISQLConnection.getRowConverter()"""

        typeMap = self.typeMap
        converters = [
            instancemethod(
                typeMap.get(d[1],NullConverter), d, None
            ) for d in description
        ]

        for conv in converters:
            if conv.im_func is not NullConverter:
                # At least one conversion, so we must create a row converter
                if post is None:
                    return lambda row: [
                        conv(col) for (col,conv) in zip(row,converters)
                    ]
                else:
                    return lambda row: post(
                        [conv(col) for (col,conv) in zip(row,converters)]
                    )
        else:
            return post     # No conversions other than postprocessor

    dbTxnStarted = True
    txnAttrs = ManagedConnection.txnAttrs + ('dbTxnStarted',)

    def setTxnState(self,outsideTxn):
        self.joinedTxn          # ALWAYS join the PEAK transaction
        if outsideTxn:
            if self.dbTxnStarted:
                raise exceptions.TransactionInProgress(
                    """Database connection already has an active transaction"""
                )
        elif outsideTxn is not None:
            if not self.dbTxnStarted:
                self.dbTxnStarted = self._startDBTxn()

    def _startDBTxn(self):
        raise NotImplementedError("DB doesn't support explicit transactions")

class MockSQLConnection(SQLConnection):

    DRIVER = "peak.util.mockdb"

    def _open(self):
        return self.API.connect()

    expect = alsoExpect = provide = binding.Delegate('connection')

    def getRowConverter(self,description,post=None):
        return post     # provide() should be given pre-converted values


class ValueBasedTypeConn(SQLConnection):

    def typeMap(self):

        tm = {}
        ps = self.TYPES_NS
        api = self.API

        for k in self.supportedTypes:

            c = importObject(ps.get(k,NullConverter))

            for v in getattr(api,k).values:
                try:
                    v+''
                except:
                    tm[v] = c
                else:
                    # We support either '.int4' or '.INTEGER' style properties
                    tm[v] = importObject(
                        ps.get(PropertyName.fromString(v),c)
                    )

        return tm

    typeMap = binding.Make(typeMap)


class SybaseConnection(ValueBasedTypeConn):

    protocols.advise(
        instancesProvide=[ISQLObjectLister, ISQLDDLExtractor]
    )
    DRIVER    = "Sybase"
    hostname  = binding.Obtain(PropertyName('Sybase.client.hostname'), default=None, noCache=True)
    appname   = binding.Obtain(PropertyName('Sybase.client.appname'),  default=None, noCache=True)
    textlimit = binding.Obtain(PropertyName('Sybase.client.textlimit'),default=None, noCache=True)
    textsize  = binding.Obtain(PropertyName('Sybase.client.textsize'), default=None, noCache=True)

    otmap = {
        'systable'  : 'S',
        'fkey'      : 'RI',
        'function'  : 'F',
        'defaults'  : 'D',
        'proc'      : 'P',
        'table'     : 'U',
        'view'      : 'V',
        'trigger'   : 'TR',
        'rule'      : 'R',
    }

    def _open(self):
        a = self.address
        db = self.API.connect(
            a.server, a.user, a.passwd, a.db, auto_commit=1, delay_connect=1
        )
        if self.hostname is not None:
            db.set_property(self.API.CS_HOSTNAME, self.hostname)
        if self.appname is not None:
            db.set_property(self.API.CS_APPNAME, str(self.appname))
        if self.textlimit is not None:
            db.set_property(self.API.CS_TEXTLIMIT, int(self.textlimit))

        db.connect()
        if self.textsize is not None:
            db.execute('set textsize %d' % int(self.textsize))
        return db


    dbTxnStarted = False    # Sybase doesn't auto-chain transactions...

    def _startDBTxn(self):
        self.connection.begin()
        return True

    def txnTime(self):
        # Retrieve the server's idea of the current time
        r = ~ self('SELECT getdate()')
        return r[0]

    txnTime = binding.Make(txnTime)


    def listObjects(self, full=False, obtypes=NOT_GIVEN):
        addsel = addwhere = ''

        if full:
            addsel = ', id, uid, type, userstat, sysstat, sysstat2, indexdel, schemacnt, expdate, deltrig, instrig, updtrig, seltrig, ckfirst, cache, objspare '

        if obtypes is not NOT_GIVEN:
            addwhere = ' where type in (%s)' % \
                ', '.join(["'%s'" % self.otmap.get(s, '') for s in obtypes])

        typecase = ' '.join([
            ("when type = '%s' THEN '%s'" % (v, k))
            for (k, v) in self.otmap.items()
        ])

        return self('''select name as obname,
            obtype = rtrim(CASE %s ELSE type END), crdate%s
            from sysobjects%s ORDER BY name''' % (typecase, addsel, addwhere), outsideTxn=None)










    def _helptext(self, name, l):
        '''Append sp_helptext lines to list l'''

        rs = self("sp_helptext '%s'" % name, multiOK=True)
        more = True
        while more:
            for r in rs:
                if r.has_key('text'):   # Sybase
                    l.append(r['text'].replace('\r\n', '\n'))
                elif r.has_key('Text'): # MS-SQL
                    l.append(r['Text'].replace('\r\n', '\n'))
            more = rs.nextset()


    def _get_permissions(self, name, l, sybase):
        '''Append permissions rules to list l'''

        if sybase:
            sybkludge = ' + 204'
        else:
            sybkludge = ''

        rs = self("""
            SELECT upper(k.name) as k, upper(a.name) as a,
                user_name(p.uid) as g
            FROM sysprotects p
            JOIN master.dbo.spt_values a
            ON p.action = a.number AND a.type = 'T'
            JOIN master.dbo.spt_values k
            ON p.protecttype%s = k.number AND k.type = 'T'
            WHERE p.id = OBJECT_ID('%s')
            ORDER BY k.name, a.name, user_name(p.uid)
            """ % (sybkludge, name))

        for r in rs:
            l.append('%s %s ON %s TO %s\ngo\n' % (
                r.k, r.a, name, r.g)
            )



    def getDDLForObject(self, name):
        name = sqlsafestr(name)

        r = ~ self("""select * from sysobjects where id = OBJECT_ID('%s')""" % name)
        kind = r.type.strip()

        sybase = r.has_key('sysstat2')

        if kind == 'P' and sybase:
            mode = (r.sysstat2 >> 4 & 0x3)
            mode = {0 : 'unchained', 1 : 'chained', 2 : 'anymode'}.get(mode)
        else:
            mode = None

        if kind in ('P', 'TR', 'V'):
            kind, otype = {
                'P' : ('PROCEDURE', 'proc'),
                'TR': ('TRIGGER',   'trigger'),
                'V' : ('VIEW',      'view')
            }[kind]

            d = []

            if not sybase:
                qi = r.status & 0x40000000 and 'ON' or 'OFF'
                an = r.status & 0x20000000 and 'ON' or 'OFF'

                d.append('SET QUOTED_IDENTIFIER %s\ngo\n' % qi)
                d.append('SET ANSI_NULLS %s\ngo\n' % an)

            d.extend([
                "IF OBJECT_ID('%s') IS NOT NULL\nBEGIN\n" % name,
                "    DROP %s %s\n" % (kind, name),
                "    IF OBJECT_ID('%s') IS NOT NULL\n" % name,
                "        PRINT '<<< FAILED DROPPING %s %s >>>'\n" % (kind, name),
                "    ELSE\n",
                "        PRINT '<<< DROPPED %s %s >>>'\n" % (kind, name),
                "END\ngo\n"
            ])


            self._helptext(name, d)

            d.extend([
                "\ngo\nIF OBJECT_ID('%s') IS NOT NULL\n" % name,
                "    PRINT '<<< CREATED %s %s >>>'\n" % (kind, name),
                "ELSE\n",
                "    PRINT '<<< FAILED CREATING %s %s >>>'\ngo\n" % (kind, name),
            ])

            if mode is not None:
                d.append("EXEC sp_procxmode '%s','%s'\ngo\n" % (name, mode))

            self._get_permissions(name, d, sybase)

            if not sybase:
                d.append('SET ANSI_NULLS OFF\ngo\n')
                d.append('SET QUOTED_IDENTIFIER OFF\ngo\n')

            return (otype, ''.join(d))



    def _prepare(self):
        self('PREPARE TRAN')

















class PGSQLConnection(ValueBasedTypeConn):

    protocols.advise(
        instancesProvide=[ISQLObjectLister]
    )

    DRIVER = "pgdb"

    def _open(self):

        a = self.address

        return self.API.connect(
            host=a.server, database=a.db, user=a.user, password=a.passwd
        )


    def txnTime(self):
        r = ~ self('SELECT now()')  # retrieve the server's idea of the time
        return r[0]

    txnTime = binding.Make(txnTime)

    supportedTypes = (
        'BINARY','BOOL','DATETIME','FLOAT','INTEGER',
        'LONG','MONEY','ROWID','STRING',
    )














    def listObjects(self, full=False, obtypes=NOT_GIVEN):

        pgclass = lambda k,v: (
            """SELECT relname AS obname, '%s' AS obtype
            FROM pg_class WHERE relkind='%s'""" % (k,v)
        )

        relkinds = Items(
            table=pgclass('table','r'),
            index=pgclass('index','i'),
            view=pgclass('view','v'),
            proc="SELECT proname AS obname, 'proc' AS obtype FROM pg_proc",
            systable=pgclass('systable','s')
        )

        if obtypes is NOT_GIVEN:
            items = [v for (k,v) in relkinds]
        else:
            items = [relkinds[k] for k in obtypes if k in relkinds]

        if items:
            return self(' UNION ALL '.join(items))
        else:
            return self(pgclass('table','r')+" LIMIT 0")    # XXX kludge


class PsycopgConnection(PGSQLConnection):

    DRIVER = "psycopg"

    supportedTypes = (
        'BINARY', 'BOOLEAN', 'DATE', 'DATETIME', 'FLOAT', 'INTEGER',
        'INTERVAL', 'LONGINTEGER', 'NUMBER', 'ROWID', 'STRING', 'TIME'
    )







class SqliteConnection(ValueBasedTypeConn):

    DRIVER = "sqlite"

    supportedTypes = (
        'DATE', 'INT', 'NUMBER', 'ROWID', 'STRING', 'TIME', 'TIMESTAMP',
    )

    def _open(self):
        return self.API.connect(self.address.getFilename())

    def listObjects(self, full=False, obtypes=NOT_GIVEN):
        addsel = addwhere = ''

        if full:
            addsel = ', rootpage, sql '

        if obtypes is not NOT_GIVEN:
            addwhere = ' where type in (%s)' % \
                ', '.join(["'%s'" % sqlsafestr(s) for s in obtypes])

        return self('''select name as obname, type as obtype%s
            from SQLITE_MASTER%s''' % (addsel, addwhere))

    protocols.advise(
        instancesProvide=[ISQLObjectLister]
    )














class GadflyConnection(SQLConnection):

    DRIVER = "gadfly"

    Error    = Exception    # Gadfly doesn't really do DBAPI...  Sigh.
    Warning  = Warning

    supportedTypes = ()

    def _open(self):
        a = self.address
        return self.API.gadfly(a.db, a.dir)

    def createDB(self):
        """Close, clear, and re-create the database"""

        self.close()
        a = self.address

        from gadfly import gadfly
        g = gadfly()
        g.startup(self.address.db, self.address.dir)
        g.commit()
        g.close()


class GadflyURL(naming.URL.Base):

    supportedSchemes = ('gadfly',)
    defaultFactory = 'peak.storage.SQL.GadflyConnection'

    class db(naming.URL.RequiredField):
        pass

    class dir(naming.URL.RequiredField):
        pass

    syntax = naming.URL.Sequence(
        ('//',), db, '@', dir
    )

from peak.naming.factories.openable import FileURL

class SqliteURL(FileURL):
    supportedSchemes = 'sqlite',
    defaultFactory = 'peak.storage.SQL.SqliteConnection'


class GenericSQL_URL(naming.URL.Base):

    supportedSchemes = {
        'sybase':  'peak.storage.SQL.SybaseConnection',
        'pgsql':   'peak.storage.SQL.PGSQLConnection',
        'psycopg': 'peak.storage.SQL.PsycopgConnection',
        'mockdb':  'peak.storage.SQL.MockSQLConnection',
    }

    defaultFactory = property(
        lambda self: self.supportedSchemes[self.scheme]
    )

    class user(naming.URL.Field):
        pass

    class passwd(naming.URL.Field):
        pass

    class server(naming.URL.RequiredField):
        pass

    class db(naming.URL.Field):
        pass

    syntax = naming.URL.Sequence(
        ('//',), (user, (':', passwd), '@'), server, ('/', db)
    )






class OracleURL(naming.URL.Base):

    supportedSchemes = {
        'cxoracle':  'peak.storage.SQL.CXOracleConnection',
        'dcoracle2': 'peak.storage.SQL.DCOracle2Connection',
    }

    defaultFactory = property(
        lambda self: self.supportedSchemes[self.scheme]
    )

    class user(naming.URL.Field):
        pass

    class passwd(naming.URL.Field):
        pass

    class server(naming.URL.RequiredField):
        pass

    syntax = naming.URL.Sequence(
        ('//',), (user, (':', passwd), '@'), server, ('/',)
    )


















class OracleBase(SQLConnection):
    """Base class for Oracle connection drivers"""

    protocols.advise(
        instancesProvide=[ISQLObjectLister]
    )

    txnId = binding.Make('peak.util.uuid:UUID')
    txnBranch = "main"

    dbTxnStarted = dbTxnReadOnly = False
    txnAttrs = SQLConnection.txnAttrs + ('dbTxnReadOnly',)


    def setTxnState(self,outsideTxn):
        super(OracleBase,self).setTxnState(outsideTxn)
        if not self.dbTxnStarted and not self.dbTxnReadOnly:
            self._readOnly()


    def _startDBTxn(self):
        self.connection.rollback()  # throw away the read-only txn, if any
        if self.twoPhase:
            self._begin()
        elif self.serializable:
            self.dbTxnStarted = True
            self('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE',outsideTxn=None)
        return True


    def commitTransaction(self, txnService):
        try:
            self._doCommit()
        except self.Error,v:
            self.log.exception("Error during Oracle commit!")
            self.closeASAP()
            # Oracle raises this error on a two-phase commit if no rows were
            # actually changed in the DB.
            if self._errCode(v)<>'ORA-24756':
                raise

    def _prepare(self):
        self.connection.prepare()

    def _readOnly(self):
        self.dbTxnReadOnly = True
        self('SET TRANSACTION READ ONLY',outsideTxn=None)


    def txnTime(self):
        r = ~ self('SELECT SYSDATE FROM DUAL')  # retrieve the server's time
        return r[0]

    txnTime = binding.Make(txnTime)


    def listObjects(self, full=False, obtypes=NOT_GIVEN):

        addsel = addwhere = ''

        if full:
            addsel = ', subobject_name, object_id, data_object_id, last_ddl_time, timestamp, status, temporary, generated, secondary'

        if obtypes is not NOT_GIVEN:
            addwhere = ' where object_type in (%s)' % \
                ', '.join(["'%s'" %
                    {'proc':'FUNCTION'}.get(s, sqlsafestr(s.upper())) for s in obtypes])

        return self('''select lower(object_name) as "obname",
        DECODE(object_type, 'FUNCTION', 'proc', lower(object_type))
        as "obtype", created as "created"%s
            from user_objects%s''' % (addsel, addwhere), outsideTxn=None)










class CXOracleConnection(OracleBase):

    DRIVER = "cx_Oracle"

    def _open(self):
        a = self.address
        return self.API.connect(a.user, a.passwd, a.server)


    supportedTypes = (
        'BINARY','CURSOR','DATETIME','FIXED_CHAR','LONG_BINARY',
        'LONG_STRING','NUMBER','ROWID','STRING',
    )

    def _begin(self):
        if not hasattr(self.API,'TRANS_NEW'):
            return self._doBegin()
        kind = self.API.TRANS_NEW
        if self.serializable:
            kind += self.API.TRANS_SERIALIZABLE
        self._doBegin(kind)

    def _doBegin(self,*extra):
        self.connection.begin(0,str(self.txnId),self.txnBranch,*extra)

    def _readOnly(self):
        if self.twoPhase and hasattr(self.API,'TRANS_NEW'):
            self._doBegin(self.API.TRANS_NEW+self.API.TRANS_READONLY)
            self.dbTxnReadOnly = True
        else:
            super(CXOracleConnection,self)._readOnly()

    def _doCommit(self):
        self.connection.commit()

    def _errCode(self,v):
        return str(v).split(':',1)[0]




class DCOracle2Connection(OracleBase):

    DRIVER = "DCOracle2"

    def _open(self):
        a = self.address
        return self.API.connect(
            user=a.user, password=a.passwd, database=a.server,
        )

    supportedTypes = ('BINARY','DATETIME','NUMBER','ROWID','STRING')

    def _begin(self):
        self.connection.setTransactionXID((0,str(self.txnId),self.txnBranch))

    def _doCommit(self):
        self.connection.commit(not not self.twoPhase)

    def _errCode(self,v):
        return str(v.args[1]).split(':',1)[0]

    def typeMap(self):

        tm = {}
        ps = self.TYPES_NS
        api = self.API

        for k in self.supportedTypes:

            c = importObject(ps.get(k,NullConverter))

            for v in getattr(api,k).values:
                v = api.Type(v) # needed to get usable typemap keys
                tm[v] = importObject(ps.get(PropertyName.fromString(v),c))

        return tm

    typeMap = binding.Make(typeMap)



