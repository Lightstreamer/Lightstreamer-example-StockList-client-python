#!/usr/bin/python

import sys

PY3 = (sys.version_info[0] >= 3)
PY2 = sys.version_info[0] == 2    

if PY3:
    from urllib.request import urlopen
    _urlopen = urlopen
    from urllib.parse import urlparse as parse_url
    from urllib.parse import urljoin, urlencode

    def str_to_bytes(s, encoding=None):
        return s.encode(encoding or 'ascii')

else:
    from urllib2 import urlopen as _urlopen
    from urlparse import urlparse as parse_url
    from urlparse import urljoin
    from urllib import urlencode

    def str_to_bytes(s, encoding='ascii'):
        return s

from six import iteritems as _iteritems
