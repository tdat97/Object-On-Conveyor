import stapipy as st
import numpy as np
import cv2
import time

class SentechCam():
    def __init__(self, light_serial=None, logger=None, ExposureTime=10000, AcquisitionMode="SingleFrame"):
        self.light_serial = light_serial
        self.logger = logger
        self.ExposureTime = ExposureTime
        self.AcquisitionMode = AcquisitionMode
        
        st.initialize()
        st_system = st.create_system()
        self.st_device = st_system.create_first_device()
        self.set_configure()
        if self.logger is not None:
            self.logger.debug(f"Device:{self.st_device.info.display_name}")
            
        self.st_datastream = self.st_device.create_datastream()
        self.st_datastream.start_acquisition()
        
        self.img_shape = self.get_image().shape
        
    def get_image(self):
        # start = time.time()
        
        self.st_device.acquisition_start()
        with self.st_datastream.retrieve_buffer() as st_buffer:
            if not st_buffer.info.is_image_present:
                if self.logger is not None:
                    self.logger.error("st_buffer.info.is_image_present : False !!")
                self.st_device.acquisition_stop()
                return None
            st_image = st_buffer.get_image()
            st_image = st_buffer.get_image()
            pixel_format = st_image.pixel_format
            pixel_format_info = st.get_pixel_format_info(pixel_format)

            data = st_image.get_image_data()

            if pixel_format_info.each_component_total_bit_count > 8:
                nparr = np.frombuffer(data, np.uint16)
                division = pow(2, pixel_format_info
                               .each_component_valid_bit_count - 8)
                nparr = (nparr / division).astype('uint8')
            else:
                nparr = np.frombuffer(data, np.uint8)

            # Process image for display.
            nparr = nparr.reshape(st_image.height, st_image.width, 1)

            # Perform color conversion for Bayer.
            if pixel_format_info.is_bayer:
                bayer_type = pixel_format_info.get_pixel_color_filter()
                if bayer_type == st.EStPixelColorFilter.BayerRG:
                    nparr = cv2.cvtColor(nparr, cv2.COLOR_BAYER_RG2RGB)
                elif bayer_type == st.EStPixelColorFilter.BayerGR:
                    nparr = cv2.cvtColor(nparr, cv2.COLOR_BAYER_GR2RGB)
                elif bayer_type == st.EStPixelColorFilter.BayerGB:
                    nparr = cv2.cvtColor(nparr, cv2.COLOR_BAYER_GB2RGB)
                elif bayer_type == st.EStPixelColorFilter.BayerBG:
                    nparr = cv2.cvtColor(nparr, cv2.COLOR_BAYER_BG2RGB)
        
        self.st_device.acquisition_stop()
        # end = time.time()
        
        # if self.logger is not None:
        #     self.logger.debug(f"Shot Time : {end-start:.4f}")
            
        return nparr # RGB 라는데 BGR 임
    
    def set_configure(self):
        nodemap = self.st_device.remote_port.nodemap
        node = nodemap.get_node("ExposureTime")
        st.PyIFloat(node).set_value(self.ExposureTime)
        node = nodemap.get_node("AcquisitionMode")
        st.PyIEnumeration(node).set_symbolic_value(self.AcquisitionMode)
        
        if self.logger is not None:
            self.logger.debug(f"ExposureTime:{self.ExposureTime}, AcquisitionMode:{self.AcquisitionMode}")
        

        
        
        
import platform
import ctypes
import numpy as np
import time
import cv2
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
            color = cv2.cvtColor(self.bayer, cv2.COLOR_BAYER_GR2BGR)
            color[:,:,1] = color[:,:,1]*0.8
            return color.astype(np.uint8)
        else:
            return None  

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
            self.img_shape = (h, w, 3)
            self.cam = self.mydll.CamOpen(ctypes.c_int(devno), ctypes.c_int(w), ctypes.c_int(h), 
                                          ctypes.c_double(fps), 0, 0)
            self.bayer = np.zeros((h,w,pixelsize), dtype=np.uint8)
            #self.bayer = np.zeros((h,w*2), dtype=np.uint8)
            return True
        except WindowsError:
            return False