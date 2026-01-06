import cv2
import numpy as np

def detect_stain(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return "No visible stain"

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


    # Oil stain → dark smooth patches
    oil_mask = cv2.inRange(hsv, (0, 0, 0), (180, 50, 80))
    oil_pixels = np.sum(oil_mask > 0)

    # Food stain → red/yellow tones
    food_mask = cv2.inRange(hsv, (10, 50, 50), (35, 255, 255))
    food_pixels = np.sum(food_mask > 0)

    if oil_pixels > food_pixels and oil_pixels > 1000:
        return "Oil"
    elif food_pixels > 1000:
        return "Food"
    else:
        return "No visible stain"
