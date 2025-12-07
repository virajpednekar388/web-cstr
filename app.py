import os
import time
import threading
import sqlite3
import csv
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from plc_logic import read_plc_registers

# ---------- Configuration ----------
DB_PATH = "scada_data.db"
PLC_IP = "192.168.1.1"
PLC_PORT = 502
PLC_UNIT_ID = 1
LOG_INTERVAL = 2.0  # seconds

# ---------- Flask setup ----------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"

# ---------- Database Setup ----------

DB_PATH = "scada_data.db"
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL,
            pressure REAL
        )
    """)
    conn.commit()
    conn.close()
    print("[app] SQLite database initialized.")

def insert_plc_record(ts, temp, pressure):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")  # Enables concurrent read/write
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO plc_data (timestamp, temperature, pressure) VALUES (?, ?, ?)", 
            (ts, temp, pressure)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("[DB] Insert error:", e)



# ---------- Background Logger ----------
def background_logger():
    print("[logger] Background logger started.")
    while True:
        try:
            regs = read_plc_registers(ip=PLC_IP, port=PLC_PORT, address=40001, count=4, device_id=PLC_UNIT_ID)
            if regs and len(regs) >= 2:
                temp = regs[0]
                pressure = regs[1]
                ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[logger] {ts} - Temp: {temp}, Pressure: {pressure}")
                insert_plc_record(ts, temp, pressure)
            else:
                print("[logger] No valid registers read.")
        except Exception as e:
            print("[logger] Exception:", e)
        time.sleep(LOG_INTERVAL)

def start_background_logger():
    t = threading.Thread(target=background_logger, daemon=True)
    t.start()

# ---------- Simple Auth ----------
users = {
    "v": generate_password_hash("v"),
    "kale": generate_password_hash("kale@123"),
    "om": generate_password_hash("om@123"),
}

# ---------- Routes ----------
@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and check_password_hash(users[username], password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="❌ Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/About")
def about():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("About.html", user=session.get("user"))

@app.route("/DataLog")
def DataLog():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("DataLog.html", user=session.get("user"))

@app.route("/Trends")
def Trends():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("Trends.html", user=session.get("user"))

@app.route("/fetch_data")
def fetch_data():
    try:
        regs = read_plc_registers(ip=PLC_IP, port=PLC_PORT, address=40001, count=4, device_id=PLC_UNIT_ID)
        if not regs or len(regs) < 2:
            return jsonify({"temperature": None, "pressure": None, "error": "PLC data invalid"}), 200

        temp = regs[0]
        pressure = regs[1]
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        insert_plc_record(ts, temp, pressure)
        return jsonify({"temperature": temp, "pressure": pressure, "timestamp": ts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @app.route("/fetch_data")
# def fetch_data():
#     return jsonify({"temperature": 25, "pressure": 45}), 200

@app.route("/historian")
def historian():
    duration = request.args.get("duration", "all")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if duration == "1min":
            start_ts = datetime.utcnow() - timedelta(minutes=1)
            cur.execute("SELECT timestamp, temperature, pressure FROM plc_data WHERE timestamp >= ? ORDER BY timestamp ASC",
                        (start_ts.strftime("%Y-%m-%d %H:%M:%S"),))
        elif duration == "1h":
            start_ts = datetime.utcnow() - timedelta(hours=1)
            cur.execute("SELECT timestamp, temperature, pressure FROM plc_data WHERE timestamp >= ? ORDER BY timestamp ASC",
                        (start_ts.strftime("%Y-%m-%d %H:%M:%S"),))
        else:
            cur.execute("SELECT timestamp, temperature, pressure FROM plc_data ORDER BY timestamp ASC")

        rows = cur.fetchall()
        conn.close()
        data = [{"timestamp": r[0], "temperature": r[1], "pressure": r[2]} for r in rows]
        return jsonify(data)
    except Exception as e:
        print("[app] Historian error:", e)
        return jsonify([]), 500
    
# @app.route("/historian")
# def historian():
#     # Dummy data instead of DB
#     data = [
#         {"timestamp": "2025-11-13 22:00:01", "temperature": 25, "pressure": 45},
#         {"timestamp": "2025-11-13 24:00:02", "temperature": 14, "pressure": 46},
#         {"timestamp": "2025-11-13 22:00:03", "temperature": 27, "pressure": 44},
#     ]
#     return jsonify(data)

# ---------- CSV Download ----------
@app.route("/download_csv")
def download_csv():
    filename = "plc_data_export.csv"
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT timestamp, temperature, pressure FROM plc_data ORDER BY timestamp ASC")
        rows = cur.fetchall()
        conn.close()

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Timestamp", "Temperature (°C)", "Pressure (bar)"])
            writer.writerows(rows)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        print("[app] CSV export error:", e)
        return "Error generating CSV file", 500

# ---------- Startup ----------
if __name__ == "__main__":
    init_db()
    start_background_logger()
    app.run(host="0.0.0.0", port=5000, debug=True)
