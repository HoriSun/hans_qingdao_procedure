from utils import log_wrap, check_ip_correct
from json_proc import dumps_json

class StarManager(object):
    def __init__(self):
        self.Log = log_wrap(prefix = "[ Star Manager ] ")
        self.__set_default_param()
        pass
        
    def __set_default_param(self):
        self.__param = {
            "connection": {
                "addr": "127.0.0.1",
                "port": {
                    "modbus": 502
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
                    if("modbus" in port):
                        if(isinstance(port["modbus"], int)):
                            self.__param["connection"]["port"]["modbus"] = port["modbus"]
        #print dumps_json(self.__param, indent=None, sort_keys=False)
        
        json_param_final = dumps_json( self.__param , 
                                       indent = 4 ,  # None for one-line output
                                       sort_keys = False )
        self.Log.info("parameters: ")
        for line in json_param_final.split("\n"):
            self.Log.info('    '+line)
        
    def connect(self):
        pass
        
    def init(self):
        pass
        
    def clean_up(self):
        pass
        
    #====== type-specific functions ======#
        
    def go_right(self):
        pass
        
    def check_goods(self):
        # [ TODO ] the two goods should be there,
        #          otherwise burst out sound alert and light blinks in red.
        pass
        
    def light(self, color="green", blink=False):
        pass
        
    def play_sound(self, sound_id=0, repeat_time=0):
        pass
        

        
def test():
    m = StarManager()
        
if __name__ == "__main__":
    test()