from utils.logger import logger
from utils.text import *
from utils import tool, device
from collections import defaultdict
from shapely.geometry import Polygon
from PIL import ImageFont, ImageDraw, Image
from threading import Thread, Lock
import numpy as np
import time
import cv2
import os

from PIL import ImageTk, Image

bytes_dic = {"light_on"   : bytes([0xA0, 0x00, 0x01, 0xA0 ^ 0x00 ^ 0x01]),
             "light_off"  : bytes([0xA0, 0x00, 0x00, 0xA0 ^ 0x00 ^ 0x00]),
             "green_on"   : bytes([0xA0, 0x01, 0x01, 0xA0 ^ 0x01 ^ 0x01]),
             "green_off"  : bytes([0xA0, 0x01, 0x00, 0xA0 ^ 0x01 ^ 0x00]),
             "yellow_on"  : bytes([0xA0, 0x02, 0x01, 0xA0 ^ 0x02 ^ 0x01]),
             "yellow_off" : bytes([0xA0, 0x02, 0x00, 0xA0 ^ 0x02 ^ 0x00]),
             "red_on"     : bytes([0xA0, 0x03, 0x01, 0xA0 ^ 0x03 ^ 0x01]),
             "red_off"    : bytes([0xA0, 0x03, 0x00, 0xA0 ^ 0x03 ^ 0x00]),
             "get_sensor1": bytes([0xB0, 0x00, 0x00, 0xB0 ^ 0x00 ^ 0x00]),
             "get_sensor2": bytes([0xB0, 0x01, 0x00, 0xB0 ^ 0x01 ^ 0x00]),}

lock = Lock() # lock.acquire() lock.release()

#######################################################################
def snap(self):
    lock.acquire()
    self.serial.write(bytes_dic["light_on"])
    lock.release()
    
    time.sleep(0.2)
    # self.cam.set_exposure(2500)
    img = self.cam.get_image()
    
    lock.acquire()
    self.serial.write(bytes_dic["light_off"])
    lock.release()
    
    self.raw_Q.put(img)
    
#######################################################################
def snaper(self):
    sensor_lock = False
    
    while not self.stop_signal:
        time.sleep(0.05)
        
        lock.acquire()
        self.serial.write(bytes_dic["get_sensor1"])
        value = self.serial.read(4)
        lock.release()
        
        if not sensor_lock and value[0] != 0xff and value[2] == 0x01:
            snap(self)
            sensor_lock = True
        elif value[0] != 0xff and value[2] == 0x00:
            sensor_lock = False

#######################################################################
def raw_Q2image_Q(self): # 촬영모드 전용
    while not self.stop_signal:
        time.sleep(0.02)
        
        if self.raw_Q.empty(): continue
        self.image_Q.put(self.raw_Q.get())
        
#######################################################################
def read(self):
    try:
        self.poly_detector.update_check()

        while not self.stop_signal:
            time.sleep(0.01)

            # get image
            if self.raw_Q.empty(): continue
            img = self.raw_Q.get()

            # predict
            start_time = time.time()
            obj_info, dst_polys = self.poly_detector.predict(img)
            end_time = time.time()
            
            logger.info(f"Detect Time : {end_time-start_time:.3f}")
            self.analy_Q.put([img, obj_info, dst_polys])

            # save
            self.recode_Q.put([img, 'raw'])
            
    except Exception as e:
        logger.error(f"[read]{e}")
        self.write_sys_msg(e)
        self.stop_signal = True

#######################################################################
def analysis(self):
    try:
        while not self.stop_signal:
            time.sleep(0.01)

            # get img, detect
            if self.analy_Q.empty(): continue
            img, obj_info, dst_polys = self.analy_Q.get()
            
            poly = dst_polys[obj_info.labels.index("object")] if obj_info else None
            name = obj_info.name if obj_info else None
            
            self.data_Q.put(name)
            self.draw_Q.put([img.copy(), name, poly])
        
    except Exception as e:
        logger.error(f"[analysis]{e}")
        self.write_sys_msg(e)
        self.stop_signal = True
        
#######################################################################
def draw(self):
    fc = lambda x,y:np.random.randint(x,y)
    colors = [(fc(50,255), fc(50,255), fc(0,150)) for _ in range(len(self.poly_detector.names))]
    color_dic = dict(zip(self.poly_detector.names, colors))
    # font = cv2.FONT_HERSHEY_SIMPLEX
    font = ImageFont.truetype(FONT_PATH, 40)
    
    # img_shape = np.array(self.cam.img_shape[:2])[::-1] # xy
    
    try:
        while not self.stop_signal:
            time.sleep(0.01)

            # get img, names, marker, polys
            if self.draw_Q.empty(): continue
            img, name, poly = self.draw_Q.get()
            if poly is not None:
                poly = poly.astype(np.int32)

            # draw area box # cv2에서는 BGR이지만 카메라로 촬영한 이미지이기 때문에 (255,0,0) -> Red
            # cv2.rectangle(img, real_area_box[0], real_area_box[1], (255,0,0), 3)

            # draw poly
            color = color_dic[name] if name else (255,255,0)
            cv2.polylines(img, [poly], True, color, thickness=5)
            if name is None:
                self.image_Q.put(img)
                self.recode_Q.put([img, name])
                continue

            # draw points
            cv2.putText(img, '1', poly[0], cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=1, color=(255,0,255))
            cv2.putText(img, '2', poly[1], cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=1, color=(255,0,255))
            cv2.putText(img, '3', poly[2], cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=1, color=(255,0,255))
            cv2.putText(img, '4', poly[3], cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=1, color=(255,0,255))

            # draw name
            x,y = poly[0]
            y -= 40
            img_pil = Image.fromarray(img)
            img_draw = ImageDraw.Draw(img_pil)
            img_draw.text((x,y), name, font=font, fill=(*color, 0))
            img = np.array(img_pil)

            self.image_Q.put(img)
            self.recode_Q.put([img, name])
        
    except Exception as e:
        logger.error(f"[draw]{e}")
        self.write_sys_msg(e)
        self.stop_signal = True


#######################################################################
def train(self):
    font = cv2.FONT_HERSHEY_SIMPLEX
    kernel = np.ones((3,3))
    
    while not self.stop_signal:
        time.sleep(0.01)

        # get image
        if self.raw_Q.empty(): continue
        img = self.raw_Q.get()
        img_copy = img.copy()
        
        # 이미지에서 제품 Polygon 따기
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        img_mask = cv2.inRange(img_hsv, (0, 0, 20), (360, 255, 255)) # 50 -> 20
        img_mask = cv2.erode(img_mask, kernel, iterations=3)
        img_mask = cv2.dilate(img_mask, kernel, iterations=3)
        polys = tool.find_polys_in_img(img_mask)
        if polys is None:
            self.write_sys_msg(f"이미지 인식 실패. 다시 시도해주세요.")
            continue
        poly = polys[0]
        
            
        # 그리기
        clock_poly = tool.poly2clock(poly)
        cv2.polylines(img_copy, [clock_poly], True, (255,255,255), thickness=5)
        cv2.putText(img_copy, '1', clock_poly[0], font, fontScale=1, thickness=1, color=(255,0,255))
        cv2.putText(img_copy, '2', clock_poly[1], font, fontScale=1, thickness=1, color=(255,0,255))
        cv2.putText(img_copy, '3', clock_poly[2], font, fontScale=1, thickness=1, color=(255,0,255))
        cv2.putText(img_copy, '4', clock_poly[3], font, fontScale=1, thickness=1, color=(255,0,255))
        
                
        self.pair_Q.put([img, clock_poly])
        self.image_Q.put(img_copy)
        
def json_saver(self):
    img, poly, name = None, None, None
    
    while not self.stop_signal:
        time.sleep(0.05)
        
        # 데이터 받기
        if not self.pair_Q.empty():
            img, poly = self.pair_Q.get()
        if not self.enter_Q.empty():
            name = self.enter_Q.get()
            
        if img is None or name is None: continue
        
        # 데이터 받은 후
        path = os.path.join(IMG_DIR_PATH, f"{name}.jpg")
        tool.imwrite(path, img)
        path = os.path.join(JSON_DIR_PATH, f"{name}.json")
        tool.poly2json(path, ["object"], [poly])
        self.write_sys_msg(f"[{name}] 등록되었습니다.")
        logger.info(f"[{name}] applied.")
        self.poly_detector.update_check()
        self.init_gui_data()
        
        # 이미지 초기화
        img, poly, name = None, None, None
        
        self.current_origin_image = None
        self.current_image = None
        
        imgtk = ImageTk.PhotoImage(Image.fromarray(np.zeros((10,10,3), dtype=np.uint8)))
        self.image_label.configure(image=imgtk)
        self.image_label.image = imgtk
        del imgtk
        self.image_label.configure(image=None)
        self.image_label.image = None
        
#######################################################################
def recode(self):
    dir_dic = {'raw':SAVE_RAW_IMG_DIR, 'debug':SAVE_DEBUG_IMG_DIR, None:SAVE_NG_IMG_DIR}
    for name in self.poly_detector.names:
        dir_dic[name] = os.path.join(SAVE_OK_IMG_DIR, name)
        if not os.path.isdir(dir_dic[name]): os.mkdir(dir_dic[name])
    
    while not self.stop_signal:
        time.sleep(0.01)
        
        if self.recode_Q.empty(): continue
        img, name = self.recode_Q.get()
        file_name = f"{tool.get_time_str()}.jpg"
        
        # save
        if len(img.shape) == 2:
            img = cv2.merge([img,img,img])
        path = os.path.join(dir_dic[name], file_name)
        tool.imwrite(path, img)
        tool.manage_file_num(dir_dic[name])
        
            
        

#######################################################################
#######################################################################
#######################################################################
#######################################################################
#######################################################################
#######################################################################











