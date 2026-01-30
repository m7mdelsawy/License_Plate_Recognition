import cv2
import numpy as np

# فتح الفيديو
video_path = r"C:\Users\abdal\Videos\Sample.mp4"
cap = cv2.VideoCapture(video_path)

# اقرأ أول إطار
ret, frame = cap.read()
if not ret:
    print("لا يمكن فتح الفيديو")
    exit()

# تصغير الإطار للعرض
h, w = frame.shape[:2]
if w > 1280:
    scale = 1280 / w
    frame = cv2.resize(frame, (int(w*scale), int(h*scale)))

# متغيرات لتخزين النقاط
points = []
distances = []

def mouse_callback(event, x, y, flags, param):
    """دالة معالجة حدث الماوس"""
    global points
    
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"نقطة {len(points)}: ({x}, {y})")
        
        # إذا اخترنا نقطتين، احسب المسافة
        if len(points) == 2:
            p1 = np.array(points[0])
            p2 = np.array(points[1])
            dist = np.linalg.norm(p2 - p1)
            distances.append(dist)
            print(f"المسافة بالبكسل: {dist:.2f}")
            
            # ارسم الخط
            cv2.line(frame, points[0], points[1], (0, 255, 0), 2)
            cv2.circle(frame, points[0], 5, (0, 255, 0), -1)
            cv2.circle(frame, points[1], 5, (0, 255, 0), -1)
            
            points = []

# عرض الصورة
cv2.namedWindow('Calibration', cv2.WINDOW_NORMAL)
cv2.setMouseCallback('Calibration', mouse_callback)

print("===== معايرة السرعة =====")
print("انقر على نقطتين لقياس عرض الحارة")
print("اضغط ESC للخروج")
print()

clone = frame.copy()
while True:
    cv2.imshow('Calibration', frame)
    key = cv2.waitKey(1) & 0xFF
    
    if key == 27:  # ESC
        break

cv2.destroyAllWindows()
cap.release()

# احسب PPM
if distances:
    avg_pixels = np.mean(distances)
    lane_width = 3.75  # متر (يمكنك تغييره)
    ppm = avg_pixels / lane_width
    
    print()
    print(f"متوسط البكسل للحارة: {avg_pixels:.2f}")
    print(f"عرض الحارة المفترض: {lane_width} متر")
    print(f"SPEED_PPM = {ppm:.2f}")
    print()
    print("استخدم هذه القيمة في config.py:")
    print(f"SPEED_PPM = {ppm:.1f}")
