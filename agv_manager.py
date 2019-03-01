from utils import log_wrap, check_ip_correct
from json_proc import dumps_json
from agv_adapter import AgvAdapter
import math

# [ WARNING ] 1. Operators should make sure the AGV is at the init position when
#                the flow starts

# [ TODO ] 1. Use pub-sub & callback machanism to decouple all modules.
# [ TODO ] 2. Make things parallel and asyncronized.
# [ TODO ] 3. Use event & callback machanism to eliminate busy waiting.
# [ TODO ] 4. Adopt the image of task-chain from Seer Robotics.

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
        self.__adapter.setSerialize(True)
        
        self.__sensors = {
            "detect_front": False,
            "detect_middle": False,
            "detect_back": False
        }
        
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
            },
            "sensor": {
                "detect_front": 1,
                "detect_middle": 2,
                "detect_back": 3
            },
            "control": {
                "stop_line": 4
            }
        }
    
    # [ TODO ] 1. Make it automatically checked, like protobuf format check_ip_correct
    # [ TODO ] 2. Automatically detect undefined parameters, and stop corresponding 
    #             operation and report error when the inexistance of parameter found. 
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
        
        if("station" in config_data):
            station = config_data["station"]
            if("right" in station):
                right = station["right"]
                if(isinstance(right, dict)):
                    if("virtual" in station):
                        virtual = right["virtual"]
                        if(isinstance(virtual, dict)):
                            if("ready" in virtual):
                                ready = virtual["ready"]
                                if(isinstance(ready, int)):
                                    self.__param["station"]["right"]["virtual"]["ready"] = ready
                            if("line" in virtual):
                                line = virtual["line"]
                                if(isinstance(line, int)):
                                    self.__param["station"]["right"]["virtual"]["line"] = line
                    if("mag" in station):
                        mag = right["mag"]
                        if(isinstance(mag, dict)):
                            if("ready" in mag):
                                ready = mag["ready"]
                                if(isinstance(ready, int)):
                                    self.__param["station"]["right"]["mag"]["ready"] = ready
                            if("line" in mag):
                                line = mag["line"]
                                if(isinstance(line, int)):
                                    self.__param["station"]["right"]["mag"]["line"] = line
            if("left" in station):
                left = station["left"]
                if(isinstance(left, dict)):
                    if("virtual" in station):
                        virtual = left["virtual"]
                        if(isinstance(virtual, dict)):
                            if("ready" in virtual):
                                ready = virtual["ready"]
                                if(isinstance(ready, int)):
                                    self.__param["station"]["left"]["virtual"]["ready"] = ready
                            if("line" in virtual):
                                line = virtual["line"]
                                if(isinstance(line, int)):
                                    self.__param["station"]["left"]["virtual"]["line"] = line
                    if("mag" in station):
                        mag = left["mag"]
                        if(isinstance(mag, dict)):
                            if("ready" in mag):
                                ready = mag["ready"]
                                if(isinstance(ready, int)):
                                    self.__param["station"]["left"]["mag"]["ready"] = ready
                            if("line" in mag):
                                line = mag["line"]
                                if(isinstance(line, int)):
                                    self.__param["station"]["left"]["mag"]["line"] = line
                            
        if("sensor" in config_data):
            sensor = config_data["sensor"]
            if(isinstance(sensor, dict)):
                if("detect_front" in sensor):
                    detect_front = sensor["detect_front"]
                    if(isinstance(detect_front, int) and detect_front >= 0):
                        self.__param["sensor"]["detect_front"] = detect_front
                if("detect_middle" in sensor):
                    detect_middle = sensor["detect_middle"]
                    if(isinstance(detect_middle, int) and detect_middle >= 0):
                        self.__param["sensor"]["detect_middle"] = detect_middle
                if("detect_back" in sensor):
                    detect_back = sensor["detect_back"]
                    if(isinstance(detect_back, int) and detect_back >= 0):
                        self.__param["sensor"]["detect_back"] = detect_back
        
        if("control" in config_data):
            control = config_data["control"]
            if(isinstance(control, dict)):
                if("stop_line" in control):
                    stop_line = control["stop_line"]
                    if(isinstance(stop_line, int) and stop_line >= 0):
                        self.__param["control"]["stop_line"] = stop_line
        
        
        
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
        self.__adapter.wait_for_connection()
        self.Log.info("AGV connected.")
        pass
        
    def init(self):
        self.__adapter.get_input_callback(self.__param["sensor"].values(), io_callback)
        self.__adapter.trigger_button_reset()
        self.__adapter.trigger_button_run()
        # [ TODO ] Make sure localization is correct
        
    def clean_up(self):
        self.__adapter.speed_control(0,0)
        self.__adapter.cancel_all_tasks()
        #self.__adapter.trigger_button_stop()
        self.__adapter.shutdown()
        
    #====== type-specific functions ======#
        
    def go_right(self):
        fixed_node = self.__param["station"]["right"]["virtual"]["ready"]
        mag_node = self.__param["station"]["right"]["mag"]["line"]
        self.__adapter.go_fixed_unblock( fixed_node )
        self.__adapter.wait_fixed( fixed_node )
        self.__adapter.go_mag_unblock( mag_node )
        self.__adapter.wait_mag( mag_node )
        #self.__adapter.go_fixed_unblock(self.__param["station"]["right"]["virtual"]["line"])

    def go_left(self):
        fixed_node = self.__param["station"]["left"]["virtual"]["ready"]
        mag_node = self.__param["station"]["left"]["mag"]["line"]
        self.__adapter.go_fixed_unblock( fixed_node )
        self.__adapter.wait_fixed( fixed_node )
        self.__adapter.go_mag_unblock( mag_node )
        self.__adapter.wait_mag( mag_node )
        self.__adapter.rotate(-0.4, -math.pi)
        self.__adapter.go_straight(-0.1, -0.1)
        #self.__adapter.go_fixed_unblock(self.__param["station"]["right"]["virtual"]["line"])

        
    def leave_right(self):
        self.__adapter.go_straight(-0.3, -0.3)
        self.__adapter.rotate(-0.4, -math.pi)
        
    def leave_left(self):
        self.__adapter.go_straight(0.3, 0.3)
        
    def stop_line(self):
        self.__adapter.set_one_output(self.__param["control"]["stop_line"], True)
    
    def start_line(self):
        self.__adapter.set_one_output(self.__param["control"]["stop_line"], False)
        
    def io_callback(self, msg):
        for i in self.__sensors:
            self.__sensors[i] = msg[self.__param["sensor"][i]]
      