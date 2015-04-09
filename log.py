#!/usr/bin/env python2

class TrivialLogger():

    def info(self, s):
        print("{}/INFO:{}".format(self.name, s))

    def warning(self, s):
        print("{}/WARNING:{}".format(self.name, s))

    def error(self, s):
        print("{}/ERROR:{}".format(self.name, s))

    def __init__(self):
        self.name = "TrivialLogger"
