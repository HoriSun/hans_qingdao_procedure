
from __future__ import print_function

import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp, hooks
from utils import log_wrap
import time
import threading


# [ TODO ] Take care of wheel-up / wheel-down.

class StarCommand(object):
    '''
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
    '''
    class AgvTask(object):
        NO_TASK = 0
        GO = 1

    class AgvTaskStation(object):
        UNKNOWN = 0
        READY = 1
        PLACE = 2
        PICK = 3

    class ElfinTask(object):
        NO_TASK = 0
        READY = 1
        PLACE_TRIANGLE = 2
        PLACE_SQUARE = 3
        PICK_TRIANGLE = 4
        PICK_SQUARE = 5

        
class StarState(object):
    class AgvStation(object):
        UNKNOWN = 0
        PLACE = 1
        PICK = 2

    class InitState(object):
        UNINITIALIZED = 0
        READY = 1

    class TaskState(object):
        NO_TASK = 0
        FINISHED = 1
        RUNNING = 2
        ERROR = 255
        
    def __init__(self):
        self.Log = log_wrap( prefix = "[ Star State ] ")
        #self.response_move = 0
        #self.response_place = 0
        #self.response_pick = 0
        #self.response_button = 0
        #self.agv_position = StarState.AgvStation.UNKNOWN
        #self.init_state_elfin = StarState.InitState.UNINITIALIZED
        #self.init_state_agv = StarState.InitState.UNINITIALIZED

        self.elfin_task_id = 0
        self.elfin_task    = 0
        self.elfin_task_param_0 = 0
        self.elfin_task_param_1 = 0
        self.elfin_task_status = 0

        self.agv_task_id = 0
        self.agv_task    = 0
        self.agv_task_param_0 = 0
        self.agv_task_param_1 = 0
        self.agv_task_status = 0


    def debug_output(self):
        #self.Log.info("[ star state ] response_move = %s"%(self.response_move))
        #self.Log.info("[ star state ] response_place = %s"%(self.response_place))
        #self.Log.info("[ star state ] response_pick = %s"%(self.response_pick))
        #self.Log.info("[ star state ] response_button = %s"%(self.response_button))
        #self.Log.info("[ star state ] agv_position = %s"%(self.agv_position))
        #self.Log.info("[ star state ] init_state_elfin = %s"%(self.init_state_elfin))
        #self.Log.info("[ star state ] init_state_agv = %s"%(self.init_state_agv))

        self.Log.info(" elfin_task_id = %s"%(self.elfin_task_id))
        self.Log.info(" elfin_task = %s"%(self.elfin_task))
        self.Log.info(" elfin_task_param_0 = %s"%(self.elfin_task_param_0))
        self.Log.info(" elfin_task_param_1 = %s"%(self.elfin_task_param_1))
        self.Log.info(" elfin_task_status = %s"%(self.elfin_task_status))

        self.Log.info(" agv_task_id = %s"%(self.agv_task_id))
        self.Log.info(" agv_task = %s"%(self.agv_task))
        self.Log.info(" agv_task_param_0 = %s"%(self.agv_task_param_0))
        self.Log.info(" agv_task_param_1 = %s"%(self.agv_task_param_1))
        self.Log.info(" agv_task_status = %s"%(self.agv_task_status))

        
class StarRegister(object):
    class HR(object):
        # Holding registers

        #MOVE = 0
        #PLACE = 1
        #PICK = 2
        #BUTTON = 3

        ELFIN_TASK_ID = 0
        ELFIN_TASK    = 1
        ELFIN_TASK_PARAM_0 = 2
        ELFIN_TASK_PARAM_1 = 3

        AGV_TASK_ID = 4
        AGV_TASK    = 5
        AGV_TASK_PARAM_0 = 6
        AGV_TASK_PARAM_1 = 7
            
    class IR(object):
        # Input registers

        #ELFIN_ERROR = 0
        #AGV_STATION = 2

        ELFIN_TASK_ID = 0
        ELFIN_TASK    = 1
        ELFIN_TASK_PARAM_0 = 2
        ELFIN_TASK_PARAM_1 = 3
        ELFIN_TASK_STATUS = 4

        AGV_TASK_ID = 5
        AGV_TASK    = 6
        AGV_TASK_PARAM_0 = 7
        AGV_TASK_PARAM_1 = 8
        AGV_TASK_STATUS = 9
        
        
        
class StarAdapter(object):

    def __init__(self, 
                 ip="127.0.0.1", port=502, 
                 log_message = False):
        self.Log = log_wrap(prefix = "[ Star Adapter ]")
        self.master = None
        self.ip = ip
        self.port = port
        self.__log_message = log_message
        self.__modbus_lock = threading.Lock()
        
        self.__state_history = None

        self.__connected = False
        self.__connecting = False
        self.__need_connection = False
        self.__connect_thread = None

        self.__running = True
        self.__updating_state = False
        self.__update_state_thread = None
        
        self.__star_state = StarState()
        pass
        
    def reconfigure(self, ip, port, log_message=False):
        self.ip = ip
        self.port = port
        self.__log_message = log_message

    # [ TODO ] Need reconnection
    def connect(self):
        if(self.__connected):
            self.Log.info("connect(): Star Modbus slave connected. Do nothing.")
            return
            
        if(self.__connecting):
            self.Log.info("connect(): Already connecting Star Modbus slave. Do nothing.")
            return

        self.Log.info("connect(): Start connection thread.")
            
        self.__need_connection = True
        self.__connect_thread = threading.Thread(target = self.__connect_loop)
        self.__connect_thread.setDaemon(True)
        self.__connect_thread.start()
        
        
    def disconnect(self):
        if(not self.__connected):
            self.Log.info("disconnect(): Star Modbus slave not connected. Do nothing.")
            return

        if(self.__connecting):
            self.__connecting = False

        if(self.__connect_thread):
            self.__connect_thread.join()
            self.__connect_thread = None

        if(self.master):
            self.master.close()


    def wait_for_connection(self):
        self.Log.info("Waiting for connection...")
        while(self.__running):
            if(self.__connected):
                break
            else:
                time.sleep(0.1)
        

    def __connect_loop(self):
        self.__connecting = True
        # Connect to the slave
        while (self.__running and self.__need_connection):
            try:
                self.Log.info("Try connecting to %s:%s"%(self.ip, self.port))
                self.master = modbus_tcp.TcpMaster( host = self.ip ,
                                                    port = self.port ,
                                                    timeout_in_sec = 5.0 )
                self.master.set_timeout(5.0)

                self.master.open()
                self.Log.info("Star modbus connection established.")
                self.__connected = True
                self.__connecting = False
                self.__need_connection = False
                break
            except modbus_tk.modbus.ModbusError as exc:
                self.Log.error("Failed connecting Star, try reconnecting")
                time.sleep(1)

    def init(self):
        self.start_update_state()
                
    def clean_up(self):
        self.__running = False
        self.stop_update_state()
        self.disconnect()
                
    # logger.info(master.execute(1, cst.READ_COILS, 0, 10))
    # logger.info(master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8))
    # logger.info(master.execute(1, cst.READ_INPUT_REGISTERS, 100, 3))
    # logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 12))
    # logger.info(master.execute(1, cst.WRITE_SINGLE_COIL, 7, output_value=1))
    # logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))
    # logger.info(master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1, 0, 1, 1]))
    # logger.info(master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12)))
        
    
    def write(self, slave_id, mode, addr, output_value):
        try:
            self.__modbus_lock.acquire()
            msg = self.master.execute( slave_id, mode, 
                                       addr, output_value = output_value )
            self.__modbus_lock.release()
            if(self.__log_message):
                self.Log.info("Reply: %s"%(repr(msg)))
            return msg
        except modbus_tk.modbus.ModbusError as exc:
            self.Log.error("Execution failed: "
                           "slave[%d], mode[%d], "
                           "addr[%d], output_value[%s]"
                           ""%(slave_id,
                               mode,
                               addr,
                               output_value))
            return None


    def read(self, slave_id, mode, addr, number):
        try:
            self.__modbus_lock.acquire()
            msg = self.master.execute( slave_id, mode, 
                                       addr, number )
            self.__modbus_lock.release()
            if(self.__log_message):
                self.Log.info("Reply: %s"%(repr(msg)))
            return msg
        except modbus_tk.modbus.ModbusError as exc:
            self.Log.error("Execution failed: "
                           "slave[%d], mode[%d], "
                           "addr[%d], output_value[%s]"
                           ""%(slave_id,
                               mode,
                               addr,
                               output_value))
            return None


            
    def write_bit_one(self, addr, value):
        return self.write(1, cst.WRITE_SINGLE_COIL, addr, output_value=value)
        
    
    def write_bit_multi(self, addr, values):
        return self.write(1, cst.WRITE_MULTIPLE_COILS, addr, output_value=value)
        
    
    def write_byte_one(self, addr, value):
        return self.write(1, cst.WRITE_SINGLE_REGISTER, addr, output_value=value)
            # logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))

    
    def write_byte_multi(self, addr, values):
        return self.write(1, cst.WRITE_MULTIPLE_REGISTERS, addr, output_value=value)
        
    
    # read coils
    def read_bit_rw(self, addr, number):
        return self.read(1, cst.READ_COILS, addr, number)
        
    
    # read discrete inputs
    def read_bit_r(self, addr, number):
        return self.read(1, cst.READ_DISCRETE_INPUTS, addr, number)
        
    
    # read holding registers
    def read_byte_rw(self, addr, number):
        return self.read(1, cst.READ_HOLDING_REGISTERS, addr, number)
        
    
    # read input registers
    def read_byte_r(self, addr, number):
        return self.read(1, cst.READ_INPUT_REGISTERS, addr, number)
        



    def agv_set_task_id(self, task_id):
        self.write_byte_one( StarRegister.HR.AGV_TASK_ID,
                             task_id )

    def agv_set_task(self, task_type):
        self.write_byte_one( StarRegister.HR.AGV_TASK,
                             task_type )

    def agv_set_task_param_0(self, task_param_0 ):
        self.write_byte_one( StarRegister.HR.AGV_TASK_PARAM_0,
                             task_param_0 )

    def agv_set_task_param_1(self, task_param_1 ):
        self.write_byte_one( StarRegister.HR.AGV_TASK_PARAM_1,
                             task_param_1 )

    def agv_get_last_task_id(self):
        return self.read_byte_r( StarRegister.IR.AGV_TASK_ID,
                                 1 )[0]

    def agv_add_task_inner( self , 
                            task_type = 0 , 
                            task_param_0 = 0 , 
                            task_param_1 = 0 ):
        last_task_id = self.agv_get_last_task_id()
        task_id = last_task_id + 1
        self.agv_set_task( task_type )
        self.agv_set_task_param_0( task_param_0 )
        self.agv_set_task_param_1( task_param_1 )
        self.agv_set_task_id( task_id )

        while(self.__running):
            if ( (self.__star_state.agv_task_id      == task_id     ) and
                 (self.__star_state.agv_task         == task_type   ) and
                 (self.__star_state.agv_task_param_0 == task_param_0) and
                 (self.__star_state.agv_task_param_1 == task_param_1) and
                 (self.__star_state.agv_task_status  != StarState.TaskState.NO_TASK) ):
                self.agv_set_task( StarCommand.AgvTask.NO_TASK )
                break
            else:
                time.sleep(0.1)            
                

    def agv_add_task( self , 
                      task_type = 0 , 
                      task_param_0 = 0 , 
                      task_param_1 = 0 ):
        self.agv_add_task_inner( task_type,
                                 task_param_0 )


    def agv_go_ready(self):
        self.agv_add_task( task_type = StarCommand.AgvTask.GO,
                           task_param_0 = StarCommand.AgvTaskStation.READY )

    def agv_go_pick(self):
        self.agv_add_task( task_type = StarCommand.AgvTask.GO,
                           task_param_0 = StarCommand.AgvTaskStation.PICK )

    def agv_go_place(self):
        self.agv_add_task( task_type = StarCommand.AgvTask.GO,
                           task_param_0 = StarCommand.AgvTaskStation.PLACE )

    def agv_go(self, station):
        if(station == 1):
            self.agv_go_place()
        elif(station == 2):
            self.agv_go_pick()
        else:
            self.Log.error("agv_go(): station ID [%d] invalid. "
                           "Only 2 stations available."
                           ""%(station))


    def wait_agv_task_finish(self):
        while(self.__running):
            if (self.__star_state.agv_task_status != StarState.TaskState.RUNNING):
                break
            else:
                time.sleep(0.1)


    def elfin_set_task_id(self, task_id):
        self.Log.info("elfin_set_task_id(%d)"%(task_id))
        self.write_byte_one( StarRegister.HR.ELFIN_TASK_ID,
                             task_id )

    def elfin_set_task(self, task_type):
        self.Log.info("elfin_set_task(%d)"%(task_type))
        self.write_byte_one( StarRegister.HR.ELFIN_TASK,
                             task_type )

    def elfin_set_task_param_0(self, task_param_0 ):
        self.Log.info("elfin_set_task_param_0(%d)"%(task_param_0))
        self.write_byte_one( StarRegister.HR.ELFIN_TASK_PARAM_0,
                             task_param_0 )

    def elfin_set_task_param_1(self, task_param_1 ):
        self.Log.info("elfin_set_task_param_1(%d)"%(task_param_1))
        self.write_byte_one( StarRegister.HR.ELFIN_TASK_PARAM_1,
                             task_param_1 )

    def elfin_get_last_task_id(self):
        self.Log.info("elfin_get_last_task_id()")
        return self.read_byte_r( StarRegister.IR.ELFIN_TASK_ID,
                                 1 )[0]

    def elfin_add_task_inner( self , 
                              task_type = 0 , 
                              task_param_0 = 0 , 
                              task_param_1 = 0 ):
        self.Log.info("elfin_add_task_inner()")
        last_task_id = self.elfin_get_last_task_id()
        task_id = last_task_id + 1
        self.Log.info("elfin_add_task_inner(): last_task_id[%d], task_id[%d]"
                      ""%(last_task_id, task_id))
        self.elfin_set_task( task_type )
        self.elfin_set_task_param_0( task_param_0 )
        self.elfin_set_task_param_1( task_param_1 )
        self.elfin_set_task_id( task_id )

        while(self.__running):
            if ( (self.__star_state.elfin_task_id      == task_id     ) and
                 (self.__star_state.elfin_task         == task_type   ) and
                 (self.__star_state.elfin_task_param_0 == task_param_0) and
                 (self.__star_state.elfin_task_param_1 == task_param_1) and
                 (self.__star_state.elfin_task_status  != StarState.TaskState.NO_TASK) ):
                self.elfin_set_task( StarCommand.ElfinTask.NO_TASK )
                break
            else:
                time.sleep(0.1)            
                

    def elfin_add_task( self , 
                        task_type = 0 , 
                        task_param_0 = 0 , 
                        task_param_1 = 0 ):
        self.Log.info("elfin_add_task()")
        self.elfin_add_task_inner( task_type,
                                   task_param_0 )

    def elfin_ready(self):
        self.Log.info("elfin_ready()")
        self.elfin_add_task( task_type = StarCommand.ElfinTask.READY )

    def elfin_place(self, block=1):
        if(block == 1):
            self.elfin_add_task( task_type = StarCommand.ElfinTask.PLACE_TRIANGLE )
        elif(block == 2):
            self.elfin_add_task( task_type = StarCommand.ElfinTask.PLACE_SQUARE )
        else:
            self.Log.error("elfin_place(): block ID [%d] invalid. "
                           "Only 2 blocks available."
                           ""%(block))

    def elfin_pick(self, block=1):
        if(block == 1):
            self.elfin_add_task( task_type = StarCommand.ElfinTask.PICK_TRIANGLE )
        elif(block == 2):
            self.elfin_add_task( task_type = StarCommand.ElfinTask.PICK_SQUARE )
        else:
            self.Log.error("elfin_pick(): block ID [%d] invalid. "
                           "Only 2 blocks available."
                           ""%(block))

    def wait_elfin_task_finish(self):
        while(self.__running):
            if (self.__star_state.elfin_task_status != StarState.TaskState.RUNNING):
                break
            else:
                time.sleep(0.1)


#    def __move(self, command):
#        self.write_byte_one( StarRegister.HoldingRegister.MOVE, command )
        
#    def move_station(self, station):
#        self.__move(station)
        
#    def move_stop(self):
#        self.__move(StarCommand.Move.STOP)

#    def __place(self, command):
#        self.write_byte_one( StarRegister.HoldingRegister.Place, command )
        
#    def place_material(self, material):
#        self.__place(material)
        
#    def place_stop(self):
#        self.__place(StarCommand.Place.STOP)

#    def __pick(self, command):
#        self.write_byte_one( StarRegister.HoldingRegister.PICK, command )
        
#    def pick_material(self, material):
#        self.__pick(material)
        
#    def pick_stop(self):
#        self.__pick(StarCommand.Pick.STOP)

#    def __trigger_button(self, command):
#        self.write_byte_one( StarRegister.HoldingRegister.BUTTON, command )
        
#    def trigger_button(self, button):
#        self.__trigger_button(button)
        
#    def trigger_button_none(self):
#        self.__trigger_button( StarCommand.Button.NONE )
    
#    def trigger_button_start(self):
#        self.__trigger_button( StarCommand.Button.START )
    
#    def trigger_button_stop(self):
#        self.__trigger_button( StarCommand.Button.STOP )
    
#    def trigger_button_initialize(self):
#        self.__trigger_button( StarCommand.Button.INITIALIZE )
    
    def update_state(self):
        self.__state = (
            self.__star_state.elfin_task_id ,
            self.__star_state.elfin_task    ,
            self.__star_state.elfin_task_param_0 ,
            self.__star_state.elfin_task_param_1 ,
            self.__star_state.elfin_task_status  ,

            self.__star_state.agv_task_id ,
            self.__star_state.agv_task    ,
            self.__star_state.agv_task_param_0 ,
            self.__star_state.agv_task_param_1 ,
            self.__star_state.agv_task_status  ,
        ) = self.read_byte_r(0,10)

        if(self.__state_history):
            if(filter(lambda x:x,
                      map(lambda y:self.__state[y]!=self.__state_history[y],
                          xrange(len(self.__state))))):
                self.Log.info("="*30)
                self.__star_state.debug_output()

        self.__state_history = self.__state
        
        #self.__star_state.agv_position = read_byte_r(19,1)
        #self.__star_state.init_state_elfin = read_bit_r(0,1)
        #self.__star_state.init_state_agv = read_bit_r(1,1)
        
        #if(self.__log_messsage):
        
    def update_state_loop(self):
        self.__updating_state = True
        while(self.__running and self.__updating_state):
            self.update_state()
            time.sleep(0.1)
            
    def start_update_state(self):
        if(self.__updating_state):
            return
        self.__update_state_thread = threading.Thread( target = self.update_state_loop )
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
