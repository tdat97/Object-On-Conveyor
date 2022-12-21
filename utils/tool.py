import numpy as np
import cv2
import datetime

##########################################################################
def get_poly_box_wh(poly_box): # (4,2)
    lt, rt, rb, lb = poly_box
    w = int((np.linalg.norm(lt - rt) + np.linalg.norm(lb - rb)) // 2)
    h = int((np.linalg.norm(lt - lb) + np.linalg.norm(rt - rb)) // 2)
    return w, h


def crop_obj_in_bg(bg_img, poly, w, h):
    poly = poly.astype(np.float32)
    pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
    M = cv2.getPerspectiveTransform(poly, pos)
    obj_img = cv2.warpPerspective(bg_img, M, (w, h))
    return obj_img, M

##########################################################################
def get_time_str(human_mode=False):
    now = datetime.datetime.now()
    if human_mode:
        s = f"{now.year:04d}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"
    else:
        s = f"{now.year:04d}{now.month:02d}{now.day:02d}{now.hour:02d}{now.minute:02d}{now.second:02d}"
        s += f"_{now.microsecond:06d}"
    return s

##########################################################################
def fix_ratio_resize_img(img, size, target='w'):
    h, w = img.shape[:2]
    ratio = h/w
    if target == 'w': resized_img = cv2.resize(img, dsize=(size, int(ratio * size)))
    else:             resized_img = cv2.resize(img, dsize=(int(size / ratio), size))
    return resized_img

##########################################################################
def clear_Q(Q):
    with Q.mutex:
        Q.queue.clear()
        
def clear_serial(ser):
    while True:
        if ser.read_all() == b'': break

##########################################################################    
def find_poly_in_img(img, min_area=0.05, max_area=0.5, scale=0.1):
    # minimize img for speed.
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    mini_img = cv2.resize(img_gray, dsize=(0,0), fx=scale, fy=scale)
    mini_img_area = mini_img.shape[0] * mini_img.shape[1]

    # set mser
    mser = cv2.MSER_create()
    mser.setMinArea(int(mini_img_area*min_area))
    mser.setMaxArea(int(mini_img_area*max_area))

    # find poly
    regions, bboxes = mser.detectRegions(mini_img)
    if len(regions) == 0: return None
    rectangles = list(map(cv2.minAreaRect, regions))
    polygons = list(map(lambda x:cv2.boxPoints(x), rectangles))
    areas = list(map(cv2.contourArea, polygons))
    max_idx = np.argmax(areas)
    poly = (polygons[max_idx] / scale).astype(np.int32)

    return poly
    
def poly2clock(poly):
    # move centroid to zero
    centroid = np.mean(poly, axis=0) # (2,)
    new_poly = poly - centroid # (n, 2)

    # sort by radian
    # 이미지에서 볼때 좌상단 첫번째로 시계방향
    # 좌표계에서 볼때 좌하단 첫번재로 반시계방향
    rad = list(map(lambda x:np.arctan2(*x), new_poly[:,::-1])) # xy -> yx
    idxs = np.argsort(rad)
    return poly[idxs]
    
##########################################################################
def centroid_tracking(points_t0, points_t1): # (n, 2), (m, 2)
    if len(points_t0) == 0 and len(points_t1) == 0: return []
    if len(points_t0) == 0: return [[-1, i] for i in range(len(points_t1))]
    if len(points_t1) == 0: return [[i, -1] for i in range(len(points_t0))]

    # get distances
    pt0 = points_t0.reshape(-1, 1, 2) # (n, 1, 2)
    pt1 = points_t1.reshape(1, -1, 2) # (1, m, 2)
    dist = np.linalg.norm(pt0-pt1, axis=-1) # (n, m)

    # argsort where 2D-Array
    flatten_idxes = np.argsort(dist.ravel()) # flatten
    idxes_2d = np.stack(np.unravel_index(flatten_idxes, dist.shape), axis=-1)

    # get pairs
    pick_t0, pick_t1, pairs = set(), set(), []
    for i0, i1 in idxes_2d:
        if i0 in pick_t0 and i1 in pick_t1: continue
        if i0 in pick_t0: i0 = -1
        if i1 in pick_t1: i1 = -1
        pick_t0.add(i0)
        pick_t1.add(i1)
        pairs.append([i0, i1])

    return pairs
        
def attach_names(names_t0, pairs, remaining_names):
    pairs = sorted(pairs, key=lambda x:x[1])
    assert not [-1, -1] in pairs
    
    names_t1 = []
    for i0, i1 in pairs:
        if i1 == -1: remaining_names.append(names_t0[i0]) # 이름 반환
        elif i0 == -1: names_t1.append(remaining_names.pop(0)) # 이름 대여
        else: names_t1.append(names_t0[i0])

    return names_t1

##########################################################################
            
        

        
    







    





        
