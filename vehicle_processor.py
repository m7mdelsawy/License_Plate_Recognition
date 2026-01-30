from config import SystemConfig
from detection.vehicle_detector import VehicleDetector
from detection.plate_detector import PlateDetector
from ocr.reader import OCREngine
from ocr.voting import PlateVoting
from speed.tracker import SpeedTracker
from alerts.watchlist import WatchlistManager
import cv2
from datetime import datetime
from pathlib import Path

class VehicleProcessor:
    def __init__(self, db):
        self.db = db
        self.states = {}
        self.frame_counter = 0

        # OCR metrics
        self.ocr_attempts = 0
        self.ocr_valid_reads = 0
        self.ocr_consensus = 0
        
        # Speed tracking
        self.total_vehicles = 0
        self.speeding_vehicles = 0

        self.vdet = VehicleDetector(SystemConfig.VEHICLE_MODEL, SystemConfig.VEHICLE_CONF)
        self.pdet = PlateDetector(SystemConfig.PLATE_MODEL, SystemConfig.PLATE_CONF)
        self.ocr = OCREngine()
        self.vote = PlateVoting(SystemConfig.OCR_VOTING_WINDOW)
        self.speed = SpeedTracker(SystemConfig.SPEED_PPM, SystemConfig.SPEED_FPS)
        self.watch = WatchlistManager(db, SystemConfig.WATCHLIST_THRESHOLD)
    
    def save_evidence(self, vid, frame, plate_crop):
        if not SystemConfig.SAVE_EVIDENCE:
            return None
            
        date = datetime.now().strftime("%Y-%m-%d")
        base_dir = (
            SystemConfig.EVIDENCE_DIR
            / date
            / f"vehicle_{vid}"
        )
        base_dir.mkdir(parents=True, exist_ok=True)

        plate_path = base_dir / "plate.jpg"
        frame_path = base_dir / "frame.jpg"

        # حفظ بجودة محددة للتوفير
        cv2.imwrite(
            str(plate_path), 
            plate_crop,
            [cv2.IMWRITE_JPEG_QUALITY, SystemConfig.SAVE_FRAME_QUALITY]
        )
        cv2.imwrite(
            str(frame_path), 
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, SystemConfig.SAVE_FRAME_QUALITY]
        )
        return str(base_dir)

    def resize_frame(self, frame):
        """تصغير الإطار للمعالجة الأسرع"""
        h, w = frame.shape[:2]
        if w > SystemConfig.PROCESS_WIDTH:
            scale = SystemConfig.PROCESS_WIDTH / w
            new_w = SystemConfig.PROCESS_WIDTH
            new_h = int(h * scale)
            return cv2.resize(frame, (new_w, new_h))
        return frame

    def process(self, frame):
        self.frame_counter += 1
        
        # Skip frames للسرعة
        if self.frame_counter % SystemConfig.PROCESS_EVERY_N_FRAMES != 0:
            return
        
        # تصغير للمعالجة الأسرع
        if SystemConfig.PROCESS_WIDTH < frame.shape[1]:
            frame = self.resize_frame(frame)
        
        vehicles = self.vdet.detect(frame)

        for v in vehicles:
            tid = v["track_id"]

            if tid not in self.states:
                vid = self.db.add_vehicle(tid)
                self.states[tid] = {
                    "vid": vid,
                    "frames": 0,
                    "plate_final": False,
                    "max_speed": 0,
                    "speeds": []
                }
                self.total_vehicles += 1

            state = self.states[tid]
            state["frames"] += 1
            vid = state["vid"]

            # حساب السرعة
            if state["frames"] % SystemConfig.SPEED_CALC_INTERVAL == 0:
                speed = self.speed.update(tid, v["center"])
                
                if speed and speed > SystemConfig.SPEED_MIN_THRESHOLD:
                    state["speeds"].append(speed)
                    state["max_speed"] = max(state["max_speed"], speed)
                    
                    # تحديث السرعة في الـ DB
                    avg_speed = sum(state["speeds"]) / len(state["speeds"])
                    self.db.update_speed(vid, state["max_speed"], avg_speed)
                    
                    # فحص المخالفة
                    if speed > SystemConfig.SPEED_LIMIT:
                        state["is_speeding"] = True

            # معالجة اللوحات
            if state["plate_final"]:
                continue

            if state["frames"] < SystemConfig.OCR_STABLE_FRAMES:
                continue

            x1, y1, x2, y2 = map(int, v["bbox"])
            crop = frame[y1:y2, x1:x2]

            box = self.pdet.detect(crop)
            if box is None:
                continue

            px1, py1, px2, py2 = map(int, box)
            plate_crop = crop[py1:py2, px1:px2]

            if plate_crop.shape[1] < SystemConfig.OCR_MIN_W:
                continue

            self.ocr_attempts += 1
            results = self.ocr.read(plate_crop)

            for text, conf in results:
                self.ocr_valid_reads += 1
                self.vote.add(vid, text, conf)

                self.db.add_ocr_timeline(
                    vehicle_id=vid,
                    frame=state["frames"],
                    text=text,
                    confidence=round(conf, 3)
                )

            consensus = self.vote.consensus(vid)
            if consensus:
                plate, conf = consensus
                self.ocr_consensus += 1
                state["plate_final"] = True
                
                evidence_path = self.save_evidence(
                    vid=vid,
                    frame=frame,
                    plate_crop=plate_crop
                )

                self.db.update_plate(vid, plate)
                
                if evidence_path:
                    self.db.c.execute(
                        "UPDATE vehicles SET evidence_path=? WHERE id=?",
                        (evidence_path, vid)
                    )
                    self.db.commit()

                # Watchlist check
                alert = self.watch.check(plate)
                if alert:
                    self.db.add_alert(
                        vehicle_id=vid,
                        plate=plate,
                        watchlist_plate=alert["plate"],
                        reason=alert["reason"],
                        similarity=round(alert["similarity"], 3),
                        evidence_path=evidence_path or ""
                    )

                # Speed violation - تسجيل المخالفة عند اكتمال القراءة
                if state.get("is_speeding") and state["max_speed"] > SystemConfig.SPEED_LIMIT:
                    self.db.add_violation(
                        vehicle_id=vid,
                        plate=plate,
                        speed=round(state["max_speed"], 2),
                        speed_limit=SystemConfig.SPEED_LIMIT
                    )
                    self.speeding_vehicles += 1

    def get_ocr_metrics(self):
        acc = (self.ocr_consensus / self.ocr_attempts) if self.ocr_attempts else 0
        return {
            "attempts": self.ocr_attempts,
            "valid_reads": self.ocr_valid_reads,
            "consensus": self.ocr_consensus,
            "accuracy_percent": round(acc * 100, 2)
        }
    
    def get_speed_metrics(self):
        """إحصائيات السرعة"""
        return {
            "total_vehicles": self.total_vehicles,
            "speeding_vehicles": self.speeding_vehicles,
            "speed_limit": SystemConfig.SPEED_LIMIT
        }