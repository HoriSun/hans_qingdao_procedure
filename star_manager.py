from utils import log_wrap, check_ip_correct
from json_proc import dumps_json
from star_adapter import StarAdapter

class StarManager(object):
    def __init__(self):
        self.Log = log_wrap(prefix = "[ Star Manager ] ")
        self.__set_default_param()
        self.__adapter = StarAdapter()
        self.__runnning = True
        pass
        
    def __set_default_param(self):
        self.__param = {
            "connection": {
                "addr": "127.0.0.1",
                "port": {
                    "modbus": 502
                }
            },
            "station": {
                "ready": 1,
                "place": 2,
                "pick": 3
            },
            "options": {
                "log_message": False
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

        self.__adapter.reconfigure(ip = self.__param["connection"]["addr"],
                                   port = self.__param["connection"]["port"]["modbus"],
                                   log_message = self.__param["options"]["log_message"])
        
    def connect(self):
        self.__adapter.connect()
        self.wait_for_connection()
        
        
    def init(self):
        self.__adapter.init()
        self.__adapter.elfin_ready()
        self.__adapter.agv_go_ready()
        pass
    
    def clean_up(self):
        self.__adapter.clean_up()
        self.__adapter.elfin_ready()
        self.__adapter.agv_go_ready()
        pass
        
    #====== type-specific functions ======#
        

    def wait_agv_task_finish(self):
        self.__adapter.wait_agv_task_finish()

    def wait_elfin_task_finish(self):
        self.__adapter.wait_elfin_task_finish()

    def agv_go_ready(self):
        self.wait_agv_task_finish()
        self.__adapter.agv_go_ready()
        
    def agv_go_pick(self):
        self.wait_agv_task_finish()
        self.__adapter.agv_go_pick()
        
    def agv_go_place(self):
        self.wait_agv_task_finish()
        self.__adapter.agv_go_place()
        
    def elfin_ready(self):
        self.wait_elfin_task_finish()
        self.__adapter.elfin_ready()
        
    def elfin_place(self, block):
        self.wait_elfin_task_finish()
        self.__adapter.elfin_place(block)
        
    def elfin_pick(self, block):
        self.wait_elfin_task_finish()
        self.__adapter.elfin_pick(block)
        
    def check_goods(self):
        # [ TODO ] the two goods should be there,
        #          otherwise burst out sound alert and light blinks in red.
        pass
        
    def light(self, color="green", blink=False):
        pass
        
    def play_sound(self, sound_id=0, repeat_time=0):
        pass
        
    def wait_for_connection(self):
        self.__adapter.wait_for_connection()
        
def test():
    m = StarManager()
        
if __name__ == "__main__":
    test()
