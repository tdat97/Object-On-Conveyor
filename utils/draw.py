from utils.logger import logger
import cv2
import os

######################################################################
def draw_box_text(img, data, poly_boxes):
    img = img.copy()
    for text, poly in zip(data, poly_boxes):
        cv2.polylines(img, [poly], True, (255,0,0))
        text_loc = np.min(poly, axis=0)
        text_loc[1] -= 10
        cv2.putText(img, text, text_loc, cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    return img
    










    
    
