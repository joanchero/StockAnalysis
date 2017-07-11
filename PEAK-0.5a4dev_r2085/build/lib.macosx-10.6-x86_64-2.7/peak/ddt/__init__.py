"""Document-Driven Testing

    This package provides tools for doing automated parsing, processing, and
    annotation of "test tables" in documents (typically HTML files).

    To use the package, one creates requirements/design documents that contain
    tables describing "text fixtures" such as expected outputs given a set of
    inputs.  Then, once you've created appropriate adapters for the tables, you
    can run a DDT processor over the document to create an annotated document.
    The annotated version will usually shade passed tests in green, failed
    tests in red, add a summary of passed/failed tests, etc.

    You can then do things like generate the annotated version on a regular
    schedule and post it on a website, so that all of a project's stakeholders
    can see the development status relative to the requirements.

    Goals:

    * Support all the "FIT":http://fit.c2.com/ idioms cleanly

    * Support HTML generated by MS products, StructuredText, and reST, so that
      developers and non-developers alike can create testing documents

    * Independent reimplementation, free of GPL restrictions

    * Use PEAK development idioms (e.g. domain model objects separated from
      parse/format implementation, property namespace to look up fixture types,
      'commands' framework for command-line tools, etc.)
"""




