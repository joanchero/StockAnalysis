#!/bin/sh -login
# Edit the next line to reflect the location of the trivial_web directory
export PYTHONPATH=../trivial_web
exec peak CGI import:webapp.WebApp
