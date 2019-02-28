import socket
import struct
import time
import json
import sys

from functools import partial

from tcp_client import TcpClient
from messages import *
import threading

# [ TODO ] state monitoring and error detection.
#          auto state prediction (online)

#    1 2 3 4 5
#  1 2 3 4 5  
#  2 3 4 5
#  3 4 5
#  4 5 

class AgvAdapter(object)£º
    def __init__(self):

        self.Log = log_wrap(prefix = "[ Agv Manager ] ")

        self.setSerialize(False)
        self.setPrintHex(False)

        self.__ncol = 10
        
        self.agv_ip = "192.168.0.3"
        
        self.port_info = {
            "state": {
                "port": 8888,
                "client": None,
                "connected": False
            },
            "control": {
                "port": 8889,
                "client": None,
                "connected": False
            },
            "task": {
                "port": 8890,
                "client": None,
                "connected": False
            },
            "config": {
                "port": 8891,
                "client": None,
                "connected": False
            }
        }
        
        self.__connected = False
        
        self.__running = True
        return 

    
    def _print(self, msg):
        print ""
        print msg
        if(self.__print_hex):
            l = len(msg)
            y = l/self.__ncol
            x = l%self.__ncol
            if(x): y += 1
            print "\n".join( map( lambda line: ' '.join( map( lambda c: "%02X"%ord(c), 
                                                              msg[ (line  ) * self.__ncol : 
                                                                   (line+1) * self.__ncol ] ) ) ,
                                  xrange(y) ) )
            pass
        return
            
    def call(self, client, cmd):
        if(self.__serialize):
            cmd = cmd.replace(" ","").replace("\n","").replace("\r","").replace("\t","")
        self._print(cmd)
        res = client.call(cmd)
        self._print(res)
        return res
    
    
    def setSerialize(self, state=True):
        self.__serialize = state
    
    def setPrintHex(self, state=False):
        self.__print_hex = state
        
    def daemon_thread(*args, **kwargs):
        # threads that don't need to be monitored
        t = threading.Thread( *args, **kwargs )
        t.setDaemon(True)
        t.start()
        
    def connect(self):
        self.daemon_thread( target = self.connect_servers )
        
    def set_agv_ip(self, ip):
        self.agv_ip = ip
        
    def set_port(self, ptype, port):
        self.port_info[ptype]["port"] = port
        
    def connect_one_server(self, ptype):

        def connection_loop(ptype):
            port = self.port_info[ptype]["port"]
            while True:
                try:
                    self.port_info[ptype]["client"] = TcpClient(self.agv_ip, port)
                    self.Log.info("[%s] connect %s:%s success.")
                    self.port_info[ptype]["connected"] = True
                    self.update_connected()
                    break
                except Exception as e:
                    self.Log.error("[%s] connect %s:%s failed. Retry...")
                    self.port_info[ptype]["connected"] = False
                    self.update_connected()
                    time.sleep(1)    

        self.daemon_thread( target = connection_loop ,
                            name = ptype,
                            #args = (self.agv) 
                            kwargs = {
                                "ptype": ptype
                            }
                          )
        
    def disconnect_one_server(self,ptype):
        self.port_info[ptype]["client"].close()

    def reconnect_one_server(self,ptype):
        self.disconnect_one_server(ptype)
        self.connect_one_server(ptype)
        
    def update_connected(self):
        self.__connected = (all(map(lambda x:x["connected"],
                                    self.port_info.values())))
        
    def connect_servers(self):
        for ptype in port_info:
            self.connect_one_server( ptype )
        
    def disconnect_servers(self):
        for ptype in port_info:
            self.disconnect_one_server( ptype )
    
    def reconnect_servers(self):
        for ptype in port_info:
            self.reconnect_one_server( ptype )