from utils.logger import logger
from utils import tool
from collections import namedtuple
from glob import glob
from tqdm import tqdm
import numpy as np
import json
import time
import cv2
import os


def json2label(path, return_dic=True): # json 경로
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    labels = [shape["label"] for shape in data["shapes"]]
    points = np.float32([shape["points"] for shape in data["shapes"]]) # (n, 2?, 2)
    if return_dic:
        return dict(zip(labels, points))
    else:
        return labels, points

def get_poly_box_wh(poly_box): # (4, 2)
    lt, rt, rb, lb = poly_box
    w = int((np.linalg.norm(lt - rt) + np.linalg.norm(lb - rb)) // 2)
    h = int((np.linalg.norm(lt - lb) + np.linalg.norm(rt - rb)) // 2)
    return w, h

def crop_obj_in_bg(bg_img, polys):
    obj_imgs = []
    for poly in polys:
        poly = poly.astype(np.float32)
        w, h = get_poly_box_wh(poly)
        pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
        M = cv2.getPerspectiveTransform(poly, pos)
        obj_img = cv2.warpPerspective(bg_img, M, (w, h))
        obj_imgs.append(obj_img)
    return obj_imgs

def get_crop_img_and_M(img, poly):
    poly = poly.astype(np.float32)
    w, h = get_poly_box_wh(poly)
    pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
    M = cv2.getPerspectiveTransform(poly, pos)
    crop_img = cv2.warpPerspective(img, M, (w, h))
    return crop_img, M

#########################################################################################
class SinglePolyDetector():
    def __init__(self, img_path, json_path, pick_labels=[], n_features=2000):
        img_gray = tool.imread(img_path, cv2.IMREAD_GRAYSCALE)
        assert img_gray is not None, "img_path is not correct."
        
        poly_dict = json2label(json_path)
        
        polys = [poly_dict[label] for label in pick_labels]
            
        # assert (target_label_name in self.labels) or (target_label_name==''), "Invalid label_name."
        
        # 0번 index를 target으로
        # target_idx = self.labels.index(target_label_name)
        # self.label[0], self.label[target_idx] = self.label[target_idx], self.label[0]
        # polys[0], polys[target_idx] = polys[target_idx], polys[0]
        
        # keypoints
        self.detector = cv2.ORB_create(n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING2, crossCheck=True)
        crop_img_gray, M = get_crop_img_and_M(img_gray, polys[0])
        self.kp, self.desc = self.detector.detectAndCompute(crop_img_gray, None)
        
        # transform polygons
        polys = np.stack(polys).astype(np.float32)
        polys = cv2.perspectiveTransform(polys, M)
        self.src_polys = polys
        
    def __call__(self, img):
        if img.ndim == 2: img_gray = img
        else: img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # match
        kp, desc = self.detector.detectAndCompute(img_gray, None)
        if len(kp) < 100: return None, None
        matches = self.matcher.match(self.desc, desc)
        
        # get keypoints of matches
        src_pts = np.float32([self.kp[m.queryIdx].pt for m in matches])
        dst_pts = np.float32([kp[m.trainIdx].pt for m in matches])
        
        # src_polys -> dst_polys
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RHO, 5.0)
        if mask.sum() / mask.size < 0.15: return None, None
        dst_polys = cv2.perspectiveTransform(self.src_polys, M)
        
        # get crop_imgs # 이래야 항상 크기가 일정함
        h, w = img.shape[:2]
        inv_M = cv2.getPerspectiveTransform(dst_polys[0], self.src_polys[0])
        img_trans = cv2.warpPerspective(img, inv_M, (w, h))
        crop_imgs = crop_obj_in_bg(img_trans, self.src_polys)
        
        return dst_polys, crop_imgs
    
#########################################################################################
class ObjInfo():
    def __init__(self, name, img_bgr, label2poly, detector):
        self.name = name
        
        obj_poly = label2poly["object"]
        polys = np.float32(list(label2poly.values())) # (n, 4, 2)
        crop_bgr, M = get_crop_img_and_M(img_bgr, obj_poly)
        self.src_polys = cv2.perspectiveTransform(polys, M)
        self.labels = list(label2poly.keys())
        
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        self.kp, self.desc = detector.detectAndCompute(crop_gray, None)
    
    def __repr__(self):
        return f"ObjInfo({self.name})"

class MultiPolyDetector():
    def __init__(self, img_dir_path, json_dir_path, n_features=2000):
        # create detector, matcher
        self.detector = cv2.ORB_create(n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING2, crossCheck=True)
        
#         # Load Images
#         img_paths = sorted(glob(os.path.join(img_dir_path, "*.jpg")))
#         imgs = list(tqdm(map(lambda x:tool.imread(x), img_paths), desc="imread"))
        
#         # Load Annotations
#         json_paths = sorted(glob(os.path.join(json_dir_path, "*.json")))
#         label2poly_list = list(map(json2label, json_paths))
        
#         # assert
#         assert len(img_paths) == len(json_paths)
#         names = list(map(lambda path:path.split('\\')[-1].split('.')[0], img_paths))
#         temps = list(map(lambda path:path.split('\\')[-1].split('.')[0], json_paths))
#         assert names == temps
        
#         # img,label2poly -> obj_info
#         _zip = zip(names, imgs, label2poly_list)
#         self.obj_info_list = list(tqdm(map(lambda x:ObjInfo(*x, self.detector), _zip), desc="obj_info"))
        
        self.obj_info_list = []
        
        # for update_check
        self.names = []#names
        self.img_dir_path = img_dir_path
        self.json_dir_path = json_dir_path
        
        
        self.update_check()
        
        # warm up
        temp = np.zeros((100,100,3), dtype=np.uint8)# tool.imread("./temp/apple.jpg")
        if temp is None: return
        _, _ = self.predict(temp)
        
    def predict(self, img):
        # 새로운 이미지 특징점
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)    
        kp, desc = self.detector.detectAndCompute(gray, None)
        if len(kp) == 0: return None, None
    
        best_obj, best_acc, best_M = None, 0, None
        for obj_info in self.obj_info_list:
            # 사전 데이터와 들어온 데이터를 매칭
            matches = self.matcher.match(obj_info.desc, desc)
            if len(matches) < 30: continue
            src_pts = np.float32([obj_info.kp[m.queryIdx].pt for m in matches])
            dst_pts = np.float32([kp[m.trainIdx].pt for m in matches])
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RHO, 5.0)
            accuracy = np.sum(mask) / len(mask)
            # 최고 정확도 선택
            if best_acc < accuracy:
                best_obj, best_acc, best_M = obj_info, accuracy, M
        
        logger.debug(f"Best Acc : {best_acc*100:0.2f}% \t Best_Obj : {best_obj}")
        if best_acc < 0.20: return None, None
    
        dst_polys = cv2.perspectiveTransform(best_obj.src_polys, best_M)
                        
        return best_obj, dst_polys
        
    def update_check(self):
        img_paths = sorted(glob(os.path.join(self.img_dir_path, "*.jpg")))
        json_paths = sorted(glob(os.path.join(self.json_dir_path, "*.json")))
        
        assert len(img_paths) == len(json_paths)
        names = list(map(lambda path:path.split('\\')[-1].split('.')[0], json_paths))
        temps = list(map(lambda path:path.split('\\')[-1].split('.')[0], img_paths))
        assert names == temps
        
        if names == self.names: return
    
        # 지워진것 거르기
        removed_idxs = [i for i, name in enumerate(self.names) if not name in names]
        removed_idxs = sorted(removed_idxs, reverse=True)
        for i in removed_idxs:
            self.obj_info_list.pop(i)
            self.names.pop(i)
        
        # 새로운것 합치기
        new_idxs = [i for i, name in enumerate(names) if not name in self.names]
        new_names = [names[i] for i in new_idxs]
        new_imgs = list(map(lambda i:tool.imread(img_paths[i]), new_idxs))
        new_label2poly_list = list(map(lambda i:json2label(json_paths[i]), new_idxs))
        _zip = zip(new_names, new_imgs, new_label2poly_list)
        new_obj_info_list = list(map(lambda x:ObjInfo(*x, self.detector), _zip))
        self.obj_info_list.extend(new_obj_info_list)
        self.names.extend(new_names)
        
