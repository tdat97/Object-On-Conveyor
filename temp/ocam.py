import platform
import ctypes
import numpy as np
import time 
import os

class OCam():
    CTRL_BRIGHTNESS	= ctypes.c_int(1)
    CTRL_CONTRAST	= ctypes.c_int(2)
    CTRL_HUE		= ctypes.c_int(3)
    CTRL_SATURATION	= ctypes.c_int(4)
    CTRL_EXPOSURE       = ctypes.c_int(5)
    CTRL_GAIN           = ctypes.c_int(6)
    CTRL_WB_BLUE        = ctypes.c_int(7)
    CTRL_WB_RED         = ctypes.c_int(8)
    def __init__(self):
        try:
            if platform.architecture()[0] == '64bit':
                self.mydll = ctypes.cdll.LoadLibrary("./libCamCap-amd64.dll")
                #self.mydll = ctypes.CDLL(".\\libCamCap-amd64.dll")
            else:
                self.mydll = ctypes.cdll.LoadLibrary(".\\libCamCap-x86.dll")
            self.mydll.CamGetDeviceInfo.restype = ctypes.c_char_p
            self.mydll.CamOpen.restype = ctypes.POINTER(ctypes.c_int)
        except WindowsError as Error:
            print (Error)
            raise Exception('libCamCap-amd64.dll or libCamCap-x86.dll not found')
            
        self.cam = None
        self.resolution = (0,0)
            

    def GetConnectedCamNumber(self):
        return int(self.mydll.GetConnectedCamNumber())

    def CamGetDeviceInfo(self, devno):
        info = dict()
        for idx, param in enumerate(('USB_Port', 'SerialNo', 'oCamName', 'FWVersion')):
            info[param] = self.mydll.CamGetDeviceInfo(int(devno), idx+1)
        return info
    
    def CamGetDeviceList(self):
        CamCount = self.GetConnectedCamNumber()
        DeviceList = list()
        for idx in range(CamCount):
            dev = self.CamGetDeviceInfo(idx)
            dev['devno'] = idx
            DeviceList.append(dev)
        return DeviceList
            
    def CamStart(self):
        if self.cam == None: return 
        ret = self.mydll.CamStart(self.cam)

    def CamGetImage(self):
        if self.cam == None: return 0, None
        ret = self.mydll.CamGetImage(self.cam, ctypes.c_char_p(self.bayer.ctypes.data))
        if ret == 1:
            return True, self.bayer
        else:
            return False, None  

    def CamStop(self):
        if self.cam == None: return
        ret = self.mydll.CamStop(self.cam)

    def CamClose(self):
        if self.cam == None: return
        ret = self.mydll.CamClose(ctypes.byref(self.cam))
        self.cam = None

    def CamGetCtrl(self, ctrl):
        if self.cam == None: return
        val = ctypes.c_int()
        ret = self.mydll.CamGetCtrl(self.cam, ctrl, ctypes.byref(val))
        return val.value
    
    def CamSetCtrl(self, ctrl, value):
        if self.cam == None: return
        val = ctypes.c_int()
        val.value = value
        ret = self.mydll.CamSetCtrl(self.cam, ctrl, val)

    def CamGetCtrlRange(self, ctrl):
        if self.cam == None: return
        val_min = ctypes.c_int()
        val_max = ctypes.c_int()
        ret = self.mydll.CamGetCtrlRange(self.cam, ctrl, ctypes.byref(val_min), ctypes.byref(val_max))            
        return val_min.value, val_max.value

    def CamOpen(self, DevNo=0, FramePerSec=5, Resolution=(4896,3672), BytePerPixel=1):
        try:
            devno = DevNo
            (w, h) = Resolution
            pixelsize = BytePerPixel
            fps = FramePerSec
            self.resolution = (w, h)
            self.cam = self.mydll.CamOpen(ctypes.c_int(devno), ctypes.c_int(w), ctypes.c_int(h), 
                                          ctypes.c_double(fps), 0, 0)
            self.bayer = np.zeros((h,w,pixelsize), dtype=np.uint8)
            #self.bayer = np.zeros((h,w*2), dtype=np.uint8)
            return True
        except WindowsError:
            return False
        
# CTRL_PARAM = {
#     'Brightness':myCamCapture.CTRL_BRIGHTNESS,
#     'Contrast':myCamCapture.CTRL_CONTRAST,
#     'Hue':myCamCapture.CTRL_HUE,
#     'Saturation':myCamCapture.CTRL_SATURATION,
#     'Exposure':myCamCapture.CTRL_EXPOSURE,
#     'Gain':myCamCapture.CTRL_GAIN,
#     'WB Blue':myCamCapture.CTRL_WB_BLUE,
#     'WB Red':myCamCapture.CTRL_WB_RED
# }

import cv2
        
if __name__ == "__main__":
    ocam = OCam()
    ocam.CamOpen(DevNo=0, Resolution=(4896,3672), FramePerSec=10, BytePerPixel=1)
    ocam.CamSetCtrl(ocam.CTRL_EXPOSURE, -4)
    
    ocam.CamStart()
    
    if ocam.GetConnectedCamNumber() == 0:
        print("oCam not Found...")
        exit()
        
    cv2.namedWindow('18CRN', cv2.WINDOW_NORMAL)
    
    
    font=cv2.FONT_HERSHEY_SIMPLEX
    while True:
        start = time.time()
        
        ret, frame = ocam.CamGetImage()
        if not ret: 
            print("ret : false")
            continue 
        color = cv2.cvtColor(frame, cv2.COLOR_BAYER_GR2BGR)
        color[:,:,1] = color[:,:,1]*0.8
        
        end = time.time()
        real_fps = round(1/(end-start))
        cv2.putText(color, f"fps : {real_fps}", (50,100), font, 3, (255,0,0), 5)
        
        cv2.imshow('18CRN', color)
        if cv2.waitKey(1) % 0xff == ord('q'): break
    
    
    cv2.destroyAllWindows()
    ocam.CamStop()
    ocam.CamClose()