from utils import Log, check_ip_correct

'''
==== Design Purpose ====
Data-driven and state-driven, all calls should return instantly,
except for those explictly defined as blocking operations (e.g. waiting for the 
task).

Automatically updates state from the AGV.
Auto-reconnecting when the connection is lost.
'''

class AgvManager(object):
    def __init__(self):
        self.__set_default_param()
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
            
        if("connetion" in config_data):
            conn = config_data["connection"]
            if("addr" in conn):
                addr = con["addr"]
                if(check_ip_correct(addr)):
                    self.__param["connection"]["addr"] = addr
            if("port" in conn):
                port = conn("port")
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
                
   
    def connect(self):
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