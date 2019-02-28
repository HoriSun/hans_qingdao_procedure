#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

class Log(object):
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    #
    # """日志记录类"""
    # debug = logging.getLogger("Log").debug
    # info = logging.getLogger("Log").info
    # warn = logging.getLogger("Log").warn
    # error = logging.getLogger("Log").error

    @classmethod
    def init(cls, debug, info, warn, error):
        """初始化日志记录器"""
        cls.debug = debug
        cls.info = info
        cls.warn = warn
        cls.error = error
        
def log_wrap(prefix=None):
    if(not prefix):
        return Log
    else:
        class LogWrap(object):
            @staticmethod
            def debug(s, *args, **kwargs):
                Log.debug(prefix+s, *args, **kwargs)
            @staticmethod
            def info(s, *args, **kwargs):
                Log.info(prefix+s, *args, **kwargs)
            @staticmethod
            def warn(s, *args, **kwargs):
                Log.warn(prefix+s, *args, **kwargs)
            @staticmethod
            def error(s, *args, **kwargs):
                Log.error(prefix+s, *args, **kwargs)
        return LogWrap
            

def curdir():
    return os.path.abspath(os.path.curdir)

def pydir():
    return os.path.split(os.path.realpath(__file__))[0]
    
def check_ip_correct(ip):
    pattern = r'^(([0-9]{1,3}\.){3}([0-9]{1,3}))$'
    m = re.match(pattern,ip)
    if(m):
        n = map(lambda x:int(x),ip.split('.'))
        #print n
        return all(map(lambda x:0<=x<=255,n))
    else:
        return False
    