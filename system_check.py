import logging
import os
import platform
from define import SystemEnum

def check_system():
    try:
        if( platform.system() == 'Windows' ):
            assert os.name == 'nt', ("platform.system() == 'Windows' "
                                     "while os.name == '%s', expected 'nt'") % os.name
            
            return SystemEnum.WINDOWS
        if( platform.system() == 'Linux' ):
            assert os.name == 'posix', ("platform.system() == 'Linux' "
                                        "while os.name == '%s', expected 'posix'") % os.name
            return SystemEnum.LINUX
    except Exception as e:
        logging.error("[ %s ]"%e, exc_info=1)
        return None
