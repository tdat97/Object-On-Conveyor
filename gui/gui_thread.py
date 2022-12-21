from utils.camera import SentechCam
from utils.logger import logger
from utils import tool
from PIL import ImageTk, Image
import serial


# Load Devices#########################################################
EXPOSURE_TIME = 2500
SERIAL_PORT = "COM1"

def get_cam(self, exposure_time):
    try:
        cam = SentechCam(logger=logger, ExposureTime=exposure_time)
        for _ in range(3): cam.get_image()
        
        self.cam = cam
        logger.info("Cam Started.")
        self.write_sys_msg("Cam Started")
    except Exception as e:
        logger.error(e)
        self.write_sys_msg(e)
        self.stop_signal = True

def get_serial(self, port):
    try:
        my_serial = serial.Serial(port, 9600, timeout=0, bytesize=serial.EIGHTBITS, 
                                  stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_ODD)
        
        time.sleep(1.2)
        my_serial.write(b'r')
        time.sleep(0.05)
        if my_serial.read(1) == b'': 
            raise Exception("Serial is unresponsive.")
        
        self.serial = my_serial
        logger.info("Serial Opened.")
        self.write_sys_msg("Serial Opened.")
    except Exception as e:
        logger.error(e)
        self.write_sys_msg(e)
        self.stop_signal = True

def device_check(self)
    while not self.stop_signal:
        time.sleep(0.05)
        if self.cam is not None and self.serial is not None:            
            self.button1.configure(text="판독모드", command=self.read_mode)
            self.button2.configure(text="촬영모드", command=self.snap_mode)
            self.button3.configure(text="학습모드", command=self.train_mode)
            break

    text = f"Cam state : {bool(self.cam)}   Serial state : {bool(self.serial)}"
    self.write_sys_msg(text)

# 실시간 이미지 조정####################################################
def image_eater(self): # 쓰레드 # self.image_Q에 있는 이미지 출력
    current_winfo = self.image_frame.winfo_width(), self.image_frame.winfo_height()
    while True:
        time.sleep(0.02)
        if self.stop_signal: break
        last_winfo = self.image_frame.winfo_width(), self.image_frame.winfo_height()
            
        if current_winfo == last_winfo and self.image_Q.empty(): continue
        if current_winfo != last_winfo: current_winfo = last_winfo
        if not self.image_Q.empty(): self.current_origin_image = self.image_Q.get()[:,:,::-1]
        if self.current_origin_image is None: continue
            
        __auto_resize_img(self)
        imgtk = ImageTk.PhotoImage(Image.fromarray(self.current_image))
        self.image_label.configure(image=imgtk)
        self.image_label.image = imgtk

def __auto_resize_img(self):
    h, w = self.current_origin_image.shape[:2]
    ratio = h/w
    wh = self.image_frame.winfo_height() - 24
    ww = self.image_frame.winfo_width() - 24
    wratio = wh/ww
        
    if ratio < wratio: size, target = ww, 'w'
    else: size, target = wh, 'h'
    self.current_image = tool.fix_ratio_resize_img(self.current_origin_image, size=size, target=target)

# 실시간 데이터 수정####################################################
def data_eater(self):
    while not self.stop_signal:
        time.sleep(0.02)
        if self.data_Q.empty(): continue
            
        code = self.data_Q.get()
        self.code2cnt[code] += 1
        update_gui(self, code)

def update_gui(self, code, init=False):
    # day_cnt gui
    day_cnt_all = sum(self.code2cnt.values())
    day_cnt_ng = self.code2cnt[None]
    day_cnt_ok = day_cnt_all - day_cnt_ng
    self.day_cnt_all.configure(text=day_cnt_all)
    self.day_cnt_ok.configure(text=day_cnt_ok)
    self.day_cnt_ng.configure(text=day_cnt_ng)
    if init: return
        
    # single_cnt
    if code is None: name = "인식실패"
    elif code in self.code2name: name = self.code2name[code]
    else: name = "새로운 제품"
    self.name_label.configure(text=name)
    self.single_cnt.configure(text=self.code2cnt[code])
     
    # OK, NG
    if code: self.ok_label.configure(text='OK', fg='#6f6')
    else: self.ok_label.configure(text='NG', fg='#f00')
    
#######################################################################
#######################################################################
#######################################################################
#######################################################################
#######################################################################
#######################################################################















