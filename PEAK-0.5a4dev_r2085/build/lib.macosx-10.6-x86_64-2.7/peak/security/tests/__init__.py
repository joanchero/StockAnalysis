"""PEAK security test suite package

Use with unittest.py to run all tests, or use the 'test_suite()' function in
an individual module to get just those tests."""


allSuites = [
    'permission:test_suite',
    'peak.security.tests:test_docs',
]

def test_docs():
    from peak.util import doctest
    return doctest.DocFileSuite(
        'rules.txt', optionflags=doctest.ELLIPSIS, package='peak.security',
    )
    
def test_suite():
    from peak.util.imports import importSuite
    return importSuite(allSuites, globals())

