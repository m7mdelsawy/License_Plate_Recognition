import numpy as np
from collections import defaultdict, deque

class SpeedTracker:
    def __init__(self, ppm, fps):
        """
        ppm: Pixels Per Meter (معايرة الكاميرا)
        fps: Frames Per Second (معدل الإطارات)
        """
        self.ppm = ppm
        self.fps = fps
        
        # تخزين مواقع وأوقات السيارات
        self.positions = defaultdict(lambda: deque(maxlen=30))  # آخر 30 موقع
        self.timestamps = defaultdict(lambda: deque(maxlen=30))
        self.speeds = defaultdict(lambda: deque(maxlen=10))  # آخر 10 سرعات
        
        self.frame_count = defaultdict(int)

    def update(self, tid, center):
        """
        تحديث موقع السيارة وحساب السرعة
        tid: Track ID
        center: (x, y) - مركز السيارة
        """
        current_frame = self.frame_count[tid]
        self.frame_count[tid] += 1
        
        # حفظ الموقع والوقت
        self.positions[tid].append(center)
        self.timestamps[tid].append(current_frame)
        
        # نحتاج على الأقل موقعين لحساب السرعة
        if len(self.positions[tid]) < 2:
            return None
        
        # حساب السرعة بين آخر نقطتين
        p1 = np.array(self.positions[tid][-2])
        p2 = np.array(self.positions[tid][-1])
        
        t1 = self.timestamps[tid][-2]
        t2 = self.timestamps[tid][-1]
        
        # المسافة بالبكسل
        distance_pixels = np.linalg.norm(p2 - p1)
        
        # الوقت بالثواني
        time_seconds = (t2 - t1) / self.fps
        
        if time_seconds == 0:
            return None
        
        # السرعة = المسافة / الوقت
        # تحويل من بكسل/ثانية إلى متر/ثانية ثم كم/ساعة
        distance_meters = distance_pixels / self.ppm
        speed_ms = distance_meters / time_seconds
        speed_kmh = speed_ms * 3.6
        
        # فلترة السرعات الغير منطقية
        if 0 < speed_kmh < 250:
            self.speeds[tid].append(speed_kmh)
            # متوسط السرعات الأخيرة لتقليل الضوضاء
            return float(np.mean(self.speeds[tid]))
        
        return None
    
    def get_average_speed(self, tid):
        """الحصول على متوسط السرعة لسيارة معينة"""
        if tid in self.speeds and len(self.speeds[tid]) > 0:
            return float(np.mean(self.speeds[tid]))
        return None
    
    def get_max_speed(self, tid):
        """الحصول على أقصى سرعة لسيارة معينة"""
        if tid in self.speeds and len(self.speeds[tid]) > 0:
            return float(np.max(self.speeds[tid]))
        return None
    
    def reset(self, tid):
        """إعادة تعيين بيانات سيارة معينة"""
        if tid in self.positions:
            del self.positions[tid]
            del self.timestamps[tid]
            del self.speeds[tid]
            del self.frame_count[tid]