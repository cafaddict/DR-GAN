import cv2
import os




for dirname, dirnames, filenames in os.walk('.'):
    # print path to all subdirectories first.
    for subdirname in dirnames:
        print(os.path.join(dirname, subdirname))

    # print path to all filenames.
    for filename in filenames:
        print(os.path.join(dirname, filename))
# im = cv2.imread("cfp-dataset/Data/Images/001/frontal/01.jpg")
# print(im)