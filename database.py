import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.c = self.conn.cursor()
        self._init()

    def _init(self):
        # Vehicles table
        self.c.execute("""
        CREATE TABLE IF NOT EXISTS vehicles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER,
            plate TEXT,
            max_speed REAL,
            avg_speed REAL,
            evidence_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # OCR timeline
        self.c.execute("""
        CREATE TABLE IF NOT EXISTS ocr_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            frame INTEGER,
            text TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # Violations
        self.c.execute("""
        CREATE TABLE IF NOT EXISTS violations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            plate TEXT,
            speed REAL,
            speed_limit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # Watchlist
        self.c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT UNIQUE,
            reason TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # Alerts
        self.c.execute("""
        CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            plate TEXT,
            watchlist_plate TEXT,
            reason TEXT,
            similarity REAL,
            evidence_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        self.conn.commit()

    def add_vehicle(self, track_id):
        self.c.execute(
            "INSERT INTO vehicles(track_id) VALUES(?)",
            (track_id,)
        )
        self.conn.commit()
        return self.c.lastrowid

    def update_plate(self, vehicle_id, plate):
        self.c.execute(
            "UPDATE vehicles SET plate=? WHERE id=?",
            (plate, vehicle_id)
        )
        self.conn.commit()

    def update_speed(self, vehicle_id, max_speed, avg_speed):
        """تحديث سرعة السيارة"""
        self.c.execute(
            "UPDATE vehicles SET max_speed=?, avg_speed=? WHERE id=?",
            (max_speed, avg_speed, vehicle_id)
        )
        self.conn.commit()

    def add_ocr_timeline(self, vehicle_id, frame, text, confidence):
        self.c.execute(
            "INSERT INTO ocr_timeline(vehicle_id,frame,text,confidence) VALUES(?,?,?,?)",
            (vehicle_id, frame, text, confidence)
        )

    def add_violation(self, vehicle_id, plate, speed, speed_limit):
        self.c.execute(
            "INSERT INTO violations(vehicle_id,plate,speed,speed_limit) VALUES(?,?,?,?)",
            (vehicle_id, plate, speed, speed_limit)
        )
        self.conn.commit()

    def add_alert(self, vehicle_id, plate, watchlist_plate, reason, similarity, evidence_path):
        self.c.execute("""
            INSERT INTO alerts(
                vehicle_id,
                plate,
                watchlist_plate,
                reason,
                similarity,
                evidence_path
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            plate,
            watchlist_plate,
            reason,
            similarity,
            evidence_path
        ))
        self.conn.commit()

    def get_watchlist(self):
        rows = self.c.execute(
            "SELECT plate,reason FROM watchlist WHERE active=1"
        ).fetchall()
        return rows

    def add_to_watchlist(self, plate, reason):
        """إضافة لوحة للمراقبة"""
        try:
            self.c.execute(
                "INSERT INTO watchlist(plate, reason) VALUES(?, ?)",
                (plate, reason)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_from_watchlist(self, plate):
        """حذف لوحة من المراقبة"""
        self.c.execute(
            "UPDATE watchlist SET active=0 WHERE plate=?",
            (plate,)
        )
        self.conn.commit()

    def get_all_vehicles(self):
        """جلب كل العربيات المسجلة"""
        rows = self.c.execute("""
            SELECT id, track_id, plate, max_speed, avg_speed, evidence_path, created_at
            FROM vehicles
            WHERE plate IS NOT NULL
            ORDER BY created_at DESC
        """).fetchall()
        return rows

    def get_all_violations(self):
        """جلب كل المخالفات"""
        rows = self.c.execute("""
            SELECT v.id, v.plate, v.speed, v.speed_limit, v.created_at, veh.evidence_path
            FROM violations v
            LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
            ORDER BY v.created_at DESC
        """).fetchall()
        return rows

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.commit()
        self.conn.close()