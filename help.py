import numpy as np
import cv2

class CoordinateStore:
    def __init__(self):
        self.points = []

    def select_point(self,event,x,y,flags,param):
            if event == cv2.EVENT_LBUTTONDBLCLK:
                cv2.circle(img,(x,y),3,(255,0,0),-1)
                self.points.append((x,y))

cs = CoordinateStore()
img = cv2.imread('C:\Users\CJ\Desktop\cut_images_xJm66dBCTl2D\image_part_002.jpg',-1)
cv2.namedWindow('image')
cv2.setMouseCallback('image',cs.select_point)

while(True):
    print(len(cs.points))
    if len(cs.points) == 4:
        pts1 = np.float32([cs.points[0], cs.points[1], cs.points[2], cs.points[3]])
        # pts1 = np.float32([
        #     (696, 455),
        #     (587, 455),
        #     (235, 700),
        #     (1075, 700)
        # ])
        pts2 = np.float32([
        (1265 - 350, 0),
        (350, 0),
        (350, 900),
        (1265 - 350, 900)
    ])
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        result0 = cv2.warpPerspective(img, matrix, (1265, 900))
        result = cv2.warpPerspective(img, matrix, (1265, 900), flags=cv2.INTER_LINEAR)
        result = cv2.resize(result, (1080, 720))

        cv2.imshow('warpLin', result)
        cv2.imshow('warp', result0)


    cv2.imshow('image',img)
    if chr(cv2.waitKey(1) & 255) == 'q':
        break;

# When everything done, release the capture
cv2.destroyAllWindows()