from ultralytics import YOLO
import numpy as np

class VehicleDetector:
    CLASSES = [2, 3, 5, 7]

    def __init__(self, model, conf):
        self.model = YOLO(model)
        self.conf = conf

    def detect(self, frame):
        res = self.model.track(
            frame,
            persist=True,
            conf=self.conf,
            classes=self.CLASSES,
            tracker="bytetrack.yaml",
            verbose=False
        )

        vehicles = []
        if res and res[0].boxes:
            for b in res[0].boxes:
                if b.id is None:
                    continue
                box = b.xyxy[0].cpu().numpy()
                vehicles.append({
                    "track_id": int(b.id),
                    "bbox": tuple(box),
                    "center": ((box[0]+box[2])/2, (box[1]+box[3])/2)
                })
        return vehicles
