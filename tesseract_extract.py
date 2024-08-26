import pytesseract
import cv2
import re
import time
import numpy as np
import threading
from algorithms import Algorithms

myconf = "--psm 11 --oem 3"
pattern1 = r'[A-Z]{3}\d{3}'
#pattern1 = r'MOBILFOX'

canRead = True

class OCR:
    def runOnAnotherThread(img):
        global text
        text = pytesseract.image_to_string(img, lang='eng', config=myconf)
    def extract_text(img):
        th = threading.Thread(target=OCR.runOnAnotherThread, args=(img,))
        th.start()
        th.join()
        clean_text = re.sub(r'[^a-zA-Z0-9]+', '', text)
        print(clean_text)
        plate_noticed = re.search(pattern1, clean_text)
        if plate_noticed: 
            plate_string = plate_noticed.group(0)
            #Camera.cameraInstall       
            return plate_string
        else:
            return None
    
class Camera:
    def cameraInstall():
        global licenseString
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if ret:
                done_frame = frame
                break
        
        gray = cv2.cvtColor(done_frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3,3), 0)
        _, thresholded_image = cv2.threshold(blurred, 5, 255, cv2.THRESH_BINARY)

        licenseString = OCR.extract_text(thresholded_image)

        cv2.imwrite(Algorithms.resourcePath("licenseplates/IMG.jpg"), thresholded_image)
        cap.release()
        cv2.destroyAllWindows()
        
        return
    
     