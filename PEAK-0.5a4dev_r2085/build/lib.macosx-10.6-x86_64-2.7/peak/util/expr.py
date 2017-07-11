"""Create abstract syntax trees from in-line Python expressions

    TODO:

        * Define interface for OpGenerators

        * Create mini-framework for symbolic representation, transformation,
          and stringification of expressions (handling operator precedence
          and parens, simple execution, etc.)

"""

__all__ = ['proxyType', 'unproxy']


class _ProxyBase(object):

    __slots__ = '_proxied_object'

    def __init__(self,ob):
        type(self)._proxied_object.__set__(self,ob)

    def __nonzero__(self):
        raise TypeError("Can't truth-test an expression proxy!")


def unproxy(ob):
    if isinstance(ob,_ProxyBase):
        return type(ob)._proxied_object.__get__(ob,type(ob))
    else:
        return ob










class OpGenerator:

    def __init__(self,buildFunc,proxyType):
        self.buildFunc = buildFunc
        self.proxyType = proxyType

    def binop(self,op):
        proxyType = self.proxyType
        buildFunc = self.buildFunc
        def operator(self,other):
            return proxyType(buildFunc(op, unproxy(self), unproxy(other)))
        return operator

    def rev_binop(self,op):
        proxyType = self.proxyType
        buildFunc = self.buildFunc
        def operator(self,other):
            return proxyType(buildFunc(op, unproxy(other), unproxy(self)))
        return operator

    def unary_op(self,op):
        proxyType = self.proxyType
        buildFunc = self.buildFunc
        def operator(self):
            return proxyType(buildFunc(op, unproxy(self)))
        return operator

    def call_op(self):
        proxyType = self.proxyType
        buildFunc = self.buildFunc
        def __call__(self,*__args,**__kw):
            return proxyType(
                buildFunc('()', unproxy(self),
                    tuple([unproxy(a) for a in __args]),
                    dict([(k,unproxy(v)) for k,v in __kw.items()])
                )
            )
        return __call__



def _setupOperators(klass, g):
    for k,v in zip(
        "lt le eq ne gt ge getitem getattribute".split(),
        "<  <= == != >  >= []      .".split()
    ):
        setattr(klass,('__%s__' % k), g.binop(v))

    for k,v in zip(
        "add sub mul floordiv mod pow lshift rshift and xor or div truediv".split(),
        "+   -   *   //       %   **  <<     >>     &   ^   |  /   /".split()
    ):
        setattr(klass,('__%s__' % k), g.binop(v))
        setattr(klass,('__r%s__' % k), g.rev_binop(v))

    for k,v in zip(
        "neg pos invert".split(),
        "u-   u+   ~".split()
    ):
        setattr(klass,('__%s__' % k), g.unary_op(v))

    setattr(klass,'__call__', g.call_op())


def proxyType(buildFunc, generatorType=OpGenerator, name='ExpressionProxy'):
    klass = type(name, (_ProxyBase,), {})
    _setupOperators(klass, generatorType(buildFunc,klass))
    return klass














