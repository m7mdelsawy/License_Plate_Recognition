import cv2
import base64
import asyncio
from core.vehicle_processor import VehicleProcessor
from config import SystemConfig
import numpy as np

class LiveVideoProcessor:
    def __init__(self, db, websocket):
        self.proc = VehicleProcessor(db)
        self.websocket = websocket
        self.frame_count = 0
        self.send_every_n_frames = 3  # إرسال كل 3 frames للسرعة

    def draw_detection(self, frame, vehicles_info):
        """رسم bounding boxes والمعلومات على الإطار"""
        overlay = frame.copy()
        
        for info in vehicles_info:
            bbox = info.get('bbox')
            if bbox is None or len(bbox) != 4:
                continue
                
            # ✅ التحويل لـ integers
            x1, y1, x2, y2 = map(int, bbox)
            tid = info['track_id']
            
            # التأكد من الـ coordinates صحيحة
            h, w = frame.shape[:2]
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # لون حسب الحالة
            if info.get('is_speeding'):
                color = (0, 0, 255)  # أحمر للمخالفة
                status = "SPEEDING"
            elif info.get('has_plate'):
                color = (0, 255, 0)  # أخضر للسيارة المسجلة
                status = "OK"
            else:
                color = (255, 165, 0)  # برتقالي للمعالجة
                status = "DETECTING"
            
            # رسم المستطيل
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 3)
            
            # خلفية للنص
            label_size = cv2.getTextSize(f"ID:{tid}", cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            label_h = max(label_size[1] + 40, 60)  # ارتفاع كافي للنص
            
            # التأكد إن الخلفية داخل حدود الصورة
            bg_y1 = max(0, y1 - label_h)
            bg_y2 = y1
            
            cv2.rectangle(
                overlay,
                (x1, bg_y1),
                (x1 + max(label_size[0] + 10, 200), bg_y2),
                color,
                -1
            )
            
            # معلومات السيارة
            y_offset = bg_y2 - 10
            
            # ID
            cv2.putText(
                overlay,
                f"ID: {tid}",
                (x1 + 5, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # اللوحة إن وُجدت
            if info.get('plate'):
                cv2.putText(
                    overlay,
                    f"{info['plate']}",
                    (x1 + 5, y_offset - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )
                y_offset -= 20
            
            # السرعة إن وُجدت
            if info.get('speed') is not None:
                speed_text = f"{info['speed']:.1f} km/h"
                cv2.putText(
                    overlay,
                    speed_text,
                    (x1 + 5, y_offset - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2
                )
        
        # دمج الصورة الأصلية مع الـ overlay
        alpha = 0.8
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    def encode_frame(self, frame):
        """تحويل الإطار لـ base64 للإرسال"""
        # تصغير للإرسال الأسرع
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280 / w
            new_w = 1280
            new_h = int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h))
        
        # ضغط JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return base64.b64encode(buffer).decode('utf-8')

    def get_vehicles_info(self):
        """جمع معلومات السيارات الحالية"""
        vehicles_info = []
        
        for tid, state in self.proc.states.items():
            bbox = state.get('last_bbox')
            
            # التأكد من وجود bbox
            if bbox is None:
                continue
            
            info = {
                'track_id': tid,
                'bbox': bbox,
                'has_plate': state.get('plate_final', False),
                'plate': state.get('final_plate'),
                'speed': state.get('last_speed'),
                'is_speeding': state.get('is_speeding', False)
            }
            vehicles_info.append(info)
        
        return vehicles_info

    async def process_video_stream(self, video_path, task_id):
        """معالجة الفيديو مع streaming للـ frames"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            await self.websocket.send_json({"error": "Cannot open video"})
            return
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # إرسال معلومات الفيديو
        await self.websocket.send_json({
            "type": "video_info",
            "total_frames": total_frames,
            "fps": fps,
            "duration": total_frames / fps if fps > 0 else 0
        })
        
        self.frame_count = 0
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                
                # حفظ الإطار الأصلي
                original_frame = frame.copy()
                
                # معالجة الإطار
                self.proc.process(frame)
                
                # الحصول على معلومات السيارات
                vehicles_info = self.get_vehicles_info()
                
                # رسم المعلومات على الإطار
                try:
                    annotated_frame = self.draw_detection(original_frame, vehicles_info)
                except Exception as e:
                    print(f"Error drawing detections: {e}")
                    annotated_frame = original_frame
                
                # إرسال الإطار كل N frames
                if self.frame_count % self.send_every_n_frames == 0:
                    frame_data = self.encode_frame(annotated_frame)
                    
                    # إعداد البيانات للإرسال
                    data = {
                        "type": "frame",
                        "frame_number": self.frame_count,
                        "total_frames": total_frames,
                        "progress": (self.frame_count / total_frames * 100) if total_frames > 0 else 0,
                        "image": frame_data,
                        "vehicles": [
                            {
                                "id": v['track_id'],
                                "plate": v.get('plate'),
                                "speed": v.get('speed'),
                                "is_speeding": v.get('is_speeding', False)
                            }
                            for v in vehicles_info
                        ]
                    }
                    
                    try:
                        await self.websocket.send_json(data)
                        # إعطاء وقت للعميل لاستقبال البيانات
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        print(f"Error sending frame: {e}")
                        break
                
                # حفظ في DB كل 50 frame
                if self.frame_count % 50 == 0:
                    self.proc.db.commit()
        
        except Exception as e:
            print(f"Error in video processing: {e}")
            await self.websocket.send_json({"error": str(e)})
        
        finally:
            cap.release()
            self.proc.db.commit()