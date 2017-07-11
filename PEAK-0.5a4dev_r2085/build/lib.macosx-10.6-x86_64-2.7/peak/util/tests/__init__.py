"""PEAK utility modules test suite package

Use with unittest.py to run all tests, or use the 'test_suite()' function in
an individual module to get just those tests."""


allSuites = [
    'EigenData:test_suite',
    'FileParsing:test_suite',
    'SOX:test_suite',
    'uuid:test_suite',
    'test_expr:test_suite',
    'test_mockdb:test_suite',
    'test_mockets:test_suite',
    'test_signature:test_suite',
    'test_conflict:test_suite',
    'peak.util.tests:test_unittrace',
    'peak.util.tests:test_Graph',
]

def test_unittrace():
    from peak.util import doctest
    return doctest.DocFileSuite(
        'unittrace.txt', optionflags=doctest.ELLIPSIS, package='peak.util',
    )


def test_Graph():
    from peak.util import doctest
    return doctest.DocFileSuite(
        'Graph.txt', optionflags=doctest.ELLIPSIS, package='peak.util',
    )


def test_suite():
    from peak.util.imports import importSuite
    return importSuite(allSuites, globals())

