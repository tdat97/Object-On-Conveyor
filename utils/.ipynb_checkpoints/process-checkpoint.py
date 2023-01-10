from utils.logger import logger
from utils.text import *
from utils import tool, device
from collections import defaultdict
from shapely.geometry import Polygon
from PIL import ImageFont, ImageDraw, Image
from threading import Thread
import numpy as np
import time
import cv2
import os

from PIL import ImageTk, Image

#######################################################################
def auto_light_cam_(self, offset=0.02):
    before_light_on = False
    light_on = False
    before_ratio = 0
    before_img = np.zeros(self.cam.img_shape, dtype=np.uint8)
    
#     img_t0 = cam.get_image()
#     my_serial.write(LIGHT_ON)

#     time.sleep(0.2)
#     img_t1 = cam.get_image()
#     my_serial.write(LIGHT_OFF)
    
    
    while not self.stop_signal:
        time.sleep(0.01)
        # 가져갈때까지 대기
        # if not self.raw_Q.empty(): continue
        if 1 < self.raw_Q.qsize(): continue
        
        # 촬영
        img = self.cam.get_image()
        if img is None: continue
        
        # 동작 감지에 따른 조명 동작 # 2연속 조건 만족해야 동작
        diff_img = tool.get_diff_img(before_img, img)
        ratio = tool.diff2ratio(diff_img)
        

        if not light_on and ratio > offset and before_ratio > offset:
            light_on = True
            self.serial.write(LIGHT_ON)
            time.sleep(0.15)
        if light_on and ratio <= offset and before_ratio <= offset:
            light_on = False
            self.serial.write(LIGHT_OFF)
            time.sleep(0.15)
            
        # 조명 켜져있을때만 보내기
        if light_on and before_light_on and ratio > offset:
            self.raw_Q.put([img, diff_img])

        before_light_on = light_on
        before_img = img
        before_ratio = ratio
    
#######################################################################
def auto_light_cam(self, offset=0.02):
    before_light_on = False
    light_on = False
    before_ratio = 0
    exp_time = {True:2500, False:25000}
    
    self.cam.set_exposure(25000)
    img_off = self.cam.get_image()
    self.serial.write(LIGHT_ON)

    time.sleep(0.2)
    self.cam.set_exposure(2500)
    img_on = self.cam.get_image()
    self.serial.write(LIGHT_OFF)
    
    if img_off is None or img_on is None:
        logger.error("img is None.")
        self.write_sys_msg("img is None.")
        self.stop_signal = True
        return
    
    
    while not self.stop_signal:
        time.sleep(0.01)
        # 가져갈때까지 대기
        # if not self.raw_Q.empty(): continue
        if 1 < self.raw_Q.qsize(): continue
        
        # 촬영
        self.cam.set_exposure(exp_time[light_on])
        img = self.cam.get_image()
        if img is None: continue
        
        # 동작 감지에 따른 조명 동작 # 2연속 조건 만족해야 동작
        img_bg = img_on if light_on else img_off
        diff_img = tool.get_diff_img(img_bg, img)
        ratio = tool.diff2ratio(diff_img)
        

        if not light_on and ratio > offset and before_ratio > offset:
            light_on = True
            self.serial.write(LIGHT_ON)
            time.sleep(0.15)
        if light_on and ratio <= offset and before_ratio <= offset:
            light_on = False
            self.serial.write(LIGHT_OFF)
            time.sleep(0.15)
            
        # 조명 켜져있을때만 보내기
        if light_on and before_light_on and ratio > offset:
            self.raw_Q.put([img, diff_img])

        before_light_on = light_on
        before_ratio = ratio
    
#######################################################################
def read(self):
    try:
        self.poly_detector.update_check()
        lock = False

        while not self.stop_signal:
            time.sleep(0.01)
            start_time = time.time()

            # get image
            if self.raw_Q.empty(): continue
            img, diff_img = self.raw_Q.get()

            # check center in area
            diff_polys = tool.find_polys_in_img(diff_img)
            if diff_polys is None: continue
            diff_poly = diff_polys[0]
            diff_center = np.mean(diff_poly, axis=0)
            size = np.array(diff_img.shape[:2])[::-1] # xy
            locs = diff_center / size
            is_center = np.all((self.area_box[0] < locs) & (locs < self.area_box[1]))
            is_center2 = np.all((self.area_box2[0] < locs) & (locs < self.area_box2[1]))

            if not is_center2: lock = False; continue
            if lock or not is_center: continue
            lock = True

            # predict
            obj_info, dst_polys = self.poly_detector.predict(img)

            end_time = time.time()
            logger.info(f"Detect Time : {end_time-start_time:.3f}")
            self.analy_Q.put([img, obj_info, dst_polys, diff_poly])

            # save
            self.recode_Q.put([img, 'raw'])
            if obj_info is None: self.recode_Q.put([diff_img, 'debug'])
            
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
            img, obj_info, dst_polys, diff_poly = self.analy_Q.get()
            
            # get iou
            if obj_info is not None:
                i = obj_info.labels.index("object")
                poly1 = Polygon(dst_polys[i])
                poly2 = Polygon(diff_poly)
                iou = poly1.intersection(poly2).area / poly1.union(poly2).area
                if iou < 0.7: obj_info, dst_polys = None, None
            
            poly = dst_polys[obj_info.labels.index("object")] if obj_info else diff_poly
            name = obj_info.name if obj_info else None
            
            self.data_Q.put(name)
            self.draw_Q.put([img.copy(), name, poly, diff_poly])
        
    except Exception as e:
        logger.error(f"[analysis]{e}")
        self.write_sys_msg(e)
        self.stop_signal = True
        
#######################################################################
def draw(self):
    fc = lambda x,y:np.random.randint(x,y)
    colors = [(fc(50,255), fc(50,255), fc(0,150)) for _ in range(len(self.poly_detector.names))]
    # colors = list(map(lambda x:tuple(map(int,x)), np.random.randint(0, 255, size=(4,3))))
    color_dic = dict(zip(self.poly_detector.names, colors))
    # font = cv2.FONT_HERSHEY_SIMPLEX
    font = ImageFont.truetype(FONT_PATH, 40)
    
    # img_shape = np.array(self.cam.img_shape[:2])[::-1] # xy
    # real_area_box = (self.area_box * img_shape).astype(np.int32)
    
    try:
        while not self.stop_signal:
            time.sleep(0.01)

            # get img, names, marker, polys
            if self.draw_Q.empty(): continue
            img, name, poly, diff_poly = self.draw_Q.get()
            poly = poly.astype(np.int32)

            # draw area box # cv2에서는 BGR이지만 카메라로 촬영한 이미지이기 때문에 (255,0,0) -> Red
            # cv2.rectangle(img, real_area_box[0], real_area_box[1], (255,0,0), 3)

            # draw poly
            color = color_dic[name] if name else (255,255,0)
            cv2.polylines(img, [diff_poly], True, (255,255,255), thickness=5)
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
def snap(self):
    self.serial.write(LIGHT_ON)
    time.sleep(0.2)
    self.cam.set_exposure(2500)
    img = self.cam.get_image()
    self.serial.write(LIGHT_OFF)
    self.image_Q.put(img)

#######################################################################
def train(self):
    lock = False
    font = cv2.FONT_HERSHEY_SIMPLEX
    while not self.stop_signal:
        time.sleep(0.01)

        # get image
        if self.raw_Q.empty(): continue
        img, diff_img = self.raw_Q.get()
        img_copy = img.copy()
        
        
        diff_polys = tool.find_polys_in_img(diff_img)
        if diff_polys is None: continue
        
        diff_poly = diff_polys[0]
        
        # check center in area
        diff_center = np.mean(diff_poly, axis=0)
        size = np.array(diff_img.shape[:2])[::-1] # xy
        locs = diff_center / size
        is_center = np.all((self.area_box[0] < locs) & (locs < self.area_box[1]))
        is_center2 = np.all((self.area_box2[0] < locs) & (locs < self.area_box2[1]))

        if not is_center2: lock = False; continue
        if lock or not is_center: continue
        lock = True
            
        # 그리기
        clock_poly = tool.poly2clock(diff_poly)
        cv2.polylines(img_copy, [clock_poly], True, (255,255,255), thickness=5)
        cv2.putText(img_copy, '1', clock_poly[0], font, fontScale=1, thickness=1, color=(255,0,255))
        cv2.putText(img_copy, '2', clock_poly[1], font, fontScale=1, thickness=1, color=(255,0,255))
        cv2.putText(img_copy, '3', clock_poly[2], font, fontScale=1, thickness=1, color=(255,0,255))
        cv2.putText(img_copy, '4', clock_poly[3], font, fontScale=1, thickness=1, color=(255,0,255))
        
        
        
        # diff_img = cv2.merge([diff_img, diff_img, diff_img])
        # new_img = np.hstack([img_copy, diff_img])
        
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











