#!/usr/bin/python

import sys

# Modules aliasing and function utilities to support a
# very coarse version differentiation between Python 2 and Python 3.
PY3 = sys.version_info[0] == 3
PY2 = sys.version_info[0] == 2

if PY3:
    from urllib.request import urlopen as _urlopen
    from urllib.parse import (urlparse as parse_url, urljoin, urlencode)

    def _url_encode(params):
        return urlencode(params).encode("utf-8")

    def _iteritems(d):
        return iter(d.items())

    wait_for_input = input

else:
    from urllib import (urlopen as _urlopen, urlencode)
    from urlparse import urlparse as parse_url
    from urlparse import urljoin

    def _url_encode(params):
        return urlencode(params)

    def _iteritems(d):
        return d.iteritems()

    wait_for_input = raw_input
