#!/bin/sh -login
# Edit the next line to reflect the location of the trivial_cgi directory
export PYTHONPATH=../trivial_cgi
exec peak CGI import:the_cgi.DemoCGI
