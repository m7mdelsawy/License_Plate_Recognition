from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from database import DatabaseManager
from core.video_processor import VideoProcessor
from config import SystemConfig
import tempfile
import shutil
import sqlite3
import uuid
import os
from pathlib import Path

app = FastAPI(title="LPR System API", version="1.0.0")

# ✅ CORS للواجهة
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# حالة المهام (مؤقتة – لاحقاً Redis / DB)
tasks_status = {}
tasks_metrics = {}  # ✅ نخزن metrics لكل task


# =========================
# Pydantic Models
# =========================
class WatchlistItem(BaseModel):
    plate: str
    reason: str


# =========================
# Background task function
# =========================
def run_video(path: str, task_id: str):
    db = None
    try:
        tasks_status[task_id] = "processing"
        
        db = DatabaseManager(SystemConfig.DB_PATH)
        vp = VideoProcessor(db)
        
        result = vp.process_video(path)
        
        # ✅ حفظ metrics الخاصة بالtask
        tasks_metrics[task_id] = {
            "ocr": vp.proc.get_ocr_metrics(),
            "speed": vp.proc.get_speed_metrics()
        }
        
        db.commit()
        tasks_status[task_id] = "done"

    except Exception as e:
        tasks_status[task_id] = f"error: {str(e)}"
        print(f"Error processing video {task_id}: {e}")

    finally:
        if db:
            db.close()
        if os.path.exists(path):
            os.remove(path)


# =========================
# Upload video (Non-blocking)
# =========================
@app.post("/api/process/video")
async def process_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """رفع فيديو للمعالجة"""
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(400, "Video format not supported")
    
    task_id = str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        shutil.copyfileobj(file.file, tmp)
        path = tmp.name

    tasks_status[task_id] = "queued"
    background_tasks.add_task(run_video, path, task_id)

    return {
        "task_id": task_id,
        "status": "queued",
        "filename": file.filename
    }


# =========================
# Task status
# =========================
@app.get("/api/task/{task_id}")
def task_status(task_id: str):
    """حالة مهمة معالجة"""
    status = tasks_status.get(task_id, "not_found")
    response = {
        "task_id": task_id,
        "status": status
    }
    
    # إذا المهمة خلصت، نرجع metrics
    if status == "done" and task_id in tasks_metrics:
        response["metrics"] = tasks_metrics[task_id]
    
    return response


# =========================
# Get all vehicles
# =========================
@app.get("/api/vehicles")
def get_vehicles(limit: int = 100):
    """جلب العربيات المسجلة"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    rows = db.get_all_vehicles()
    db.close()
    
    return [
        {
            "id": r[0],
            "track_id": r[1],
            "plate": r[2],
            "max_speed": r[3],
            "avg_speed": r[4],
            "evidence_path": r[5],
            "created_at": r[6]
        }
        for r in rows[:limit]
    ]


# =========================
# Get all violations
# =========================
@app.get("/api/violations")
def get_violations(limit: int = 100):
    """جلب المخالفات"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    rows = db.get_all_violations()
    db.close()
    
    return [
        {
            "id": r[0],
            "plate": r[1],
            "speed": r[2],
            "speed_limit": r[3],
            "created_at": r[4],
            "evidence_path": r[5]
        }
        for r in rows[:limit]
    ]


# =========================
# Get alerts
# =========================
@app.get("/api/alerts")
def get_alerts(limit: int = 100):
    """جلب تنبيهات الwatchlist"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    
    rows = db.c.execute("""
        SELECT
            id, plate, watchlist_plate, reason,
            similarity, evidence_path, created_at
        FROM alerts
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    
    db.close()
    
    return [
        {
            "id": r[0],
            "plate": r[1],
            "watchlist_plate": r[2],
            "reason": r[3],
            "similarity": r[4],
            "evidence_path": r[5],
            "created_at": r[6]
        }
        for r in rows
    ]


# =========================
# OCR timeline per vehicle
# =========================
@app.get("/api/vehicle/{vehicle_id}/ocr-timeline")
def vehicle_timeline(vehicle_id: int):
    """تتبع قراءات OCR لعربية معينة"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    
    rows = db.c.execute("""
        SELECT frame, text, confidence, created_at
        FROM ocr_timeline
        WHERE vehicle_id = ?
        ORDER BY frame
    """, (vehicle_id,)).fetchall()
    
    db.close()
    
    return {
        "vehicle_id": vehicle_id,
        "timeline": [
            {
                "frame": r[0],
                "text": r[1],
                "confidence": r[2],
                "created_at": r[3]
            }
            for r in rows
        ]
    }


# =========================
# Watchlist Management
# =========================
@app.get("/api/watchlist")
def get_watchlist():
    """جلب قائمة المراقبة"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    rows = db.c.execute("""
        SELECT id, plate, reason, created_at
        FROM watchlist
        WHERE active = 1
        ORDER BY created_at DESC
    """).fetchall()
    db.close()
    
    return [
        {
            "id": r[0],
            "plate": r[1],
            "reason": r[2],
            "created_at": r[3]
        }
        for r in rows
    ]


@app.post("/api/watchlist")
def add_to_watchlist(item: WatchlistItem):
    """إضافة لوحة للمراقبة"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    success = db.add_to_watchlist(item.plate, item.reason)
    db.close()
    
    if not success:
        raise HTTPException(400, "Plate already in watchlist")
    
    return {"status": "added", "plate": item.plate}


@app.delete("/api/watchlist/{plate}")
def remove_from_watchlist(plate: str):
    """حذف لوحة من المراقبة"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    db.remove_from_watchlist(plate)
    db.close()
    
    return {"status": "removed", "plate": plate}


# =========================
# Statistics
# =========================
@app.get("/api/stats")
def get_stats():
    """إحصائيات النظام"""
    db = DatabaseManager(SystemConfig.DB_PATH)
    
    stats = {
        "total_vehicles": db.c.execute("SELECT COUNT(*) FROM vehicles WHERE plate IS NOT NULL").fetchone()[0],
        "total_violations": db.c.execute("SELECT COUNT(*) FROM violations").fetchone()[0],
        "total_alerts": db.c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
        "watchlist_count": db.c.execute("SELECT COUNT(*) FROM watchlist WHERE active=1").fetchone()[0],
    }
    
    db.close()
    return stats


# =========================
# Serve evidence images
# =========================
app.mount("/evidence", StaticFiles(directory=str(SystemConfig.EVIDENCE_DIR)), name="evidence")


# =========================
# Frontend
# =========================
if Path("frontend").exists():
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")