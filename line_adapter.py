# -*- coding: utf-8 -*-
import threading
import struct
import subprocess
import time

from utils import log_wrap
from define import SystemEnum

import sys
import socket

from system_check import check_system

from socket_err_str import socket_error_str
    

Log = log_wrap(prefix = "[ Line Adapter ]")
    
# [ TODO ] Make a general Keyance adapter
    
class LineAdapterHelper(object):
    DEBUG = False
    
try:
    import win32api
    def get_err_msg(errn):
        if(not isinstance(errn, int)):
            Log.error("errn [ %s ] is not `int` type"%errn)
            msg = repr(errn)
        else:
            try:
                msg = win32api.FormatMessageW(errn)
            except Exception as e:
                Log.error("get_err_msg() error: %s"%e)
                msg = "{ errno: [ %s ]  msg: [ %s ] }"%(errn, socket_error_str(errn))
                
        if(isinstance(errn, unicode)):
            return msg
        else:
            try:
                return msg.decode("gb2312")
            except Exception as e:
                return msg
except:
    def get_err_msg(errn):
        return socket_error_str(errn)



class SoftComponentsMacro(object):
    R = "R"
    MR = "MR"
    DM = "DM"

# [ HORISUN ] Not used here
#class DataFormatMacro(object):
#    default = DEFAULT = ""
#    uint16  = U = ".U"
#    int16   = S = ".S"
#    uint32  = D = ".D"
#    int32   = L = ".L"
#    hex16   = H = ".H"
 


class AddressMacro(object):
    """各个模块的内存地址"""
    
    LINE_RIGHT_SENSOR_FRONT = 0
    LINE_RIGHT_SENSOR_MIDDLE = 1
    LINE_RIGHT_SENSOR_END = 2
    LINE_RIGHT_SENSOR_AGV = 3
    LINE_LEFT_SENSOR_FRONT = 6 #4
    LINE_LEFT_SENSOR_MIDDLE = 5
    LINE_LEFT_SENSOR_END = 4 #6
    LINE_LEFT_SENSOR_AGV = 7
    
    LINE_RIGHT_ROLL_FORWARD = 503
    LINE_RIGHT_ROLL_BACKWARD = 504
    LINE_LEFT_ROLL_FORWARD = 505
    LINE_LEFT_ROLL_BACKWARD = 506
    LINE_RIGHT_POWER_ON = 507
    LINE_LEFT_POWER_ON = 508

    

    
class PlcConnector(object):
    '''
    Handles socket connection with PLC,
    and the (command send | reply recv) activity
    SHOULD try to reconnect when the connection is lost
    better to be able to detect connection lost (keep-alive heartbeat)
    '''

    def __init__( self, ip, port=8501,
                  connect_cb = lambda:None,
                  disconnect_cb = lambda:None
                ):

        self.__plc_ip = ip
        self.__plc_port = port
        self.__connect_timeout = 5.0

        self.__connect_cb = connect_cb
        self.__disconnect_cb = disconnect_cb
        
        self.__connected = False
        self.__connecting = False

        self.__read_buf = b""

        self.__socket_lock = threading.Lock()

    def update_param(self, ip, port):
        self.__plc_ip = ip
        self.__plc_port = port
        
    def reconnect(self):
        self.close()
        self.connect()
    
    def connect(self):
        self.__connect()
        
    def register_connection_cb(self,
                               connect_cb = lambda:None,
                               disconnect_cb = lambda:None):
        self.__connect_cb = connect_cb
        self.__disconnect_cb = disconnect_cb

    def __connect(self):
        self.__connected = False
        self.__connecting = True
        #self.__socket = socket.create_connection(( self.__plc_ip   , 
        #                                           self.__plc_port ))
        self.__socket = socket.socket( socket.AF_INET     ,
                                       socket.SOCK_STREAM )        
        self.__set_socket_opt() # [ WARN ] timeout = ???

        Log.info("Start connecting to PLC "
                     "[ %s : %s ]"%( self.__plc_ip   ,
                                     self.__plc_port ))
        while(True):
            Log.info("Waiting %.2f seconds for "
                         "connection..."%(self.__connect_timeout))
            try:
                self.__socket.connect(( self.__plc_ip   ,
                                        self.__plc_port ))
                break
            except Exception as e:
                #eeee = e
                print e.errno
                print e.__dict__
                Log.error(
                    "socket connection to PLC failed: %s %s\n"
                    " [ %s ]%s\n"%(
                        e, type(e), e.errno, get_err_msg(e.errno) if e.errno else None
                    ), 
                    exc_info=1
                )
                if(e.errno == 10056):
                    #self.__connected = True
                    Log.error("error 10056, break loop")
                    break
                Log.info("Sleep for 1 second")
                time.sleep(1)
                continue
        
        self.__connected = True
        self.__connecting = False
        self.__connect_cb()
        Log.info("Connection to PLC established.")
        
        # Clear the buffer
        self.__read_buf = b""

        
    def close(self):
        try:
            self.__socket.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            Log.error(e, exc_info=1)
        self.__socket.close()
        self.__disconnect_cb()
        
    def is_connected(self):
        return self.__connected and (not self.__connecting)

    def __set_socket_opt(self):
        self.__socket.settimeout( self.__connect_timeout ) # ??? WARNING ???
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # 激活keep-alive
        _system = check_system()
        print "===================================",_system
        if(_system == None):
            raise RuntimeError("Operating system UNKNOWN!!! exiting")
            sys.exit(-1)
        elif(_system == SystemEnum.LINUX):
            self.__socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 1)  # tcp_keepalive_time
            self.__socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 3)  # tcp_keepalive_probes
            self.__socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1)  # tcp_keepalive_intvl
        elif (_system == SystemEnum.WINDOWS):
            self.__socket.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 1000, 300))
        else:
            raise RuntimeError("Operating system UNDEFINED!!! exiting")

            
    def assert_connected(self):
        if (self.__connected and (not self.__connecting)):
            pass
        else:
            raise RuntimeError("PLC:  "
                               "connected  [ %s ]   "
                               "connecting [ %s ]"%(
                                   self.__connected,
                                   self.__connecting
                               ))


    def write(self, data):
        try:
            if(LineAdapterHelper.DEBUG):
                Log.info("Writing [ %s ]"%repr(data))
            self.assert_connected()
            
            ldata = len(data)
            while(True):
                ret = self.__socket.send(data)
                if(ret < 0): # == -1):
                    raise Exception("Socket closed")
                elif(ret == ldata):
                    break
                elif(ret < ldata):
                    data = data[ret:]
                    ldata -= ret
                else:
                    continue
            
        except Exception as e:
            Log.error(
                " Writing failed: %s %s\n"
                "%s"%(
                    e, type(e), 
                    (" ERRNO[ %s ] : %s \n"%(e.errno,get_err_msg(e.errno))) if hasattr(e,"errno") else ""
                ), 
                exc_info=1
            )
            
            self.wake_reconnecting_daemon()
            
            raise RuntimeError("Found PLC connection lost when try writing. Try reconnecting.")
            
            
    
    def reconnecting_deamon(self):
        Log.info("Reconnecting daemon start to work.")
        while((not self.__connected)):
            self.close()
            self.__connect()

    
    
    def wake_reconnecting_daemon(self):
        Log.info("Try to reconnnect. ")
        
        if(self.__connecting):
            Log.info("Reconnecting daemon is working...")
            return
            
        self.__connected = False
        Log.info("Waking up reconnecting daemon")
            
        t = threading.Thread(target = self.reconnecting_deamon)
        t.setDaemon(True)
        t.start()
        

    def read(self):
        try:
            if(LineAdapterHelper.DEBUG):
                Log.info("Reading")
            self.assert_connected()
            
            _recv_data = self.__socket.recv(1024)  
            self.__read_buf += _recv_data
            if(LineAdapterHelper.DEBUG):
                Log.info("Receive [ %s ]"%repr(_recv_data))
                
        except Exception as e:
            Log.error(
                " Reading failed: %s %s\n"
                "%s"%(
                    e, type(e), 
                    (" ERRNO[ %s ] : %s \n"%(e.errno,get_err_msg(e.errno))) if hasattr(e,"errno") else ""
                ), 
                exc_info=1
            )
            
            if(hasattr(e,"errno")):
                if(e.errno == 10054):
                    Log.error("ERROR 10054 : Connection reset by peer")
            
            self.wake_reconnecting_daemon()
            
            #raise Exception("Raise an exception after reconnecting "
            #                "to ensure that initialization will be "
            #                "done again")
            
            raise RuntimeError("Found PLC connection lost when try reading. Try reconnecting.")
            
    
    def cut(self):
        read_split = "\r\n"
        lrs = len(read_split)
        eol = self.__read_buf.find( read_split )
        if(eol<0):
            return ""

        seg = self.__read_buf[:eol+lrs]
        self.__read_buf = self.__read_buf[eol+lrs:]
        return seg

    def __repr__(self):
        return repr(self.__read_buf)

    def get_buf(self):
        return self.__read_buf

        
    def read_one(self):
        read_count_max = 3
        read_iter = xrange(read_count_max)
        for i in read_iter:
            ret = self.cut()
            if(ret):
                return ret
            self.read()
        else:
            return b""

    def send(self, data):
        """发送数据

        :param data:
        :type data: str
        :return:
        :rtype: str
        """
        with self.__socket_lock:
            data = data.encode() + b'\r'
            if(LineAdapterHelper.DEBUG):
                Log.info('send to plc:%s' % data)
            recv_data = b""

            # TODO 可能陷入死循环
            while(True):
                self.write(data)
                recv_data = self.read_one()
                if(not recv_data):
                    pass
                    #self.write("ER") # clear all the errors
                else:
                    break
            if(LineAdapterHelper.DEBUG):
                Log.info("recv from plc: %s" % recv_data)
            recv_data = recv_data[:-2].decode()
            if len(recv_data) == 2 and recv_data.startswith("E"):
                self.__handler_error(recv_data[1])
            else:
                return recv_data
        
    @classmethod
    def __handler_error(cls, error_code):
        """处理错误

        :param error_code: 错误码
        :type error_code: str
        :return:
        """
        if error_code == "0":
            raise RuntimeError(u"PLC: 软元件编号异常")
        elif error_code == "1":
            raise RuntimeError(u"PLC: 命令异常")
        elif error_code == "2":
            raise RuntimeError(u"PLC: 未登录程序")
        elif error_code == "4":
            raise RuntimeError(u"PLC: 禁止写入")
        elif error_code == "5":
            raise RuntimeError(u"PLC: 单元错误")
        elif error_code == "6":
            raise RuntimeError(u"PLC: 无注释")
        else: 
            raise RuntimeError(u"PLC: 其他错误")
        
        
        


class SoftComponent(object):
    """软元件"""

    def __init__(self, type_, id_, format_):
        """

        :param type_: 软元件类型
        :param id_: 软元件编号
        :param formate_: 软元件格式
        """
        self.type = type_
        self.id = id_
        self.format = format_


class Plc(object):
    def __init__(self, ip, port=8501,
                 connect_cb = lambda:None,
                 disconnect_cb = lambda:None):
        self.__ip = ip
        self.__port = port
        self.__connect_cb = self.on_connect_gen(connect_cb)
        self.__disconnect_cb = self.on_disconnect_gen(disconnect_cb)
        self.__plc_connector = PlcConnector( self.__ip, 
                                             self.__port,
                                             connect_cb = self.__connect_cb,
                                             disconnect_cb = self.__disconnect_cb
                                           )

    def update_param(self, ip, port):
        self.__ip = ip
        self.__port = port
        self.__plc_connector.update_param(self.__ip,
                                          self.__port)

    def is_connected(self):
        return self.__plc_connector.is_connected()
                                          
    def connect(self):
        self.__plc_connector.connect()
    
    def reconnect(self):
        self.__plc_connector.reconnect()
    
    def register_connection_cb(self,
                               connect_cb = lambda:None,
                               disconnect_cb = lambda:None):
        self.__connect_cb = self.on_connect_gen(connect_cb)
        self.__disconnect_cb = self.on_disconnect_gen(disconnect_cb)
        self.__plc_connector.register_connection_cb(
            self.__connect_cb,
            self.__disconnect_cb    
        )
                                           
    def on_connect_gen(self,f):
        def on_connect():
            # do something here
            f()
            # and do something here
        return on_connect
    
    def on_disconnect_gen(self,f):
        def on_disconnect():
            # do something here
            f()
            # and do something here
        return on_disconnect
        
                                           
    def shutdown(self):
        """关闭PLC

        :return:
        """
        self.__plc_connector.send("M0")

    def reboot(self):
        """重启PLC

        :return:
        """
        self.__plc_connector.send("M1")

    def reset(self):
        """重置PLC errors

        :return:
        """
        self.__plc_connector.send("ER")

    def set_bit(self, soft_component_type, address):
        """置位

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :return: None
        """
        self.__plc_connector.send(
            "ST %s%s" % (
                soft_component_type, 
                address
            ))

    def reset_bit(self, soft_component_type, address):
        """复位

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :return: None
        """
        self.__plc_connector.send(
            "RS %s%s" % (
                soft_component_type, 
                address
            ))

    def bit_write_value(self, soft_component_type, address, value):
        '''
        self.__plc_connector.send(
            "%s %s%s" % (
                "ST" if value else "RS",
                soft_component_type, 
                address
            ))
        '''
        if(value):
            self.set_bit(soft_component_type,address)

    def set_bits(self, soft_component_type, address, number):
        """置位多个位

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :param number: 置位的数量
        :type number: int
        :return: None
        """
        self.__plc_connector.send("STS %s%s %s" % (soft_component_type, address, number))

    def reset_bits(self, soft_component_type, address, number):
        """复位多个位

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :param number: 复位的数量
        :type number: int
        :return: None
        """
        self.__plc_connector.send("RSS %s%s %s" % (soft_component_type, address, number))

    def read(self, soft_component_type, address):
        """读取一个地址

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :return:
        """
        ret = self.__plc_connector.send("RD %s%s" % (soft_component_type, address))
        return int(ret)

    def reads(self, soft_component_type, address, number):
        """读取多个连续地址

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :param number: 读取的数量
        :type number: int
        :return: 返回读取到的数据
        :rtype: list
        """
        ret = self.__plc_connector.send("RDS %s%s %s" % (soft_component_type, address, number))
        return self.string_to_number_list(ret)

    def write(self, soft_component_type, address, value):
        """写一个地址

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :param value: 写入的值
        :type value: int
        :return: None
        """
        self.__plc_connector.send("WR %s%s %s" % (soft_component_type, address, value))

    def write_with_type(self, soft_component_type, address, value, value_type):
        """写一个地址

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :param value: 写入的值
        :type value: int
        :return: None
        """
        self.__plc_connector.send("WR %s%s%s %s" % (soft_component_type, address, value_type, value))

    def writes(self, soft_component_type, address, *args):
        """写多个连续地址

        :param soft_component_type: 软元件类型
        :type soft_component_type: str
        :param address: 软元件地址
        :type address: int
        :param args: 写入的值
        :type args: list
        :return: None
        """
        l = [soft_component_type, address]
        l.extend(args)
        s = "WRS %s%s " + str(len(args)) + (" %s" * len(args))
        self.__plc_connector.send(s % tuple(l))

    def login_monitor_word(self, soft_components):
        """登陆监控器, 注册需要监控的数据

        :param soft_components:
        :type soft_components: list
        :return:
        """
        x = ["%s%s%s" % (soft_component.type, 
                         soft_component.id, 
                         soft_component.format) 
             for soft_component in soft_components]
        f = "MWS" + " %s" * len(x)
        self.__plc_connector.send(f % tuple(x))


    def login_monitor_bit(self, soft_components):
        """登陆监控器, 注册需要监控的数据

        :param soft_components:
        :type soft_components: list
        :return:
        """
        x = ["%s%s" % (soft_component.type, 
                       soft_component.id) 
             for soft_component in soft_components]
        f = "MBS" + " %s" * len(x)
        self.__plc_connector.send(f % tuple(x))


    def read_monitor_word(self):
        """读取监控器中的数据

        :return: 监控器中的数据
        :rtype: list
        """
        ret = self.__plc_connector.send("MWR")
        return self.string_to_number_list(ret)


    def read_monitor_bit(self):
        """读取监控器中的数据

        :return: 监控器中的数据
        :rtype: list
        """
        ret = self.__plc_connector.send("MBR")
        return self.string_to_number_list(ret)


    @classmethod
    def string_to_number_list(self, s):
        return [int(n) for n in s.split()]

        
            
class LineAdapter(object):
    """用于注册所有到其他节点的映射"""

    __port_default__ = 8501
    
    class ROLL_STATE(object):
        STOP = 0
        FORWARD = 1
        BACKWARD = 2
        
    class POWER(object):
        OFF = 0
        ON = 1

    def __init__(self, ip, port=8501):
        self.__ip = ip
        self.__port = port
        self.__plc = Plc(ip=self.__ip, port=self.__port)        
        self.__plc.register_connection_cb(connect_cb = self.on_connect,
                                          disconnect_cb = self.on_disconnect)

        self.data = {
            "line_right_sensor_front" : 0 ,
            "line_right_sensor_middle" : 0 ,
            "line_right_sensor_end" : 0 ,
            "line_right_sensor_agv" : 0 ,
            
            "line_left_sensor_front" : 0 ,
            "line_left_sensor_middle" : 0 ,
            "line_left_sensor_end" : 0 ,
            "line_left_sensor_agv" : 0 ,
        }

        self.__updating_state = False
        self.__state_update_thread = None
                                          
        self.soft_components_bit = [
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_SENSOR_FRONT, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_SENSOR_MIDDLE, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_SENSOR_END, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_SENSOR_AGV, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_LEFT_SENSOR_FRONT, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_LEFT_SENSOR_MIDDLE, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_LEFT_SENSOR_END, None ),
            SoftComponent( SoftComponentsMacro.R, AddressMacro.LINE_LEFT_SENSOR_AGV, None ),

            SoftComponent( SoftComponentsMacro.R, 503, None ),
            SoftComponent( SoftComponentsMacro.R, 504, None ),
            SoftComponent( SoftComponentsMacro.R, 505, None ),
            SoftComponent( SoftComponentsMacro.R, 506, None ),
            SoftComponent( SoftComponentsMacro.R, 507, None ),
            SoftComponent( SoftComponentsMacro.R, 508, None ),

            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_RIGHT_SENSOR_FRONT, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_RIGHT_SENSOR_MIDDLE, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_RIGHT_SENSOR_END, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_RIGHT_SENSOR_AGV, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_LEFT_SENSOR_FRONT, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_LEFT_SENSOR_MIDDLE, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_LEFT_SENSOR_END, None ),
            #SoftComponent( SoftComponentsMacro.MR, AddressMacro.LINE_LEFT_SENSOR_AGV, None ),

        ]

                    
    def update_param(self, ip, port):
        self.__ip = ip
        self.__port = port
        self.__plc.update_param(self.__ip, self.__port)
        
    def is_connected(self):
        return self.__plc.is_connected()
        
    def connect(self):
        self.__plc.connect()
        
    def reconnect(self):
        self.__plc.reconnect()
        
    def state_update_start(self):
        if(self.__updating_state):
            return
    
        self.__state_update_thread = threading.Thread( target = self.state_update_loop )
        self.__state_update_thread.setDaemon(True)
        self.__state_update_thread.start()
    
    def state_update_stop(self):
        if(not self.__updating_state):
            return
        
        self.__updating_state = False
        self.__state_update_thread.join()
        self.__state_update_thread = None

    def state_update(self):
        (
        
            self.data["line_right_sensor_front"] ,
            self.data["line_right_sensor_middle"] ,
            self.data["line_right_sensor_end"] ,
            self.data["line_right_sensor_agv"] ,
            
            self.data["line_left_sensor_front"] ,
            self.data["line_left_sensor_middle"] ,
            self.data["line_left_sensor_end"] ,
            self.data["line_left_sensor_agv"] ,
            
            s503,
            s504,
            s505,
            s506,
            s507,
            s508,
            
        ) = data = self.__plc.read_monitor_bit()
        #Log.info("%s  %s"%(data[:8],data[8:]))

    def state_update_loop(self):
        self.__updating_state = True
        while(self.__updating_state):
            self.state_update()
            time.sleep(0.1)
        
    def on_connect(self):
        Log.info("PLC connection established, registering data monitor.")
        self.__plc.login_monitor_bit(self.soft_components_bit)
        
    def on_disconnect(self):
        Log.info("PLC disconnected.")
        
        
    def left_power_on(self):
        self.__plc.set_bit(SoftComponentsMacro.R, AddressMacro.LINE_LEFT_POWER_ON)
    
    def left_power_off(self):
        self.__plc.reset_bit(SoftComponentsMacro.R, AddressMacro.LINE_LEFT_POWER_ON)
    
    def left_power(self, on):
        if(on):
            self.left_power_on()
        else:
            self.left_power_off()
    
    def right_power_on(self):
        self.__plc.set_bit(SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_POWER_ON)
    
    def right_power_off(self):
        self.__plc.reset_bit(SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_POWER_ON)
    
    def right_power(self, on):
        if(on):
            self.right_power_on()
        else:
            self.right_power_off()
    
    def power_off(self):
        self.left_power_off()
        self.right_power_off()
    
    def power_on(self):
        self.left_power_on()
        self.right_power_on()
    
    def left_roll_forward_on(self):
        self.__plc.set_bit(SoftComponentsMacro.R, AddressMacro.LINE_LEFT_ROLL_FORWARD)
    
    def left_roll_forward_off(self):
        self.__plc.reset_bit(SoftComponentsMacro.R, AddressMacro.LINE_LEFT_ROLL_FORWARD)
        
    def left_roll_backward_on(self):
        self.__plc.set_bit(SoftComponentsMacro.R, AddressMacro.LINE_LEFT_ROLL_BACKWARD)
    
    def left_roll_backward_off(self):
        self.__plc.reset_bit(SoftComponentsMacro.R, AddressMacro.LINE_LEFT_ROLL_BACKWARD)

    def right_roll_forward_on(self):
        self.__plc.set_bit(SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_ROLL_FORWARD)
    
    def right_roll_forward_off(self):
        self.__plc.reset_bit(SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_ROLL_FORWARD)
                
    def right_roll_backward_on(self):
        self.__plc.set_bit(SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_ROLL_BACKWARD)
    
    def right_roll_backward_off(self):
        self.__plc.reset_bit(SoftComponentsMacro.R, AddressMacro.LINE_RIGHT_ROLL_BACKWARD)
        
    def left_roll_forward(self):
        self.left_roll_backward_off()
        self.left_roll_forward_on()
        
    def left_roll_backward(self):
        self.left_roll_forward_off()
        self.left_roll_backward_on()
        
    def left_roll_stop(self):
        self.left_roll_forward_off()
        self.left_roll_backward_off()
        
    def right_roll_forward(self):
        self.right_roll_backward_off()
        self.right_roll_forward_on()
        
    def right_roll_backward(self):
        self.right_roll_forward_off()
        self.right_roll_backward_on()
        
    def right_roll_stop(self):
        self.right_roll_forward_off()
        self.right_roll_backward_off()
        
    def left_roll(self, state):
        if(state == ControlMapper.ROLL_STATE.STOP):
            self.left_roll_stop()
        elif(state == ControlMapper.ROLL_STATE.FORWARD):
            self.left_roll_forward()
        elif(state == ControlMapper.ROLL_STATE.BACKWARD):
            self.left_roll_backward()
        else:
            Log.error("left roll state invalid: %s"%(state))
            
    def right_roll(self, state):
        if(state == ControlMapper.ROLL_STATE.STOP):
            self.right_roll_stop()
        elif(state == ControlMapper.ROLL_STATE.FORWARD):
            self.right_roll_forward()
        elif(state == ControlMapper.ROLL_STATE.BACKWARD):
            self.right_roll_backward()
        else:
            Log.error("right roll state invalid: %s"%(state))
            
    def roll_stop(self):
        self.left_roll_stop()
        self.right_roll_stop()
        
