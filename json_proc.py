#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json


def json_load_byteified(file_handle):
    return _byteify(
        json.load(file_handle, object_hook=_byteify),
        ignore_dicts=True
    )

def json_loads_byteified(string):
    if(not string):
        return None

    return _byteify(
        json.loads(string, object_hook=_byteify),
        ignore_dicts=True
    )

loads_json = json_loads_byteified
dumps_json = json.dumps

loadf_json = json_load_byteified
dumpf_json = json.dump

def _byteify(data, ignore_dicts = False):
    # if this is a unicode string, return its string representation
    if isinstance(data, unicode):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [ _byteify(item, ignore_dicts=True) for item in data ]
    # if this is a dictionary, return list of bytefied values
    # but only if we haven't already bytefied it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True) : _byteify(value, ignore_dicts=True)
            for key, value in data.iteritems()
        }
    return data
##enddef _byteify    
