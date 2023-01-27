from utils.camera import SentechCam, OCam
from utils.text import *
from utils import tool
import time
import serial
# debug
import cv2


def get_cam(exposure_time, logger=None):
    try:
        cam = SentechCam(ExposureTime=exposure_time, logger=logger)
        for _ in range(3): cam.get_image()
        return cam, None
    except Exception as e:
        return None, e
    
def get_cam2():
    try:
        cam = OCam()
        cam.get_image = cam.CamGetImage
        # cam.CamOpen(DevNo=0, Resolution=(3840,2160), FramePerSec=10, BytePerPixel=1)
        cam.CamOpen(DevNo=0, Resolution=(1280,720), FramePerSec=100, BytePerPixel=1)
        cam.CamSetCtrl(cam.CTRL_EXPOSURE, -3)
        cam.CamStart()
        if cam.GetConnectedCamNumber() == 0:
            raise Exception("oCam not Found...")
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
    