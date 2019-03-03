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
            
        self.__param = config_data
        
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
        #self.__adapter.get_input_callback(self.__param["sensor"].values(), self.io_callback, 0.1)
        self.__adapter.trigger_button_reset()
        self.__adapter.trigger_button_run()
        # [ TODO ] Make sure localization is correct
        
    def clean_up(self):
        self.__adapter.speed_control(0,0)
        self.__adapter.cancel_all_tasks()
        #self.__adapter.trigger_button_stop()
        self.__adapter.shutdown()
        
    #====== type-specific functions ======#
        
    def face_different(self, station):
        face = self.__param["station"][station]["face"]
        # [ TODO ] Check the spelling error in "face" ("front", "back"). This may lead to bugs
        return (face["ready"] != face["line"])
        
    def face_adapt(self, station):
        face = self.__param["station"][station]["face"]
        face_ready = face["ready"]
        face_line = face["line"]
        if(face_ready == "back"):
            self.__adapter.rotate(-0.4, -math.pi)
        self.__adapter.rotate_find_tape()
        if(face_line == "back"):
            self.go_mag_wait(station, force_direction="FRONT")
            self.__adapter.rotate(-0.4, -math.pi)
            self.__adapter.rotate_find_tape()
        pass
        
    def go_right(self):
        station = "right"
        self.Log.info("go_right()")
        fixed_node = self.__param["station"][station]["virtual"]["ready"]
        self.__adapter.go_fixed_unblock( fixed_node )
        self.__adapter.wait_fixed( fixed_node )
        self.face_adapt(station)
        #if(self.face_different("right")):
        #    self.Log.info("right face different, rotating 180 degrees")
        #    self.__adapter.rotate(-0.4, -math.pi)
        self.go_mag_wait(station)
        
        #self.__adapter.go_fixed_unblock(self.__param["station"]["right"]["virtual"]["line"])

    def go_left(self):
        station = "left"
        self.Log.info("go_left()")
        fixed_node = self.__param["station"][station]["virtual"]["ready"]
        self.__adapter.go_fixed_unblock( fixed_node )
        self.__adapter.wait_fixed( fixed_node )
        self.face_adapt(station)
        #if(self.face_different("left")):
        #    self.Log.info("left face different, rotating 180 degrees")
        #    self.__adapter.rotate(-0.4, -math.pi)
        self.go_mag_wait(station)
        #self.__adapter.rotate(-0.4, -math.pi)
        #self.__adapter.go_straight(-0.1, -0.1)
        #self.__adapter.go_fixed_unblock(self.__param["station"]["right"]["virtual"]["line"])

    def go_mag_wait(self, station, force_turn="", force_direction=""):
        self.Log.info("go_mag_wait(%s)"%(repr(station)))
        station_info = self.__param["station"][station]
        
        mag_node = station_info["mag"]["line"]
        turn = "RIGHT"
        direction = "FRONT" 
        
        if(force_direction):
            direction = force_direction
        else:
            if(station_info["face"]["line"] == "front"):
                direction = "FRONT"
            else: # [ TODO ] Check undefined values and log an error
                direction = "BACK"
        
        self.__adapter.go_mag_unblock( mag_node, turn, direction )
        self.__adapter.wait_mag( mag_node )
        
    def leave_action(self, station):
        station_info = self.__param["station"][station]
        if(station_info["face"]["line"] == "front"):
            self.__adapter.go_straight(-0.3, -0.3)
        else:
            self.__adapter.go_straight(0.3, 0.3)
        
        
    def leave_right(self):
        self.leave_action("right")
        
    def leave_left(self):
        self.leave_action("left")
        
    def stop_line(self):
        self.__adapter.set_one_output(self.__param["control"]["stop_line"], True)
    
    def start_line(self):
        self.__adapter.set_one_output(self.__param["control"]["stop_line"], False)
        
    def io_callback(self, msg):
        for i in self.__sensors:
            self.__sensors[i] = msg[self.__param["sensor"][i]]
      