from utils import log_wrap, check_ip_correct
from json_proc import dumps_json

from line_adapter import LineAdapter

class LineManager(object):

    def __init__(self):
        self.Log = log_wrap(prefix = "[ Line Manager ] ")
        self.__set_default_param()
        self.__adapter = LineAdapter(self.__param["connection"]["addr"],
                                     self.__param["connection"]["port"]["keyence"])
        self.__running = True
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
        self.__adapter.roll_stop()
        self.__adapter.power_on()
        self.__adapter.state_update_start()
        
    def clean_up(self):
        self.__running = False
        self.stop_line()
        self.__adapter.state_update_stop()
        
    #====== type-specific functions ======#
    
    def stop_line(self):
        self.__adapter.roll_stop()
        
    def wait_state(self, device, sensor, state):
        sensor_id = "line_"+device+"_sensor_"+sensor
        while(self.__running and self.__adapter.data[sensor_id] != state):
            time.sleep(0.1)
            