#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

class Log(object):
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    #
    # """��־��¼��"""
    # debug = logging.getLogger("Log").debug
    # info = logging.getLogger("Log").info
    # warn = logging.getLogger("Log").warn
    # error = logging.getLogger("Log").error

    @classmethod
    def init(cls, debug, info, warn, error):
        """��ʼ����־��¼��"""
        cls.debug = debug
        cls.info = info
        cls.warn = warn
        cls.error = error
        

def curdir():
    return os.path.abspath(os.path.curdir)

def pydir():
    return os.path.split(os.path.realpath(__file__))[0]