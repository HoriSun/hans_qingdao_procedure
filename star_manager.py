from utils import Log

class StarManager(object):
    def __init__(self):
        pass
        
    def update_param(self, config_data=None):
        pass
        
    def connect(self):
        pass
        
    def init(self):
        pass
        
    def clean_up(self):
        pass
        
    #====== type-specific functions ======#
        
    def go_right(self):
        pass
        
    def check_goods(self):
        # [ TODO ] the two goods should be there,
        #          otherwise burst out sound alert and light blinks in red.
        pass
        
    def light(self, color="green", blink=False):
        pass
        
    def play_sound(self, sound_id=0, repeat_time=0):
        pass
        
    