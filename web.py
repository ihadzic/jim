
#!/usr/bin/env python2

import tornado
import log
from tornado import web, httpserver

_http_server = None
_https_server = None
_html_root = './'
_log = None

# TODO: SSL needs this
# ssl_options['certfile'] - server certificate
# ssl_options['keyfile'] - server key
# ssl_options['ca_certs'] - CA certificate

class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/index.html', permanent = True)

def run_server(ssl_options = {}, http_port = 80, https_port = 443, log_facility = None, html_root = './'):
    global _http_server
    global _https_server
    global _log

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler)
        ]

    if log_facility:
        _log = log_facility
    else:
        _log = log.TrivialLogger()

    handlers.append(('/(.*)', web.StaticFileHandler, {'path': html_root}))
    app = tornado.web.Application(handlers)
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False, ssl_options = ssl_options)
    _log.info("setting up TCP ports")
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
