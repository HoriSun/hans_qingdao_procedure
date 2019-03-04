from utils import log_wrap, check_ip_correct, angle_diff, abs
from json_proc import dumps_json
from agv_adapter import AgvAdapter
import math
import time
import threading

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
            "detect_front": 0,
            "detect_middle": 0,
            "detect_back": 0
        }
        
        self.__position = {
            "x": 0,
            "y": 0,
            "theta": 0
        }
        
        self.__going_unblock = False
        self.__go_unblock_thread = None
        
        self.__running = True
        self.__map_nodes = {}
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
                "start_line": 4
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
        self.get_map_nodes()
        self.__adapter.get_input_callback_start(self.__param["sensor"].values(), 
                                                self.io_callback)
        self.__adapter.trigger_button_reset()
        self.__adapter.trigger_button_run()
        self.__adapter.start_monitor_state(callback = self.agv_state_callback)
        # [ TODO ] Make sure localization is correct
        
    def clean_up(self):
        self.__running = False
        self.__adapter.speed_control(0,0)
        self.__adapter.cancel_all_tasks()
        self.__adapter.get_input_callback_stop()
        #self.__adapter.trigger_button_stop()
        self.__adapter.stop_monitor_state()
        self.__adapter.shutdown()
        
    #====== type-specific functions ======#
        
    def face_different(self, station):
        face = self.__param["station"][station]["face"]
        # [ TODO ] Check the spelling error in "face" ("front", "back"). This may lead to bugs
        return (face["ready"] != face["line"])
        
    def face_adapt(self, station, interruptor):
        face = self.__param["station"][station]["face"]
        face_ready = face["ready"]
        face_line = face["line"]
        if(face_ready == "back"):
            self.__adapter.rotate(-0.4, -math.pi)
        self.__adapter.rotate_find_tape()
        if(face_line == "back"):
            self.go_mag_wait(station, interruptor, force_direction="FRONT")
            self.__adapter.rotate(-0.4, -math.pi)
            self.__adapter.rotate_find_tape()
        pass
        
    def __go_station(self, station, interruptor):
        self.Log.info("__go_station(\"%s\")"%(station))
        fixed_node = self.__param["station"][station]["virtual"]["ready"]
        
        if(interruptor.check()):
            return
        
        self.__adapter.go_fixed_unblock( fixed_node )
        
        if(interruptor.check()):
            self.__adapter.cancel_all_tasks()
            return
        
        self.__adapter.wait_fixed( fixed_node, interruptor )
        self.face_adapt(station, interruptor)
        #if(self.face_different("left")):
        #    self.Log.info("left face different, rotating 180 degrees")
        #    self.__adapter.rotate(-0.4, -math.pi)
        self.go_mag_wait(station, interruptor)
        #self.__adapter.rotate(-0.4, -math.pi)
        #self.__adapter.go_straight(-0.1, -0.1)
        #self.__adapter.go_fixed_unblock(self.__param["station"]["right"]["virtual"]["line"])
        
    def go_unblock(self, station, interruptor):
        if(station in ["left","right"]):
            self.__go_station(interruptor)
        else:
            self.Log.error("go_unblock(): Undefined station name: %s"%(station))
            
    def is_at_station(self, station):
        pose_map = lambda x:(x["x"],x["y"],x["theta"])
        diff = lambda x,y:(x[i]-y[i] for i in xrange(len(x)))
        norm = lambda a:math.sqrt(reduce(lambda x,y:x+y,map(lambda z:z*z,a)))
        distance_threshold = 0.05
        
        station_pose = pose_map(self.__map_nodes[station])
        agv_pose = pose_map(self.__position)
        
        
        
        
        self.Log.info("[is_at_station] station %s pose:  ( % 7.5lf, % 7.5lf, % 7.5lf, )"
                      ""%((station,)+station_pose))
        self.Log.info("[is_at_station] agv pose:  ( % 7.5lf, % 7.5lf, % 7.5lf, )"
                      ""%agv_pose)
        
        d_position = norm(diff(station_pose[:2], agv_pose[:2]))
        d_angle = abs(angle_diff(station_pose[2], agv_pose[2]))
        
        return d_position <= distance_threshold, d_position, d_angle 
        
    def go_unblock_reached(self, station):
        pass
        
    def go_unblock_start(self, station):
        self.__going_unblock = True
        interruptor = TaskInterruptor([self.__going_unblock])
        self.__go_unblock_thread = threading.Thread( target = self.go_unblock,
                                                     args = (station, interruptor) )
        self.__go_unblock_thread.setDaemon(True)
        self.__go_unblock_thread.start()
        
    def go_unblock_stop(self):
        self.__going_unblock = False
        self.__go_unblock_thread.join()
        self.__go_unblock_thread = None
        
    def go_mag_wait(self, station, interruptor, force_turn="", force_direction=""):
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

        if(interruptor.check()):
            self.__adapter.cancel_all_tasks()
            return

            self.__adapter.wait_mag( mag_node, interruptor )
        
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
        self.__adapter.set_one_output(self.__param["control"]["start_line"], False)
    
    def start_line(self):
        self.__adapter.set_one_output(self.__param["control"]["start_line"], True)
        
    def io_callback(self, msg):
        for i in self.__sensors:
            #print msg
            self.__sensors[i] = 1 if msg[self.__param["sensor"][i]] else 0
      
    def wait_sensor_state(self, sensor, state):
        state = 1 if state else 0
        while((self.__running) and
              (self.__sensors["detect_%s"%(sensor)] != state)):
            #print self.__sensors
            #print "detect_%s"%(sensor)
            #print state
            time.sleep(0.1)
    
    def get_map_nodes(self):
        m = self.__adapter.get_map()
        
        #self.Log.info( m.keys() )
        nodes = m["nodes"]
        
        for n in nodes:
            name = n["name"]
            x = n["pos"]["x"]
            y = n["pos"]["y"]
            theta = n["pos"]["theta"]
            self.__map_nodes[name] = {"x":x, "y":y, "theta":theta}
            self.Log.info("map node [ % 2s ]  x( % 7.5lf )  y( % 7.5lf )  "
                          "theta( % 7.5lf )"%(name,x,y,theta))
        
    def get_position(self, agv_state):
        #( self.__position["x"] ,
        #  self.__position["y"] ,
        #  self.__position["theta"] ) = self.__adapter(get_position())
        self.Log.info("get_position()")
        self.__position["x"] = agv_state["x"]
        self.__position["y"] = agv_state["y"] 
        self.__position["theta"] = agv_state["angle"]
         
          
    def agv_state_callback(self, msg):
        self.Log.info("agv_state_callback()")
        self.__agv_state = msg
        self.get_position(self.__agv_state)