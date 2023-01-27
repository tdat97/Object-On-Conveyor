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

def get_serial(port, cam, offset=0.25):
    try:
        my_serial = serial.Serial(port, 9600, timeout=0, bytesize=serial.EIGHTBITS, 
                                  stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_ODD)

        # 빛 변화 촬영
        time.sleep(0.2)
        cam.set_exposure(25000)
        img_t0 = cam.get_image()
        my_serial.write(LIGHT_ON)
        
        time.sleep(0.2)
        cam.set_exposure(2500)
        img_t1 = cam.get_image()
        my_serial.write(LIGHT_OFF)

        # debug
        tool.imwrite("./temp/light_on.jpg", img_t1)
        tool.imwrite("./temp/light_off.jpg", img_t0)
        
        # 이미지 차이
        img = tool.get_diff_img(img_t0, img_t1)
        

        # 차이 변화 감지
        ratio = tool.diff2ratio(img)
        if ratio > offset:
            return my_serial, None
        else:
            raise Exception("Make sure to connect serial.")
        
    except Exception as e:
        return None, e