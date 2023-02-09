from gui import configure, gui_thread as gthr
from utils import tool, process, device#, db
from utils.poly import MultiPolyDetector
from utils.logger import logger
from utils.text import *

from collections import defaultdict
import tkinter as tk
import tkinter.filedialog as filedialog
import numpy as np
import cv2
from queue import Queue
from threading import Thread, Lock
import time
import serial
import os

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
        self.fsize_factor = np.linalg.norm((self.screenheight, self.screenwidth)) / 2202.9071700822983
        self.thr_lock = Lock() # lock.acquire() lock.release()
        
        # 디자인
        configure(self)
        self.button1.configure(text="", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))

        # 기타 변수 초기화
        self.current_origin_image = None #np.zeros((100,100,3), dtype=np.uint8)
        self.current_image = None
        self.not_found_path = SAVE_NG_IMG_DIR
        self.sys_msg_list = []
        # self.area_box = np.array([[0.45, 0.0], [0.55, 1.0]]) # xyxy
        # self.area_box2 = np.array([[0.40, 0.0], [0.60, 1.0]]) # xyxy
        self.write_sys_msg("test")
        self.write_sys_msg("Loading...")

        # 쓰레드 통신용
        self.stop_signal = True
        self.raw_Q = Queue()
        self.analy_Q = Queue()
        self.draw_Q = Queue()
        self.image_Q = Queue()
        self.data_Q = Queue()
        self.db_Q = Queue()
        self.pair_Q = Queue()
        self.enter_Q = Queue()
        self.recode_Q = Queue()

        # db 정보 가져오기
        #self.connection, self.cursor = db.connect_db()
        #self.code2name, self.code2cnt = db.load_db(self) # (dict, defaultdict) # 카운트는 오늘 날짜만 가져와서 카운트
        #logger.info("Loaded DB.")

        # 판독자 초기화
        self.poly_detector = MultiPolyDetector(IMG_DIR_PATH, JSON_DIR_PATH)
        
        # 초기정보 적용
        self.name2cnt = defaultdict(int)
        self.init_gui_data()
        self.make_recode_dir()
        

        # 카메라, 보드 연결
        self.cam = None
        self.serial = None
        self.load_devices()
            
    #######################################################################
    def write_sys_msg(self, msg, maxlen=4):
        msg = tool.get_time_str(True).split(' ')[-1] + " >>> " + str(msg)
        self.sys_msg_list.append(msg)
        if len(self.sys_msg_list) > maxlen: self.sys_msg_list.pop(0)
        
        msg_concat = '\n'.join(self.sys_msg_list)
        self.msg_label.configure(text=msg_concat)
    
    #######################################################################
    def load_devices(self):
        Thread(target=gthr.device_check, args=(self,), daemon=True).start()

    #######################################################################
    def init_button_(self):
        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="판독모드", command=self.read_mode)
        self.button2.configure(text="촬영모드", command=self.snap_mode)
        self.button3.configure(text="학습모드", command=self.train_mode)
    
    #######################################################################
    def init_gui_data(self):        
        # 전체통계
        cnt_all = sum(self.name2cnt.values())
        cnt_ng = self.name2cnt[None]
        cnt_ok = cnt_all - cnt_ng
        self.total_ffl1.configure(text=cnt_all)
        self.total_ffl2.configure(text=cnt_ng)
        self.total_ffl3.configure(text=cnt_ok)
        
        # 세부통계
        self.listbox1.delete(0, 'end')
        self.listbox2.delete(0, 'end')
        for i, name in enumerate(self.poly_detector.names):
            self.listbox1.insert(i, name)
            self.listbox2.insert(i, self.name2cnt[name])
        self.listbox1.insert(len(self.poly_detector.names), "NG")
        self.listbox2.insert(len(self.poly_detector.names), self.name2cnt[None])
        
        # 현재 제품 정보
        self.objinfo.configure(text="")
        
    #######################################################################
    def make_recode_dir(self):
        if not os.path.isdir(SAVE_IMG_DIR): os.mkdir(SAVE_IMG_DIR)
        if not os.path.isdir(SAVE_RAW_IMG_DIR): os.mkdir(SAVE_RAW_IMG_DIR)
        if not os.path.isdir(SAVE_OK_IMG_DIR): os.mkdir(SAVE_OK_IMG_DIR)
        if not os.path.isdir(SAVE_NG_IMG_DIR): os.mkdir(SAVE_NG_IMG_DIR)
        if not os.path.isdir(SAVE_DEBUG_IMG_DIR): os.mkdir(SAVE_DEBUG_IMG_DIR)
    
    #######################################################################
    def stop(self):
        self.write_sys_msg("중지.")
        logger.info("Stop button clicked.")
        self.stop_signal = True
        # self.serial.write(LIGHT_OFF)

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
        tool.clear_Q(self.raw_Q)
        tool.clear_Q(self.analy_Q)
        tool.clear_Q(self.draw_Q)
        tool.clear_Q(self.image_Q)
        tool.clear_Q(self.data_Q)
        tool.clear_Q(self.recode_Q)
        tool.clear_serial(self.serial)
        
        Thread(target=gthr.image_eater, args=(self,), daemon=True).start()
        Thread(target=gthr.data_eater, args=(self,), daemon=True).start()
        Thread(target=process.snaper, args=(self,), daemon=True).start()
        Thread(target=process.read, args=(self,), daemon=True).start()
        Thread(target=process.analysis, args=(self,), daemon=True).start()
        Thread(target=process.draw, args=(self,), daemon=True).start()
        Thread(target=process.recode, args=(self,), daemon=True).start()

        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="중지", command=self.stop)
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        
        self.write_sys_msg("판독모드 시작!")
        
        while not self.stop_signal: time.sleep(0.01)
        self.object_names = None
        self.thr_lock.acquire()
        self.serial.write(BYTES_DIC["light_off"])
        self.thr_lock.release()
        self.init_button_()
        self.ok_label.configure(text='NONE', fg='#ff0', bg='#333', anchor='center')
        self.objinfo.configure(text="")
        

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
        tool.clear_Q(self.image_Q)
        tool.clear_serial(self.serial)
        
        Thread(target=gthr.image_eater, args=(self,), daemon=True).start()
        Thread(target=process.raw_Q2image_Q, args=(self,), daemon=True).start()

        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="중지", command=self.stop)
        self.button2.configure(text="촬영", command=lambda:process.snap(self))
        self.button3.configure(text="저장", command=self.save)

        self.write_sys_msg("촬영모드 시작!")
        
        while not self.stop_signal: time.sleep(0.01)
        self.init_button_()
        self.thr_lock.acquire()
        self.serial.write(BYTES_DIC["light_off"])
        self.thr_lock.release()
    
    def save(self):
        logger.info("Save button clicked.")
        if self.current_origin_image is None: return
        filename = filedialog.asksaveasfilename(initialdir=os.getcwd(), title="이미지 저장",
                                          filetypes=(("IMG files", "*.jpg"), ))
        filename = filename.split(".jpg")[0]
        if filename:
            res = tool.imwrite(f"{filename}.jpg", self.current_origin_image)
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
        # init
        self.input_name.delete(0, "end")
        self.input_name.bind("<Return>", self.name_enter_save)
        tool.clear_Q(self.raw_Q)
        tool.clear_Q(self.image_Q)
        tool.clear_Q(self.pair_Q)
        tool.clear_Q(self.enter_Q)
        tool.clear_serial(self.serial)
        
        Thread(target=gthr.image_eater, args=(self,), daemon=True).start()
        Thread(target=process.snaper, args=(self,), daemon=True).start()
        Thread(target=process.train, args=(self,), daemon=True).start()
        Thread(target=process.json_saver, args=(self,), daemon=True).start()
        Thread(target=process.recode, args=(self,), daemon=True).start()
        

        self.button1.configure(text="Waiting...", command=lambda:time.sleep(0.1))
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.button1.configure(text="중지", command=self.stop)
        self.button2.configure(text="", command=lambda:time.sleep(0.1))
        self.button3.configure(text="", command=lambda:time.sleep(0.1))

        self.write_sys_msg("학습모드 시작!")
        self.write_sys_msg("정방향으로 촬영되도록 해주세요.")
        self.write_sys_msg("촬영후 라벨 입력뒤 엔터를 누르면 등록됩니다.")
        
        # OK,NG 부분에 입력칸
        self.ok_label.place_forget()
        self.input_name.place(relx=0.05, rely=0.3, relwidth=0.9, relheight=0.5)
        
        while not self.stop_signal: time.sleep(0.01)
        self.init_button_()
        self.thr_lock.acquire()
        self.serial.write(BYTES_DIC["light_off"])
        self.thr_lock.release()
        
        # 입력칸 부분에 OK,NG
        self.input_name.place_forget()
        self.ok_label.place(relx=0.0, rely=0.2, relwidth=1, relheight=0.8)
        self.ok_label.configure(text='NONE', fg='#ff0', bg='#333', anchor='center')

    #######################################################################
    # 입력창에서 Enter 했을때
    def name_enter_save(self, _):
        name = self.input_name.get()
        
        if self.current_origin_image is None: 
            self.write_sys_msg("제품을 촬영해주세요.")
            return
        if not name: 
            self.write_sys_msg("제품이름을 입력해주세요.")
            return
        
        # 전송
        self.enter_Q.put(name)
        # 지우기
        self.input_name.delete(0, "end")
        
            
    #######################################################################
    def go_directory(self, path):
        path = os.path.realpath(path)
        os.startfile(path)
        
    #######################################################################



























        
