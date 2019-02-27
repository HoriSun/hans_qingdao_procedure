#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Horisun
# Email : huangzj117697@hanslaser.com 


import zipfile
 
import sys

import time

import os

from glob import glob

import shutil

import logging
import logging.handlers

#from py_utils.utils.utils import Log
from utils import Log

import re


def remove_path(_path):
    """Remove a file or a directory.
    param <_path> could either be relative or absolute. 
    
    :return: None
    """
    if os.path.isfile(_path):
        os.remove(_path)  # remove the file
    elif os.path.isdir(_path):
        shutil.rmtree(_path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(_path))

def zip_path(_path, ziph):
    """
    Compress a file or a directory into ZIP file, in a relative path tree
    
    :param _path: _path to the file or directory
    :type _path: str
    :param ziph: a zipfile handler (see module `zipfile`)
    :param ziph: zipfile.ZipFile
    :return: None
    """
    if os.path.isfile(_path):
        _ori_path = os.getcwd() 
        try:
            os.chdir( os.path.dirname(_path) )
            ziph.write( os.path.basename(_path) )
        except Exception as e:
            print e
        finally:
            os.chdir(_ori_path)
    elif os.path.isdir(_path):
        _ori_path = os.getcwd()
        try:
            os.chdir(_path)
            #print os.getcwd()
            #print ziph
            for root, dirs, files in os.walk( os.path.curdir ):
                #root = os.path.split(root)[-1]
                for file in files:
                    #print root, file
                    #ziph.write(os.path.join(root, file))
                    ziph.write(os.path.join(root, file))
        except Exception as e:
            print e
        finally:
            os.chdir(_ori_path)        
    else:
        raise ValueError("file {} is not a file or dir.".format(_path))




class LogManager(object):

    def __init__(self, log_dir, archive_dir, max_size):
        """

        :param log_dir: 日志所在目录
        :type log_dir: str
        :param max_size: 最大允许的日志量,单位为K
        :type max_size: int
        """
        self.__log_dir = os.path.abspath(log_dir)
        self.__archive_dir = os.path.abspath(archive_dir)

        if not os.path.exists(self.__log_dir):
            print "Generating LOG directory [ %s ]"%self.__log_dir
            os.makedirs(self.__log_dir)
        
        if not os.path.exists(self.__archive_dir):
            print "Generating ARCHIVE directory [ %s ]"%self.__archive_dir
            os.makedirs(self.__archive_dir)
        
        self.__max_size_log = max_size
        self.__max_size_archive = max_size
        self.__init_log()
        self.__log_suffix = "log"
        self.__archive_suffix = "zip"
        
    def __init_log(self):
        """初始化日志配制

        :return:
        """
        # 配置日志
        if not os.path.exists(self.__log_dir):
            os.mkdir(self.__log_dir)

        log_filename = os.path.join(self.__log_dir, "navigation_" + 
                                                    time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime()) + 
                                                    ".log" )

        self.__current_log_file_name = os.path.basename(log_filename)
                    
        logging.basicConfig(
            #filename= log_filename ,
            format="%(levelname)-10s %(pathname)s:%(lineno)s %(asctime)s %(message)s",
            #level=logging.INFO
        )

        class add_traceback(object):
            def __init__(self, _log):
                self._log = _log
                self.info = _log.info
                self.debug = _log.debug
            def error(self, *argc, **argv):
                argv.update({"exc_info":1})
                self._log.error(*argc,**argv)
            def warning(self, *argc, **argv):
                argv.update({"exc_info":1})
                self._log.warning(*argc,**argv)
        
        log = logging.getLogger("navigation")
        log.setLevel(logging.INFO)

        # assume 80 bytes per line, and 3 lines per second (a bit too fast, for redundancy)
        #bytes_per_day_guess = 80*3*60*60*24  # means about 20MB per day
        #max_bytes_per_file = bytes_per_day_guess / float( 6 * 3 )    
        max_bytes_per_file = 2 * 1024 * 1024
        backup_count = self.__max_size_log / float(max_bytes_per_file)

      
        # Add the log message handler to the logger
        rotate_handler = logging.handlers.RotatingFileHandler( log_filename, 
                                                               maxBytes = int(max_bytes_per_file) ,  
                                                               backupCount = int(backup_count) )
        #rotate_handler.setFormatter( logging.Formatter("%(levelname)-10s %(pathname)s:%(lineno)s %(asctime)s %(message)s") )
        rotate_handler.setFormatter( logging.Formatter("%(levelname)-10s %(filename)s:%(lineno)s %(asctime)s %(message)s") )
        log.addHandler( rotate_handler )
        
        log_with_traceback = add_traceback(log)
        
        Log.init( debug=log.debug, 
                  info=log.info, 
                  warn=log_with_traceback.warning, 
                  error=log_with_traceback.error )

        Log.info("max space for log files run one time: %f MB"%(self.__max_size_log/float(2**20)))
        Log.info("max bytes per log file: %f MB"%(max_bytes_per_file/float(2**20)))
        Log.info("log file backup count: %d files"%backup_count)
                  
    def get_current_log_file_name(self):
        return self.__current_log_file_name

    def log_size_not_exceed(self):
        """空间占用是否正常

        :return: 占用空间小于最大允许空间,则返回True, 否则返回False
        :rtype: int
        """
        return self.get_log_size() < self.__max_size_log

    def archive_size_not_exceed(self):
        """空间占用是否正常

        :return: 占用空间小于最大允许空间,则返回True, 否则返回False
        :rtype: int
        """
        return self.get_archive_size() < self.__max_size_archive

    def archive_and_cleanup(self):
        """检查压缩日志占用空间

        检查压缩日志占用空间,如果空间不够,则删除旧的压缩日志文件,直到占用空间小于最大允许占用空间
        :return: None
        """
        self.compress_and_remove()
        if self.archive_size_not_exceed():
            return
        files = self.get_archive_file_paths()
        Nfiles = len(files)
        files.sort(key=os.path.getctime)
        file_sorted_sizes = map(os.path.getsize, files)
        total_size = sum( file_sorted_sizes )
        decrease_size = total_size
        number_of_removal = 0
        for i in xrange(Nfiles):
            decrease_size -= file_sorted_sizes[i]
            if(decrease_size < self.__max_size_archive):
                number_of_removal = i+1
                break
        if(not number_of_removal):
            number_of_removal = Nfiles

        for f in files[:number_of_removal]:
            os.remove(f)
            #if self.archive_size_not_exceed():
            #    return

    def get_log_size(self):
        """获取已有日志占用的空间

        :return: 日志占用空间
        :rtype: int
        """
        return sum([os.path.getsize(f) for f in self.get_log_file_paths()])

    def get_log_size_list(self):
        """获取已有日志占用的空间

        :return: 日志占用空间
        :rtype: int
        """
        return [os.path.getsize(f) for f in self.get_log_file_paths()]

    def get_archive_size(self):
        """获取已有压缩日志占用的空间

        :return: 压缩日志占用空间
        :rtype: int
        """
        return sum([os.path.getsize(f) for f in self.get_archive_file_paths()])


    def get_archive_size_list(self):
        """获取已有压缩日志占用的空间

        :return: 压缩日志占用空间
        :rtype: int
        """
        return [os.path.getsize(f) for f in self.get_archive_file_paths()]

    def get_files_with_suffix(self, path, sufx):
        """Get a list of file in a direcory with a given suffix

        :param path: diretory to find
        :type path: str
        :param sufx: suffix of files, no '.' ('.log' is invalid, and 'log' is valid)
        :type sufx: str
        :return: list of file paths
        :rtype: list
        """
        #files = []
        #for d, dirs, file_names in os.walk(self.__log_dir):
        #    files.extend([os.path.join(d, filename) for filename in file_names])
        #return files
        return map( lambda f: f.replace(os.path.join(path, ""),"") ,
                              self.get_file_paths_with_suffix(path, sufx) )

    def get_file_paths_with_suffix(self, path, sufx):
        """Get a list of file in a direcory with a given suffix

        :param path: diretory to find
        :type path: str
        :param sufx: suffix of files, no '.' ('.log' is invalid, and 'log' is valid)
        :type sufx: str
        :return: list of file paths
        :rtype: list
        """
        #files = []
        #for d, dirs, file_names in os.walk(self.__log_dir):
        #    files.extend([os.path.join(d, filename) for filename in file_names])
        #return files
        return ( glob(os.path.join(path,"*."+sufx)) +
                 glob(os.path.join(path,"*."+sufx+".[0-9]*")) )  

    def get_log_files(self):
        return self.get_files_with_suffix( self.__log_dir, self.__log_suffix )

    def get_archive_files(self):    
        return self.get_files_with_suffix( self.__archive_dir, self.__archive_suffix )

    def get_log_file_paths(self):
        return self.get_file_paths_with_suffix( self.__log_dir, self.__log_suffix )

    def get_archive_file_paths(self):    
        return self.get_file_paths_with_suffix( self.__archive_dir, self.__archive_suffix )

    def compress_and_remove(self):
            _log_path = self.__log_dir
            _arch_path = self.__archive_dir 
            _log_sufx = self.__log_suffix
            _arch_sufx = self.__archive_suffix

            log_list = self.get_log_files()
            print log_list
            print self.__current_log_file_name
            log_list.remove( self.__current_log_file_name )


            for log_file in log_list:

                zip_file = re.sub(r"\."+_log_sufx+r"((\.[0-9]*)?)", r"\1", log_file)+".zip" # ".log"->".zip"
                print zip_file
                log_file = os.path.abspath(os.path.join( _log_path, log_file ))
                log_zip_file = os.path.abspath(os.path.join( _log_path, zip_file ))
                archive_zip_file = os.path.abspath(os.path.join( _arch_path, zip_file ))

                zf = zipfile.ZipFile( log_zip_file, 'w', zipfile.ZIP_DEFLATED )
                
                zip_path( log_file, zf )
                #zf.flush()
                #os.fsync(zf)
                #os.fdatasync(zf)
                zf.close()
                del zf
                
                if( _arch_path != _log_path ):
                    try:
                        shutil.move( log_zip_file,      # from 
                                    archive_zip_file ) # to
                
                        #remove_path( log_zip_file )
                        pass
                    except Exception as e:
                        Log.error(e.args)
                        print e
                
                remove_path( log_file )
    



if __name__ == "__main__":
    import traceback
    import signal
    import sys
    k = []
    def test():
        global k   
        log_dir = os.path.join(os.path.curdir,"test","log")
        archive_dir = os.path.join(os.path.curdir,"test","archive")
        print log_dir
        print archive_dir

        err = 0
        lm = LogManager( log_dir, archive_dir, (2**20)*100 )
        k.append(lm)

        def exit_signal_hanlder(x, y):
            lm.archive_and_cleanup()
            sys.exit(0)

        signal.signal( signal.SIGINT,   exit_signal_hanlder )
        signal.signal( signal.SIGBREAK, exit_signal_hanlder )
        signal.signal( signal.SIGABRT,  exit_signal_hanlder )
        signal.signal( signal.SIGTERM,  exit_signal_hanlder )


        try:
            lm.archive_and_cleanup()
        except Exception as e:
            print e, type(e), e.args
            traceback.print_exc()
            k.append(e)
            
        if not os.path.exists(log_dir):
            print "Generating LOG directory [ %s ]"%log_dir
            os.makedirs(log_dir)
        
        try:
            for i in xrange(10):#*1000*5):
                #print i
                #f = open(os.path.join(log_dir,"%d.log"%i),"w")
                data_ = ["hahahahahahhhh%d\n"%j for j in xrange(i,i+10)]
                #f.writelines(data_)
                Log.info("".join(data_))
                #f.close()
        except Exception as e:
            print e, type(e), e.args
            traceback.print_exc()
            Log.error("WTF")
            k.append(e)

        lm.archive_and_cleanup()


    test()