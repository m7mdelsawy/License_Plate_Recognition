import cv2
from core.vehicle_processor import VehicleProcessor

class VideoProcessor:
    def __init__(self, db):
        self.proc = VehicleProcessor(db)

    def process_video(self, path):
        cap = cv2.VideoCapture(path)
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            self.proc.process(frame)
            frame_count += 1

            if frame_count % 50 == 0:
                self.proc.db.commit()

        cap.release()
        self.proc.db.commit()
        return {"status": "done"}

