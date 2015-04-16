#!/usr/bin/env python2

import tornado
import log
import magic
from tornado import web, httpserver

_http_server = None
_https_server = None
_html_root = './'
_log = None
_magic = None

class DefaultHandler(tornado.web.RequestHandler):
    def get(self, match):
        _log.info("incoming request: {}".format(self.request))
        _log.info("matched default match: {}".format(match))
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Connection", "close")
        if match:
            fname = _html_root + '/' + match
        else:
            fname = _html_root + '/index.html'
        try:
            with open(fname, 'rb') as fd:
                content = fd.read()
            mime_type = _magic.file(fname)
            self.set_header("Content-type",  mime_type)
            self.finish(content)
        except:
            self.set_status(404)
            self.finish("Not found: {}".format(match))

_app = tornado.web.Application([
        ('/(.*)', DefaultHandler)
])

# TODO: SSL needs this
# ssl_options['certfile'] - server certificate
# ssl_options['keyfile'] - server key
# ssl_options['ca_certs'] - CA certificate

def run_server(ssl_options = {}, http_port = 80, https_port = 443, log_facility = None, html_root = './'):
    global _http_server
    global _https_server
    global _log
    global _magic

    # http://www.zak.co.il/tddpirate/2013/03/03/the-python-module-for-file-type-identification-called-magic-is-not-standardized/
    try:
        _magic = magic.open(magic.MAGIC_MIME_TYPE)
        _magic.load()
    except AttributeError,e:
        _magic = magic.Magic(mime=True)
        _magic.file = _magic.from_file

    if log_facility:
        _log = log_facility
    else:
        _log = log.TrivialLogger()
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(_app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(_app, no_keep_alive = False, ssl_options = ssl_options)
    _log.info("setting up TCP ports")
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
