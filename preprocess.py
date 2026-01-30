import cv2

class PlatePreprocessor:
    @staticmethod
    def generate(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

        clahe = cv2.createCLAHE(2.0, (8,8)).apply(gray)
        _, otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

        return [gray, clahe, otsu]

