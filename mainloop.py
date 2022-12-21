from gui import configure, gui_thread as gthr
from utils import tool, process, db

from utils.logger import logger
from collections import defaultdict
import tkinter as tk
import tkinter.filedialog as filedialog

import numpy as np
import cv2
from queue import Queue
from threading import Thread
import time
import serial
import os


TITLE = "Machine Vision System"
ICON_PATH = "./gui/eye.ico"


class VisualControl():
    def __init__(self, root):
        self.root = root
        self.root.iconbitmap(ICON_PATH)
        self.screenheight = self.root.winfo_screenheight()
        self.screenwidth = self.root.winfo_screenwidth()
        self.root.title(TITLE)
        self.root.state("zoomed")
        self.root.geometry(f"{self.screenwidth//3*2}x{self.screenheight//3*2}")
        self.root.minsize(self.screenwidth//3*2, self.screenheight//3*2)
        self.fsize_factor = np.linalg.norm((self.screenheight, self.screenwidth))
        
        # 디자인
        configure(self)
        self.button1.configure(text="", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))

        # 기타 변수 초기화
        self.current_origin_image = None#np.zeros((100,100,3), dtype=np.uint8)
        self.current_image = None
        #self.not_found_path = NOT_FOUND_PATH
        self.sys_msg_list = []
        self.write_sys_msg("Loading...")

        # 쓰레드 통신용
        self.stop_signal = True
        self.raw_Q = Queue()
        self.image_Q = Queue()
        self.data_Q = Queue()
        self.db_Q = Queue()

        # db 정보 가져오기
        #self.connection, self.cursor = db.connect_db()
        #self.code2name, self.code2cnt = db.load_db(self) # (dict, defaultdict) # 카운트는 오늘 날짜만 가져와서 카운트
        #logger.info("Loaded DB.")

        # 초기정보 적용
        #self.update_gui(None, init=True)
        #self.single_cnt.configure(text='')

        # 카메라, 보드 연결
        self.cam = None
        self.serial = None
        self.load_devices()
            
    #######################################################################
    def write_sys_msg(self, msg):
        msg = tool.get_time_str(True) + " >>> " + str(msg)
        self.sys_msg_list.append(msg)
        if len(self.sys_msg_list) > 3: self.sys_msg_list.pop(0)
        
        msg_concat = '\n'.join(self.sys_msg_list)
        self.msg_label.configure(text=msg_concat)
    
    #######################################################################
    def load_devices(self):
        self.stop_signal = False
        Thread(target=gthr.get_cam, args=(self, EXPOSURE_TIME), daemon=True).start()
        Thread(target=gthr.get_serial, args=(self, SERIAL_PORT), daemon=True).start()
        Thread(target=gthr.device_check, args=(self,), daemon=True).start()

    #######################################################################
    def stop(self):
        self.write_sys_msg("중지.")
        logger.info("Stop button clicked.")
        self.stop_signal = True

    #######################################################################
    def read_mode(self):
        logger.info("read_mode button clicked.")
        if self.cam == None or self.serial == None:
            logger.error("device 로드 안됐는데 시작 버튼 눌림.")
            self.write_sys_msg("ERROR : device 로드 안됐는데 시작 버튼 눌림.")
            return

        self.stop_signal = False
        Thread(target=self.read_thread, args=(), daemon=True).start()

    def read_thread(self):
        tool.clear_serial(self.serial)
        tool.clear_Q(self.raw_Q)
        tool.clear_Q(self.image_Q)
        #tool.clear_Q(self.data_Q)
        #tool.clear_Q(self.db_Q)
        
        Thread(target=gthr.image_eater, args=(self,), daemon=True).start()
        #Thread(target=gthr.data_eater, args=(self,), daemon=True).start()
        Thread(target=process.sensor2shot, args=(self,), daemon=True).start()
        Thread(target=process.read, args=(self,), daemon=True).start()
        #Thread(target=db.db_process, args=(self,), daemon=True).start()

        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="중지", command=self.stop)
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        
        self.write_sys_msg("판독모드 시작!")
        
        while not self.stop_signal: time.sleep(0.01)
        
        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="판독모드", command=self.read_mode)
        self.button2.configure(text="촬영모드", command=self.snap_mode)
        self.button3.configure(text="학습모드", command=self.train_mode)

    #######################################################################
    def snap_mode(self):
        logger.info("SnapMode button clicked.")
        if self.cam == None or self.serial == None:
            logger.error("device 로드 안됐는데 시작 버튼 눌림.")
            self.write_sys_msg("ERROR : device 로드 안됐는데 시작 버튼 눌림.")
            return

        self.stop_signal = False
        Thread(target=self.snap_mode_thread, args=(), daemon=True).start()

    def snap_mode_thread(self):
        tool.clear_Q(self.raw_Q)
        
        Thread(target=gthr.image_eater, args=(), daemon=True).start()
        Thread(target=self.raw_Q2image_Q, args=(), daemon=True).start()

        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="중지", command=self.stop)
        self.button2.configure(text="촬영", command=lambda:process.raw_shot(self))
        self.button3.configure(text="저장", command=lambda:self.save)

        self.write_sys_msg("촬영모드 시작!")
        
        while not self.stop_signal: time.sleep(0.01)
        
        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="판독모드", command=self.read_mode)
        self.button2.configure(text="촬영모드", command=self.snap_mode)
        self.button3.configure(text="학습모드", command=self.train_mode)

    
    def save(self):
        logger.info("Save button clicked.")
        if self.current_origin_image is None: return
        filename = filedialog.asksaveasfilename(initialdir=os.getcwd(), title="이미지 저장",
                                          filetypes=(("IMG files", "*.jpg"), ))
        filename = filename.split(".jpg")[0]
        if filename:
            res = cv2.imwrite(f"{filename}.jpg", self.current_origin_image[:,:,::-1])
            text = "저장됨." if res else "저장실패."
            logger.info(f"{filename}.jpg " + text)
            self.write_sys_msg(text)

    #######################################################################
    def train_mode(self):
        logger.info("TrainMode button clicked.")
        if self.cam == None or self.serial == None:
            logger.error("device 로드 안됐는데 시작 버튼 눌림.")
            self.write_sys_msg("ERROR : device 로드 안됐는데 시작 버튼 눌림.")
            return

        self.stop_signal = False
        Thread(target=self.train_mode_thread, args=(), daemon=True).start()

    def train_mode_thread(self):
        tool.clear_Q(self.raw_Q)
        
        Thread(target=gthr.image_eater, args=(), daemon=True).start()
        Thread(target=process.sensor2shot, args=(self,), daemon=True).start()

        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="중지", command=self.stop)
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))

        self.write_sys_msg("학습모드 시작!")
        
        while not self.stop_signal: time.sleep(0.01)
        
        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="판독모드", command=self.read_mode)
        self.button2.configure(text="촬영모드", command=self.snap_mode)
        self.button3.configure(text="학습모드", command=self.train_mode)

    #######################################################################

    #######################################################################

    #######################################################################



























        
