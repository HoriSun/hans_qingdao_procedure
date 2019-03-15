#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import time
import logging
import threading
import signal
from json_proc import loadf_json
from log_manager import LogManager
from system_check import check_system
from define import SystemEnum
from utils import log_wrap, pydir
from agv_manager import AgvManager
from star_manager import StarManager
from line_manager import LineManager

# [ TODO ] Add log, text & sqlite
class QingDaoProcedure(object):
    def __init__( self,
                  root_dir = pydir(),
                  log_dir = 'log' ,
                  archive_dir = 'log_archive' ,
                  max_log_size = 4096 ):
        self.Log = log_wrap(prefix = "[ Qingdao Procedure ] ")
        
        # [ TODO ] Set default value of parameters here
        self.__root_dir = root_dir
        self.__log_dir = os.path.join(self.__root_dir,log_dir)
        self.__archive_dir = os.path.join(self.__root_dir,archive_dir)
        self.__max_log_size = max_log_size
        self.__log_manager = LogManager( self.__log_dir ,
                                         self.__archive_dir ,
                                         self.__max_log_size )
        self.__agv_manager = AgvManager()
        self.__star_manager = StarManager()
        self.__line_manager = LineManager()
        
        self.__managers = [ #self.__agv_manager ,
                            #self.__star_manager ,
                            self.__line_manager 
                          ]
        
        pass
    
    
            
    def __check_instance(self):
        """检查是否存在多个运行实例

        :return:
        """
        running_on_windows = None
        try:
            running_on_windows = (check_system() == SystemEnum.WINDOWS)
        except AssertionError as e:
            self.Log.error("[ Runner.__check_instance ] "
                      "Assertion error: %s"%repr(e))
            logging.exception(e)
        except Exception as e:
            self.Log.error("[ Runner.__check_instance ] "
                      "Unexpected error: %s"%repr(e))
            logging.exception(e)

        if(running_on_windows):
            import win32event
            import win32api
            from winerror import ERROR_ALREADY_EXISTS

            self.__tmux = win32event.CreateMutex(None, False, "navigation.temp.line")
            last_error = win32api.GetLastError()
            if last_error == ERROR_ALREADY_EXISTS:
                self.Log.error("exit running instance! name = " + "navigation")
                raise RuntimeError("exit running instancel!")
        else:
            self.Log.error("[ Runner.__check_instance ] "
                      "(running_on_windows == %s) "
                      "Not running on Windows, "
                      "__check_instance() won't do anything. "
                      "Make sure only one instance is running on this machine. "%(
                          repr(running_on_windows)
                      ))

    
    
    def load_config(self, config_file_name=""):
        # [ TODO ] may try to use sqlite
        self.__set_default_param()        
        config_file = None
        config_data = None
        
        if config_file_name:
            try:
                config_file = file( os.path.join( self.__root_dir ,
                                                  config_file_name ),
                                    "r" )
            except Exception as e:
                config_file = None
                self.Log.warn("Config file `%s` open error, "
                         "using default configurations. "
                         "The file may not exist. "
                         "Error message: `%s`"%(config_file_name,e))
                 
            if(config_file):
                try:
                    config_data = loadf_json(config_file)
                except Exception as e:
                    config_data = None
                    self.Log.warn("Config file `%s` parsing error, "
                             "using default configurations. "
                             "Please check the format of your config file. "
                             "Error message: `%s`"%(config_file_name,e))
                pass #if(config_file)
            pass #if not config_file_name else
            
        if config_data:
            self.__update_param(config_data)
        
        
    def __set_default_param(self):
        self.__param = {
            
            "agv": {
                "connection": {
                    "addr": "192.168.0.3",
                    "port": {
                        "state": 8888,
                        "control": 8889,
                        "task": 8890,
                        "config": 8891
                    }
                },
                "station": {
                    "right": {
                        "virtual": {
                            "ready": 22,
                            "line": 12,
                        },
                        "mag": {
                            "line": 2
                        }
                    },
                    "left": {
                        "virtual": {
                            "ready": 21,
                            "line": 11,
                        },
                        "mag": {
                            "line": 1
                        }
                    }
                }
            },
            
            "star": {
                "connection": {
                    "addr": "192.168.0.168",
                    "port": {
                        "modbus": 502
                    }
                }
            },
            
            "line": {
                "connection": {
                    "addr": "192.168.0.100",
                    "port": {
                        "keyence": 8501
                    }
                }
            }
            
        }

    def __update_param(self, config_data):
        #if("agv" in config_data):
        #    self.__agv_manager.update_param(config_data["agv"])
        #if("star" in config_data):
        #    self.__star_manager.update_param(config_data["star"])
        if("line" in config_data):
            self.__line_manager.update_param(config_data["line"])
        
    def __connect_all(self):
        # [ TODO ] Better make this asyncronized
        for m in self.__managers:
            m.connect()
            
    def __start_scheduling(self):
        self.__schedule_thread = threading.Thread( target = self.__schedule_loop )
        self.__schedule_thread.setDaemon(True)
        self.__schedule_thread.start()
        
    def start(self):
        self.__log_manager.archive_and_cleanup()
        self.__check_instance()
        self.__connect_all()
        self.__start_scheduling()
        self.__block()
        
    def __block(self):
        def exit(signum, frame):
            self.Log.info("Program stopped by the user. "
                     "signum:%s, frame:%s"
                     ""%(signum, frame))
            self.__clean_up()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, exit)
        signal.signal(signal.SIGTERM, exit)

        for_a_day = 24*60*60
        
        while(True):
            time.sleep( for_a_day )
        
    def __schedule_loop(self):
        self.__init_all()
        
        # alias
        line = self.__line_manager
        agv = self.__agv_manager
        star = self.__star_manager
        
        while True:
            #agv.leave_right()
            #agv.go_left()
            #agv.leave_left()
            #agv.go_right()
            #line.line_roll_right_start()
            #line.line_roll_left_start()
            pass
        
        pass
        
    def __init_all(self):
        # [ TODO ] Better make this asyncronized
        for m in self.__managers:
            m.init()
        
        # [ TODO ] ### Move them to the init position
        # alias
        line = self.__line_manager
        agv = self.__agv_manager
        star = self.__star_manager
        
        self.Log.info("Start initialize device states")
        
        
        line.stop_line()
        #line.test()
        #agv.stop_line()
        
        #agv.go_right()
        
        #star.go_right()
            
        #star.check_goods()
        
        self.Log.info("Initialized.")
        
        
    def __clean_up(self):
        # [ TODO ] Better make this asyncronized
        for m in self.__managers:
            m.clean_up()
    
    
    
if "__main__" == __name__:

    bytes_per_day_guess = 600 * 1024 * 1024  # means 600MB per day
    log_keep_day = 3
    max_size = bytes_per_day_guess * log_keep_day

    proc = QingDaoProcedure( root_dir = pydir(),
                             log_dir = "log.temp.line",
                             archive_dir = "log_archive.temp.line",
                             max_log_size = max_size )
    proc.load_config( config_file_name = "qingdao_config.json" )
    proc.start()