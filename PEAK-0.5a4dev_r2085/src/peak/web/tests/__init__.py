"""peak.web test suite package

Use with unittest.py to run all tests, or use the 'test_suite()' function in
an individual module to get just those tests."""


allSuites = [
    'wsgiref.tests:test_suite',
    'test_sitemap:test_suite',   
    'test_environ:test_suite',
    'test_templates:test_suite',
    'test_resources:test_suite',   
]


def test_suite():
    from peak.util.imports import importSuite
    return importSuite(allSuites, globals())

