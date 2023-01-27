
# window
TITLE = "Machine Vision System"
ICON_PATH = "./gui/eye.ico"

# source
IMG_DIR_PATH = "./source/img"
JSON_DIR_PATH = "./source/json"

# recode
SAVE_IMG_DIR = "./recode"
SAVE_RAW_IMG_DIR = "./recode/raw"
SAVE_OK_IMG_DIR = "./recode/OK"
SAVE_NG_IMG_DIR = "./recode/NG"
SAVE_DEBUG_IMG_DIR = "./recode/debug"

# Serial
SERIAL_PORT = "COM1"
# ex) 0xB0 0x01 0x00 0xB1 -> get input-pin-1 sensor value
# ex) 0xC0 0x01 0x01 0xC0 -> reply (input-pin-1 is HIGH)
# ex) 0xA0 0x02 0x01 0xA3 -> turn on output-pin-2 
# ex) 0xFF 0x00 0x00 0xFF -> Incorrect validation.

# Cam
EXPOSURE_TIME = 2500

# Font
FONT_PATH = "./source/NanumGothic.ttf"