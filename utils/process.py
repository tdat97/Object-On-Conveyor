from utils.logger import logger
from utils.detect_code import get_qrcode, get_barcode, draw_box_text
from utils import tool
import numpy as np
import time
import cv2
import os

#SAVE_PATH = "./image"
#path = os.path.join(SAVE_PATH, "anno")
#if not os.path.isdir(path): os.mkdir(path)
#path = os.path.join(SAVE_PATH, "debug")
#if not os.path.isdir(path): os.mkdir(path)
#path = os.path.join(SAVE_PATH, "raw")
#if not os.path.isdir(path): os.mkdir(path)
#path = os.path.join(SAVE_PATH, "not_found")
#if not os.path.isdir(path): os.mkdir(path)



def read(self):
    try:
        while not self.stop_signal::
            time.sleep(0.01)
            start_time = time.time()
            
            # get image
            if self.raw_Q.empty(): continue
            img = self.raw_Q.get()
            
            self.image_Q.put(img)
            self.data_Q.put(data) #########
            self.db_Q.put([data, path])
        
    except Exception as e:
        logger.error(f"[process]{e}")
        self.write_sys_msg(e)
        self.stop_signal = True
