from ultralytics import YOLO

class PlateDetector:
    def __init__(self, model, conf):
        self.model = YOLO(model)
        self.conf = conf

    def detect(self, crop):
        if crop is None:
            return None
        r = self.model(crop, conf=self.conf, verbose=False)
        if not r or not r[0].boxes:
            return None
        b = r[0].boxes[0]
        return b.xyxy[0].cpu().numpy()
