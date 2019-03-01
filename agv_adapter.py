import socket
import struct
import time
import json
import sys
import math

from functools import partial

from tcp_client import TcpClient
from messages import *
import threading

from utils import log_wrap, angle_diff, abs
from json_proc import loads_json

# [ TODO ] state monitoring and error detection.
#          auto state prediction (online)

#    1 2 3 4 5
#  1 2 3 4 5  
#  2 3 4 5
#  3 4 5
#  4 5 


class AgvAdapter(object):
    def __init__(self):

        self.Log = log_wrap(prefix = "[ Agv Adapter ] ")

        self.setSerialize(False)
        self.setPrintHex(False)

        self.__ncol = 10
        
        self.agv_ip = "192.168.0.3"
        
        self.port_info = {
            "state": {
                "port": 8888,
                "client": None,
                "connected": False,
                "connect_thread": None,
                "want_connect": False
            },
            "control": {
                "port": 8889,
                "client": None,
                "connected": False,
                "connect_thread": None,
                "want_connect": False
            },
            "task": {
                "port": 8890,
                "client": None,
                "connected": False,
                "connect_thread": None,
                "want_connect": False
            },
            "config": {
                "port": 8891,
                "client": None,
                "connected": False,
                "connect_thread": None,
                "want_connect": False
            }
        }
        
        self.__connected = False
        
        self.__running = True
        
        self.__agv_state = None
        self.__monitoring = False
        self.__monitoring_internal = 0
        self.__monitoring_external = 0
        self.__monitor_data_recv = False
        self.state_monitor_thread = None
        return 

    def shutdown(self):
        self.__running = False
    
    def _print(self, msg, prefix=""):
        print_msg = msg
        if(prefix):
            print_msg = prefix + msg 
        for m in print_msg.split("\n"):
            self.Log.info(m)
        if(self.__print_hex):
            l = len(msg)
            y = l/self.__ncol
            x = l%self.__ncol
            if(x): y += 1
            msg = "\n".join( map( lambda line: ' '.join( map( lambda c: "%02X"%ord(c), 
                                                              msg[ (line  ) * self.__ncol : 
                                                                   (line+1) * self.__ncol ] ) ) ,
                                  xrange(y) ) )
            for m in msg.split("\n"):
                self.Log.info(m)
            pass
        return
    
    
    def call(self, client, cmd):
        if(self.__serialize):
            cmd = cmd.replace(" ","").replace("\n","").replace("\r","").replace("\t","")
        self._print(cmd, prefix="[ ->]: ")
        res = client.call(cmd)
        self._print(res, prefix="[<- ]: ")
        return res
    
    
    def setSerialize(self, state=True):
        self.__serialize = state
    
    def setPrintHex(self, state=False):
        self.__print_hex = state
        
    def daemon_thread( group=None, target=None, name="", args=(),
                       kwargs={}, verbose=None ):
        # threads that don't need to be monitored
        t = threading.Thread( group=None, name=name, target=target, 
                              args=args, kwargs=kwargs, 
                              verbose=verbose )
        t.setDaemon(True)
        t.start()
        
        return t
        
    def connect(self):
        return self.daemon_thread( target = self.connect_servers )
        
    def set_agv_ip(self, ip):
        self.agv_ip = ip
        
    def set_port(self, ptype, port):
        self.port_info[ptype]["port"] = port
        
    def connect_one_server(self, ptype):

        def connection_loop(ptype):
            port = self.port_info[ptype]["port"]
            while self.__running and self.port_info[ptype]["want_connect"]:
                try:
                    self.port_info[ptype]["client"] = TcpClient(self.agv_ip, port)
                    self.Log.info("[%s] connect %s:%s success."
                                  ""%(ptype, self.agv_ip, port))
                    self.port_info[ptype]["connected"] = True
                    self.update_connected()
                    break
                except Exception as e:
                    self.Log.error("[%s] connect %s:%s failed. Retry..."
                                   ""%(ptype, self.agv_ip, port))
                    self.port_info[ptype]["connected"] = False
                    self.update_connected()
                    time.sleep(1)    

        self.port_info[ptype]["want_connect"] = True
        return self.daemon_thread( target = connection_loop ,
                                   name = ptype,
                                   #args = (self.agv) 
                                   kwargs = {
                                       "ptype": ptype
                                   }
                                 )
                
    def disconnect_one_server(self,ptype):
        self.port_info[ptype]["client"].close()
        self.port_info[ptype]["want_connect"] = False
        self.port_info[ptype]["connect_thread"].join()

    def reconnect_one_server(self,ptype):
        self.disconnect_one_server(ptype)
        self.connect_one_server(ptype)
        
    def update_connected(self):
        self.__connected = (all(map(lambda x:x["connected"],
                                    self.port_info.values())))
        
    def connect_servers(self):
        for ptype in self.port_info:
            self.connect_one_server( ptype )
        
    def disconnect_servers(self):
        for ptype in self.port_info:
            self.disconnect_one_server( ptype )
    
    def reconnect_servers(self):
        for ptype in self.port_info:
            self.reconnect_one_server( ptype )
            
    def wait_for_connection(self):
        while(not self.__connected):
            time.sleep(0.3)
            
    
    
    def trigger_button_reset(self):
        return self.call( self.port_info["control"]["client"], soft_button('RESET') )
    
    def trigger_button_run(self):
        return self.call( self.port_info["control"]["client"], soft_button('RUN') )

    def trigger_button_stop(self):
        return self.call( self.port_info["control"]["client"], soft_button('STOP') )

    def switch_auto(self):
        return self.call( self.port_info["control"]["client"], change_mode_auto )

    def switch_manual(self):
        return self.call( self.port_info["control"]["client"], change_mode_manual )

    def cancel_all_tasks(self):
        return self.call( self.port_info["task"]["client"], cancel_task )

    
    def go_fixed_block(self,node):
        self.go_fixed_unblock(node)
        self.wait_fixed(node)
        
    def go_fixed_unblock(self,node):
        self.trigger_button_run()
        self.switch_auto()

        return self.call( self.port_info["task"]["client"], add_target_task(node) )
        

    # [ TODO ] Should stop and report error when the task failed
    def wait_task(self, target_func):
    
        self.__start_monitor_state_internal()
    
        while(not self.__monitor_data_recv):
            time.sleep(0.1)
    
        while(self.__running):
            state__ = self.__agv_state["taskState"]
            if(state__ == 'FINISHED'):
                if(target_func()):
                    self.cancel_all_tasks()
                    break
            elif(state__ == 'PREEMPTED'):
                pass
                #print(self.task_client.call(cmd))
                #elif(state__ == 'FAILED'):
                #    self.task_client.call(cmd__)
                #    continue
            else:
                time.sleep(0.3)
                continue
        else:
            self.cancel_all_tasks()        

        self.__stop_monitor_state_internal()
    
    
    def wait_fixed(self, node=""):
        def target_f():
            ret = True
            ret &= (self.__agv_state["controlMode"] == "FIXED_TRACK")
            ret &= (self.__agv_state["virtualNode"] == self.__agv_state["taskTargetVirtual"])
            if(node):
                ret &= (self.__agv_state["virtualNode"] == str(node)) # adapt to possible type (int)
            return ret
        self.wait_task(target_f)
    
    def go_mag_block(self,rfid):
        self.go_mag_unblock(rfid)
        self.wait_mag(rfid)

    def go_mag_unblock(self,rfid):
        self.trigger_button_run()
        
        self.rotate_find_tape()
        
        self.switch_auto()

        return self.call( self.port_info["task"]["client"], add_mag_task(rfid) )

    
    def wait_mag(self, node=-1):
        def target_f():
            ret = True
            ret &= (self.__agv_state["controlMode"] == "MAG")
            ret &= (self.__agv_state["magNode"] == self.__agv_state["taskTargetMag"])
            if(node!=-1):
                ret &= (self.__agv_state["magNode"] == int(node))
            return ret
        self.wait_task(target_f)
    
    
    def get_state(self, key=""):
        #res__ = self.call( self.port_info["state"]["client"], get_state )
        res__ = self.port_info["state"]["client"].call( get_state )
        try:
            data = loads_json(res__)['data']
            
            if(not key):
                return data
            else:
                return data[key]
        
        except Exception as e:
            self.Log.error("state response JSON extraction failed: %s"%(e))
            return None
            
    
    def start_monitor_state(self):
        self.__monitoring_external += 1
        self.__start_monitor_state_impl()
    
    def stop_monitor_state(self):
        self.__monitoring_external -= 1
        self.__stop_monitor_state_impl()
    
    def __start_monitor_state_internal(self):
        self.__monitoring_internal += 1
        self.__start_monitor_state_impl()
    
    def __stop_monitor_state_internal(self):
        self.__monitoring_internal -= 1
        self.__stop_monitor_state_impl()
    
    def __start_monitor_state_impl(self):
        
        
        if(self.__monitoring_internal<0):
            self.__monitoring_internal = 0
            self.Log.error("self.__monitoring_internal < 0 happens. Bugs exist.")
        
        if(self.__monitoring_external<0):
            self.__monitoring_external = 0
            self.Log.error("self.__monitoring_external < 0 happens. Bugs exist.")
        
        if not (self.__monitoring_external or 
                self.__monitoring_internal):
            return
        
        if(self.__monitoring):
            return
        
        def monitor_state_loop():
            while(self.__running and self.__monitoring):
                agv_state = self.get_state()
                if(agv_state):
                    self.__agv_state = agv_state
                self.__monitor_data_recv = True
                time.sleep(0.2)
        
        self.__monitoring = True
        self.state_monitor_thread = self.daemon_thread( target = monitor_state_loop ,
                                                        name = "monitor_state_loop" )
        
    def __stop_monitor_state_impl(self):
    
        if (self.__monitoring_external or 
            self.__monitoring_internal):
            return
    
        self.__monitoring = False
        self.__monitor_data_recv = False
        if(self.state_monitor_thread):
            self.state_monitor_thread.join()
        self.state_monitor_thread = None
        
        
    def speed_control(self, v, w):
        return self.call( self.port_info["control"]["client"], robot_motion(v,0,w) )
    
    def go_straight(self, v, d):
    
        self.trigger_button_run()
        self.switch_manual()
        
        if(v == 0):
            self.speed_control(0,0)
            return
    
        #sign = lambda x:x if x==0 else x/x
        
    
        #sgn_d = sign(d)
        abs_d = abs(d)
    
        #v = v * sgn_d
    
        if(abs_d <= 1e-3):
            self.Log.warn("Move distance too short. Do nothing.")
            return
    
        self.__start_monitor_state_internal()
        
        while(not self.__monitor_data_recv):
            time.sleep(0.1)

        ori_x = self.__agv_state["x"]
        ori_y = self.__agv_state["y"]
        
        self.speed_control(v,0)
                
        while(self.__running):
            x = self.__agv_state["x"]
            y = self.__agv_state["y"]
            dx = x - ori_x
            dy = y - ori_y
            dp = math.sqrt(dx*dx+dy*dy)
            if(dp >= abs_d):
                self.speed_control(0,0)
                break
        
        self.__stop_monitor_state_internal()
    
    
    
    def rotate(self, w, a):
        
        self.trigger_button_run()
        self.switch_manual()
        
        if(w == 0):
            self.speed_control(0,0)
            return
    
        #sign = lambda x:x if x==0 else x/x
        
    
        #sgn_d = sign(d)
        abs_a = abs(a)
    
        #v = v * sgn_d
    
        if(abs_a <= math.pi/180.0/10.0):
            self.Log.warn("Move angle too small. Do nothing.")
            return
    
        self.__start_monitor_state_internal()
        
        while(not self.__monitor_data_recv):
            time.sleep(0.1)

        ori_angle = self.__agv_state["angle"]
        
        self.speed_control(0,w)
                
        while(self.__running):
            angle = self.__agv_state["angle"]
            dangle = angle_diff( angle, ori_angle )
            #self.Log.warn("oria [%lf]   a [%lf]   da [%lf]  funa [%lf]"%(ori_angle, angle, dangle, a))
            
            if(abs( abs(dangle) - abs_a ) <= 0.1):
                self.speed_control(0,0)
                break
        
        self.__stop_monitor_state_internal()

    
    def rotate_find_tape( self, 
                          angle_range = 10/180.0*math.pi, 
                          angular_speed = 0.1,
                          angle_tolerance = 0.01,
                          check_duration = 0.1 ):
                                
        angle_ori = 0.0
                        
        self.__start_monitor_state_internal()
        
        while(not self.__monitor_data_recv):
            time.sleep(0.1)

        track_found = False

        if(not self.__agv_state["onMagTrack"]):
            track_found = False
            angle_ori = self.__agv_state["angle"]
            self.switch_manual()

            for dend, dspeed in [[ -1*angle_range, -1 ],
                                 [  2*angle_range,  1 ],
                                 [ -1*angle_range, -1 ]]:
                self.speed_control( 0, angular_speed * dspeed )
                
                dangle = angle_diff( self.__agv_state["angle"], angle_ori )
                while( angle_diff(dangle, dend) > angle_tolerance ):
                    if (self.__agv_state["onMagTrack"]):
                        self.speed_control( 0, 0 )
                        track_found = True
                        break
                        pass # if
                    time.sleep(check_duration)
                    pass # while
                if(track_found):
                    break
                pass # for

            self.speed_control( 0, 0 )
            self.switch_auto()
            pass # if not 
        else:
            track_found = True
            pass # else
            
       
        self.__stop_monitor_state_internal()
        
        return track_found

        
    def play_sound(self, sound_id, repeat_time):
        return self.call( self.port_info["control"]["client"], sound(sound_id, repeat_time) )
        
    
    def set_idle(self):
        return self.call( self.port_info["task"]["client"], switch_to_idle )
    
    def set_one_output(self, index, switch):
        if(isinstance(switch, str)):
            assert switches in ['true','false']
        if(isinstance(switch, int)):
            switch = bool(switch)
        return self.call( self.port_info["control"]["client"], set_output(index, switch) )
    
    # set outputs one by one
    def set_output_one_by_one(self, indexes, switches):
        for index,switch in zip(indexes, switches):
            self.set_one_output(index, switch)

    def get_one_input(self, index):
        return self.call( self.port_info["state"]["client"], get_input(index) )
            
    def get_input_one_by_one(self, indexes):
        ret = {}
        for index in indexes:
            while(self.__running):
                try:
                    __res = get_one_intput(index)
                    data = json.loads(__res)["data"]
                    state = data["state"]
                    break
                except Exception as e:
                    self.Log.error("Get DI #%d state failed. Retry..."
                                   ""%(index))
                    time.sleep(0.2)
            ret[index] = state
        return ret
    
    def get_input_callback(self, indexes, f, sleep_time):
        while(self.__running):
            f(self.get_input_one_by_one(indexes))
            time.sleep(sleep_time)
            
        