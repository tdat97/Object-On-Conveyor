from utils.camera import BaslerCam
from utils.text import *
from utils import tool
import time
import serial


def get_cam(exposure_time, logger=None):
    try:
        cam = BaslerCam(ExposureTime=exposure_time, logger=logger)
        for _ in range(3): cam.get_image()
        return cam, None
    except Exception as e:
        return None, e
    

def get_serial(port):
    try:
        my_serial = serial.Serial(port, 9600, timeout=0.05)

        my_serial.write(b"\xB0\x00\x00\xB0")
        value = my_serial.read(4)
        
        if value[0] != 0xc0:
            raise Exception("Make sure to connect serial.")
            
        return my_serial, None
        
    except Exception as e:
        return None, e
    