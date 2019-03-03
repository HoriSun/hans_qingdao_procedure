
from __future__ import print_function

import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp, hooks
from utils import log_wrap
import time


# [ TODO ] Take care of wheel-up / wheel-down.

class StarCommand(object):
    class Move(object):
        STOP = 0
        LEFT = 1
        RIGHT = 2
        
    class Pick(object):
        STOP = 0
        FRAME_1 = 1
        FRAME_2 = 2
        
    class Place(object):
        STOP = 0
        FRAME_1 = 1
        FRAME_2 = 2
    
    class Button(object):
        NONE = 0
        START = 1
        STOP = 2
        
class StarState(object):
    class AgvStation(object):
        UNKNOWN = 0
        LEFT = 1
        RIGHT = 2

    class InitState(object):
        UNINITIALIZED = 0
        READY = 1
        
    def __init__(self):
        self.response_move = 0
        self.response_place = 0
        self.response_pick = 0
        self.response_button = 0
        self.agv_position = StarState.AgvStation.UNKNOWN
        self.init_state_elfin = StarState.InitState.UNINITIALIZED
        self.init_state_agv = StarState.InitState.UNINITIALIZED

    def debug_output(self):
        self.Log.info("[ star state ] response_move = %s"%(self.response_move))
        self.Log.info("[ star state ] response_place = %s"%(self.response_place))
        self.Log.info("[ star state ] response_pick = %s"%(self.response_pick))
        self.Log.info("[ star state ] response_button = %s"%(self.response_button))
        self.Log.info("[ star state ] agv_position = %s"%(self.agv_position))
        self.Log.info("[ star state ] init_state_elfin = %s"%(self.init_state_elfin))
        self.Log.info("[ star state ] init_state_agv = %s"%(self.init_state_agv))
        
class StarRegister(object):
    class HoldingRegister(object):
        # Holding registers
        MOVE = 0
        PLACE = 1
        PICK = 2
        BUTTON = 3
            
    class InputRegister(object):
        ELFIN_ERROR = 0
        AGV_STATION = 2

        
        
class StarAdapter(object):

    def __init__(self, ip="127.0.0.1", port=502):
        self.Log = log_wrap(prefix = "[ Star Adapter ]")
        self.master = None
        self.ip = ip
        self.port = port
        self.__running = True
        self.__updating_state = False
        self.__update_state_thread = None
        
        self.__star_state = StarState()
        pass
        
    def reconfigure(self, ip, port):
        self.ip = ip
        self.port = port
        
    # [ TODO ] Need reconnection
    def connect(self):
        # Connect to the slave
        while (self.__running):
            try:
                self.master = modbus_tcp.TcpMaster( host = self.ip ,
                                                    port = self.port ,
                                                    timeout = 5.0 )
                self.master.set_timeout(5.0)
                self.Log.info("Star modbus connection established.")
                break
            except modbus_tk.modbus.ModbusError as exc:
                self.Log.error("Failed connecting Star, try reconnecting")
                time.sleep(1)

    def init(self):
        self.start_update_state()
                
    def clean_up(self):
        self.__running = False
        self.stop_update_state()
                
    # logger.info(master.execute(1, cst.READ_COILS, 0, 10))
    # logger.info(master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8))
    # logger.info(master.execute(1, cst.READ_INPUT_REGISTERS, 100, 3))
    # logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 12))
    # logger.info(master.execute(1, cst.WRITE_SINGLE_COIL, 7, output_value=1))
    # logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))
    # logger.info(master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1, 0, 1, 1]))
    # logger.info(master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12)))
        
            
    def write_bit_one(self, addr, value):
        msg = self.master.execute(1, cst.WRITE_SINGLE_COIL, addr, output_value=value)
        self.Log.info(msg)
    
    def write_bit_multi(self, addr, values):
        msg = self.master.execute(1, cst.WRITE_MULTIPLE_COILS, addr, output_value=value)
        self.Log.info(msg)
    
    def write_byte_one(self, addr, value):
        msg = self.master.execute(1, cst.WRITE_SINGLE_REGISTER, addr, output_value=value)
        self.Log.info(msg)
    
    def write_byte_multi(self, addr, values):
        msg = self.master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, addr, output_value=value)
        self.Log.info(msg)
    
    # read coils
    def read_bit_rw(self, addr, number):
        msg = self.master.execute(1, cst.READ_COILS, addr, output_value=value)
        self.Log.info(msg)
    
    # read discrete inputs
    def read_bit_r(self, addr, number):
        msg = self.master.execute(1, cst.READ_DISCRETE_INPUTS, addr, output_value=value)
        self.Log.info(msg)
    
    # read holding registers
    def read_byte_rw(self, addr, number):
        msg = self.master.execute(1, cst.READ_HOLDING_REGISTERS, addr, output_value=value)
        self.Log.info(msg)
    
    # read input registers
    def read_byte_r(self, addr, number):
        msg = self.master.execute(1, cst.READ_INPUT_REGISTERS, addr, output_value=value)
        self.Log.info(msg)
    
    def __move(self, command):
        self.write_byte_one( StarRegister.HoldingRegister.MOVE, command )
        
    def move_station(self, station):
        self.__move(station)
        
    def move_stop(self):
        self.__move(StarCommand.Move.STOP)

    def __place(self, command):
        self.write_byte_one( StarRegister.HoldingRegister.Place, command )
        
    def place_material(self, material):
        self.__place(material)
        
    def place_stop(self):
        self.__place(StarCommand.Place.STOP)

    def __pick(self, command):
        self.write_byte_one( StarRegister.HoldingRegister.PICK, command )
        
    def pick_material(self, material):
        self.__pick(material)
        
    def pick_stop(self):
        self.__pick(StarCommand.Pick.STOP)

    def __trigger_button(self, command):
        self.write_byte_one( StarRegister.HoldingRegister.BUTTON, command )
        
    def trigger_button(self, button):
        self.__trigger_button(button)
        
    def trigger_button_none(self):
        self.__trigger_button( StarCommand.Button.NONE )
    
    def trigger_button_start(self):
        self.__trigger_button( StarCommand.Button.START )
    
    def trigger_button_stop(self):
        self.__trigger_button( StarCommand.Button.STOP )
    
    def trigger_button_initialize(self):
        self.__trigger_button( StarCommand.Button.INITIALIZE )
    
    def update_state(self):
        (
          self.__star_state.response_move ,
          self.__star_state.response_place ,
          self.__star_state.response_pick ,
          self.__star_state.response_button ,
        ) = read_byte_r(0,4)
        
        self.__star_state.agv_position = read_byte_r(19,1)
        
        self.__star_state.init_state_elfin = read_bit_r(0,1)
        self.__star_state.init_state_agv = read_bit_r(1,1)
        
        self.Log.info("="*30)
        self.__star_state.debug_output()
        
    def update_state_loop(self):
        self.__updating_state = True
        while(self.__running and self.__updating_state):
            self.update_state()
            time.sleep(0.1)
            
    def start_update_state(self):
        if(self.__updating_state):
            return
        self.__update_state_thread = threading.Thread( target = update_state_loop )
        self.__update_state_thread.setDaemon(True)
        self.__update_state_thread.start()
        
    def stop_update_state(self):
        if(not self.__updating_state):
            return
        self.__updating_state = False
        self.__update_state_thread.join()
        self.__update_state_thread = None
    
def main():
    """main"""
#    logger = modbus_tk.utils.create_logger("console", level=logging.DEBUG)

    def on_after_recv(data):
        master, bytes_data = data
#        logger.info(bytes_data)

    hooks.install_hook('modbus.Master.after_recv', on_after_recv)

    try:

        def on_before_connect(args):
            master = args[0]
#            logger.debug("on_before_connect {0} {1}".format(master._host, master._port))

        hooks.install_hook("modbus_tcp.TcpMaster.before_connect", on_before_connect)

        def on_after_recv(args):
            response = args[1]
#            logger.debug("on_after_recv {0} bytes received".format(len(response)))

        hooks.install_hook("modbus_tcp.TcpMaster.after_recv", on_after_recv)

        # Connect to the slave
        master = modbus_tcp.TcpMaster()
        master.set_timeout(5.0)
#        logger.info("connected")

#        logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 0, 3))

        # logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 0, 2, data_format='f'))

        # Read and write floats
        # master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, starting_address=0, output_value=[3.14], data_format='>f')
        # logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 0, 2, data_format='>f'))

        # send some queries
        # logger.info(master.execute(1, cst.READ_COILS, 0, 10))
        # logger.info(master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8))
        # logger.info(master.execute(1, cst.READ_INPUT_REGISTERS, 100, 3))
        # logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 12))
        # logger.info(master.execute(1, cst.WRITE_SINGLE_COIL, 7, output_value=1))
        # logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))
        # logger.info(master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1, 0, 1, 1]))
        # logger.info(master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12)))

    except modbus_tk.modbus.ModbusError as exc:
        pass
 #       logger.error("%s- Code=%d", exc, exc.get_exception_code())

if __name__ == "__main__":
    #main()
    pass
