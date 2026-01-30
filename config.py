from pathlib import Path

class SystemConfig:
    BASE_DIR = Path(__file__).parent
    MODELS_DIR = BASE_DIR / "models"
    DATA_DIR = BASE_DIR / "data"
    EVIDENCE_DIR = BASE_DIR / "evidence"
    TEMP_DIR = BASE_DIR / "temp"

    DB_PATH = DATA_DIR / "lpr.db"

    # ========== MODELS ==========
    # استخدم yolo11n (nano) للسرعة أو yolo11s للتوازن
    VEHICLE_MODEL = MODELS_DIR / "yolo11n.pt"  # n=nano, s=small, m=medium
    PLATE_MODEL = MODELS_DIR / "best.pt"

    VEHICLE_CONF = 0.4  # خفّضت شوية للسرعة
    PLATE_CONF = 0.25

    # ========== PERFORMANCE OPTIMIZATION ==========
    # معالجة resolution أصغر = سرعة أعلى
    PROCESS_WIDTH = 1280  # بدل 1920 (Full HD)
    PROCESS_HEIGHT = 720  # بدل 1080
    
    # معالجة كل N frames (skip frames للسرعة)
    PROCESS_EVERY_N_FRAMES = 2  # يعني هيعالج frame واحد ويسكيب واحد
    
    # استخدام GPU إذا متوفر
    USE_GPU = True
    
    # حجم batch للمعالجة
    BATCH_SIZE = 2  # لو عندك GPU قوي، زوّده لـ 2 أو 4

    # ========== OCR SETTINGS ==========
    OCR_STABLE_FRAMES = 5  # قلّلته من 5 للسرعة
    OCR_VOTING_WINDOW = 10  # قلّلته من 10
    OCR_MIN_W = 40  # قلّلته من 50
    OCR_MIN_H = 15  # قلّلته من 20

    # ========== SPEED CALCULATION ==========
    SPEED_FPS = 24.0        # FPS الفيديو (مهم للدقة!)
    SPEED_PPM = 83       # Pixels Per Meter (معايرة من الفيديو)
    SPEED_MAX = 200.0       # أقصى سرعة منطقية km/h
    SPEED_LIMIT = 60.0      # حد السرعة km/h
    
    # حساب السرعة كل N frames
    SPEED_CALC_INTERVAL = 3  # يحسب السرعة كل 3 frames
    
    # حد أدنى للسرعة للحفظ (تجاهل السيارات الواقفة)
    SPEED_MIN_THRESHOLD = 5.0  # km/h

    # ========== WATCHLIST ==========
    WATCHLIST_THRESHOLD = 0.75

    # ========== EVIDENCE SAVING ==========
    SAVE_EVIDENCE = True
    SAVE_FRAME_QUALITY = 85  # جودة JPEG (0-100)
    
    @classmethod
    def init_dirs(cls):
        for d in [cls.MODELS_DIR, cls.DATA_DIR, cls.EVIDENCE_DIR, cls.TEMP_DIR]:
            d.mkdir(parents=True, exist_ok=True)

SystemConfig.init_dirs()