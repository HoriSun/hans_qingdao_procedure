from utils import log_wrap, check_ip_correct
from json_proc import dumps_json
from agv_adapter import AgvAdapter

# [ TODO ] 1. Use pub-sub machanism to decouple all modules.
# [ TODO ] 2. Make things parallel and asyncronized.

'''
==== Design Purpose ====
Data-driven and state-driven, all calls should return instantly,
except for those explictly defined as blocking operations (e.g. waiting for the 
task).

Automatically updates state from the AGV.
Auto-reconnecting when the connection is lost.
'''

class AgvManager(object):
        
    __ptypes = ["state", "control", "task", "config"]

    def __init__(self):
        self.Log = log_wrap(prefix = "[ Agv Manager ] ")
        self.__set_default_param()
        self.__adapter = AgvAdapter()
        pass
        
    def __set_default_param(self):
        self.__param = {
            "connection": {
                "addr": "192.168.0.3",
                "port": {
                    "state": 8888,
                    "control": 8889,
                    "task": 8890,
                    "config": 8891
                }
            }    
        }
    
    def update_param(self, config_data=None):
        if(not config_data):
            return
            
        if("connection" in config_data):
            conn = config_data["connection"]
            if("addr" in conn):
                addr = conn["addr"]
                if(check_ip_correct(addr)):
                    self.__param["connection"]["addr"] = addr
            if("port" in conn):
                port = conn["port"]
                if(isinstance(port, dict)):
                    if("state" in port):
                        if(isinstance(port["state"], int)):
                            self.__param["connection"]["port"]["state"] = port["state"]
                    
                    if("control" in port):
                        if(isinstance(port["control"], int)):
                            self.__param["connection"]["port"]["control"] = port["control"]
                    
                    if("task" in port):
                        if(isinstance(port["task"], int)):
                            self.__param["connection"]["port"]["task"] = port["task"]
                    
                    if("config" in port):
                        if(isinstance(port["config"], int)):
                            self.__param["connection"]["port"]["config"] = port["config"]
                
        #print dumps_json(self.__param, indent=None, sort_keys=False)
        
        json_param_final = dumps_json( self.__param , 
                                       indent = 4 ,  # None for one-line output
                                       sort_keys = False )
        self.Log.info("parameters: ")
        for line in json_param_final.split("\n"):
            self.Log.info('    '+line)
            
        self.__adapter.set_agv_ip(self.__param["connection"]["addr"])
        for ptype in self.__ptypes:
            self.__adapter.set_port(ptype, self.__param["connection"]["port"][ptype])
        
    def connect(self):
        self.__adapter.connect()
        #self.__adapter.wait_for_connection()
        pass
        
    def init(self):
        pass
        
    def clean_up(self):
        pass
        
    #====== type-specific functions ======#
        
    def go_right(self):
        pass
        
    def stop_line(self):
        pass