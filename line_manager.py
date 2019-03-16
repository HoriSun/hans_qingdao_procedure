from utils import log_wrap, check_ip_correct
from json_proc import dumps_json

from line_adapter import LineAdapter
import time
import threading

class LineManager(object):

    def __init__(self):
        self.Log = log_wrap(prefix = "[ Line Manager ] ")
        self.__set_default_param()
        self.__adapter = LineAdapter(self.__param["connection"]["addr"],
                                     self.__param["connection"]["port"]["keyence"])
        self.__running = True
        self.__line_rolling_left = False
        self.__line_rolling_right = False
        self.__line_roll_thread_left = None
        self.__line_roll_thread_right = None
        pass
        
    def __set_default_param(self):
        self.__param = {
            "connection": {
                "addr": "192.168.0.100",
                "port": {
                    "keyence": 8501
                }
            }
        }
        
    def update_param(self, config_data=None):
        if(not config_data):
            return

        self.__param = config_data
            
        json_param_final = dumps_json( self.__param , 
                                       indent = 4 ,  # None for one-line output
                                       sort_keys = False )
        self.Log.info("parameters: ")
        for line in json_param_final.split("\n"):
            self.Log.info('    '+line)
            
        self.__adapter.update_param(self.__param["connection"]["addr"],
                                    self.__param["connection"]["port"]["keyence"])
        if(self.__adapter.is_connected()):
            self.__adapter.reconnect()
        
    def connect(self):
        if(self.__adapter.is_connected()):
            self.__adapter.reconnect()
        else:
            self.__adapter.connect()
                
    def init(self):
        self.Log.info("initializing")
        self.__adapter.roll_stop()
        self.__adapter.power_on()
        self.__adapter.state_update_start()
        self.Log.info("initialized")
        #self.__adapter.left_roll_backward()
            
        #while(True):
        #    self.__adapter.left_roll_backward()
        #    time.sleep(0.1)
        #    break
        #while(True):
        #
        #    self.__adapter.left_roll_backward()
        #    time.sleep(0.1)
        
        
    def line_roll_left_step(self):
        self.__adapter.left_roll_forward()
        
    def line_roll_left_loop(self):
        while(self.__running and self.__line_rolling_left):
            self.line_roll_left_step()
            time.sleep(0.1)
    
    def line_roll_left_start(self):
        self.__line_rolling_left = True
        self.__line_roll_thread_left = threading.Thread( target = self.line_roll_left_loop )
        self.__line_roll_thread_left.setDaemon(True)
        self.__line_roll_thread_left.start()
    
    def line_roll_left_stop(self):
        self.__line_rolling_left = False
        self.__line_roll_thread_left.join()
        self.__line_roll_thread_left = None
        self.__adapter.left_roll_stop()
    
    def line_roll_right_step(self):
        self.__adapter.right_roll_forward()
        #self.__adapter.left_roll_backward()
        
    def line_roll_right_loop(self):
        self.Log.info("self.__running = %s"%(self.__running))
        self.Log.info("self.__line_rolling_right = %s"%(self.__line_rolling_right))
        while(self.__running and self.__line_rolling_right):
            self.line_roll_right_step()
            time.sleep(0.1)
    
    def line_roll_right_start(self):
        self.__line_rolling_right = True
        self.__line_roll_thread_right = threading.Thread( target = self.line_roll_right_loop )
        self.__line_roll_thread_right.setDaemon(True)
        self.__line_roll_thread_right.start()
    
    def line_roll_right_stop(self):
        self.__line_rolling_right = False
        self.__line_roll_thread_right.join()
        self.__line_roll_thread_right = None
        self.__adapter.right_roll_stop()
    
    def clean_up(self):
        self.__running = False
        self.stop_line()
        self.__adapter.power_off()
        self.__adapter.state_update_stop()
        
    #====== type-specific functions ======#
    
    def stop_line(self):
        self.__adapter.roll_stop()
        
    def get_sensor_state(self, station, sensor):
        return self.__adapter.data["line_%s_sensor_%s"%(station,sensor)]
        
    def wait_sensor_state(self, station, sensor, state=1):
        while((self.__running) and 
              (self.get_sensor_state(station, sensor) != state)):
            #self.Log.info("="*20)
            #for st in ["left", "right"]:
            #    for sr in ["front","middle","end"]:
            #        self.Log.info("%s-%s : %s"%(st,sr,self.get_sensor_state(station, sensor)))
            #self.Log.info("%s-%s : %s"%(st,sr,self.get_sensor_state(station, sensor)))
            time.sleep(0.1)
    
    def test(self):
        return
        self.Log.info("===========================!!!!!")
        self.__line_rolling_right = True
        self.line_roll_right_loop()
        self.__line_rolling_right = False
        
        pass
