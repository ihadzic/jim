#!/usr/bin/env python2

import tornado
import log
import datetime
import os
import binascii
from tornado import web, httpserver

_http_server = None
_https_server = None
_template_root = './templates'
_log = None
# This is default (test-only) certificate located in ./certs directory.
# default certificate is self-signed, so we don't have 'ca_cert' field
# in the dictionary. Normally, we need one to point to the 'CA'
_test_ssl_options = { 'certfile' : './certs/cert.pem', 'keyfile': './certs/key.pem' }

class DynamicBaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

    def get_current_user(self):
        return self.get_secure_cookie('user')

class RootHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/index.html', permanent = True)

class LoginHandler(DynamicBaseHandler):
    def get(self):
        if self.current_user:
            self.redirect('/date')
        else:
            self.write('<html><body><form action="/login" method="post">'
                       'Name: <input type="text" name="name">'
                       '<input type="submit" value="Sign in">'
                       '</form></body></html>')

    def post(self):
        # TODO: check the password here
        self.set_secure_cookie('user', self.get_argument('name'))
        self.redirect('/date')

class LogoutHandler(DynamicBaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect('/login')

class DateHandler(DynamicBaseHandler):
    def get(self):
        if self.current_user:
            name = tornado.escape.xhtml_escape(self.current_user)
        else:
            name = 'nobody'
        self.render('date.html',
                    date_string = str(datetime.datetime.now()),
                    user_string = name)

def run_server(ssl_options = _test_ssl_options, http_port = 80, https_port = 443, log_facility = None, html_root = './html', template_root = './templates'):
    global _http_server
    global _https_server
    global _log

    # list handlers for REST calls here
    handlers = [
        ('/', RootHandler),
        ('/login', LoginHandler),
        ('/logout', LogoutHandler),
        ('/date', DateHandler)
        ]

    if log_facility:
        _log = log_facility
    else:
        _log = log.TrivialLogger()

    handlers.append(('/(.*)', web.StaticFileHandler, {'path': html_root}))
    app = tornado.web.Application(handlers = handlers, template_path = template_root,
                                  cookie_secret = binascii.b2a_hex(os.urandom(32)))
    _log.info("creating servers")
    _http_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False)
    _https_server = tornado.httpserver.HTTPServer(app, no_keep_alive = False, ssl_options = ssl_options)
    _log.info("setting up TCP ports")
    _http_server.listen(http_port)
    _https_server.listen(https_port)
    _log.info("starting server loop")
    tornado.ioloop.IOLoop.instance().start()
    _log.info("server loop exited")
