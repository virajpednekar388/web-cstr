import os
import threading
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from bisect import bisect_left
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# from plc_logic import read_plc_registers, is_plc_connected
from plc_logic import (
    read_plc_registers,
    is_plc_connected,
    set_valve1_percent,
    set_valve2_percent,
    valve1_open,
    valve1_close,
    valve2_open,
    valve2_close,
)

from supabase import create_client, Client

# ---------------- Supabase Config (Server Only) ----------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")  # server-only key
LOG_SECONDS = int(os.environ.get("LOG_SECONDS", "10"))        # how often to insert into DB

supabase = None
if SUPABASE_URL and SUPABASE_SECRET_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# ---------- PLC CONFIG ----------
PLC_IP = "192.168.1.1"
PLC_PORT = 502
PLC_UNIT_ID = 1

# Optional scaling (example: 253 -> 25.3 means TEMP_SCALE=0.1)
TEMP_SCALE = 1.0
PRESS_SCALE = 1.0

# ---------- TREND STORAGE CONFIG ----------
SAMPLE_SECONDS = 2
WINDOW_HOURS = 24
MAX_POINTS = int((WINDOW_HOURS * 3600) / SAMPLE_SECONDS) + 100

trend_buffer = deque(maxlen=MAX_POINTS)  # {"ts": ms, "temperature": x, "pressure": y}
trend_lock = threading.Lock()
sampler_started = False

# For monitoring
last_sample_ms = 0
sample_ok_count = 0
sample_err_count = 0

# ---------- DATALOG LOGGER CONFIG ----------
logger_started = False
last_db_insert_ms = 0

# ---------- FLASK SETUP ----------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"

# ---------- SIMPLE AUTH ----------
users = {
    "v": generate_password_hash("v"),
    "kale": generate_password_hash("kale@123"),
    "om": generate_password_hash("om@123"),
}

# ---------- AUTH DECORATOR ----------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

# ---------- HELPERS ----------
def utc_ms_now() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------- PLC SAMPLER ----------
def plc_sampler_loop():
    """Read REAL PLC values and append to trend buffer."""
    global last_sample_ms, sample_ok_count, sample_err_count

    while True:
        try:
            regs = read_plc_registers(
                ip=PLC_IP,
                port=PLC_PORT,
                address=40001,
                count=4,
                device_id=PLC_UNIT_ID,
            )

            if regs and len(regs) >= 2:
                point = {
                    "ts": utc_ms_now(),
                    "temperature": float(regs[0]) * TEMP_SCALE,
                    "pressure": float(regs[1]) * PRESS_SCALE,
                }
                with trend_lock:
                    trend_buffer.append(point)
                    last_sample_ms = point["ts"]
                sample_ok_count += 1
            else:
                sample_err_count += 1

        except Exception:
            sample_err_count += 1

        time.sleep(SAMPLE_SECONDS)

def start_sampler_once():
    """Start sampler only once; avoid double thread with Flask reloader."""
    global sampler_started
    if sampler_started:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    t = threading.Thread(target=plc_sampler_loop, daemon=True)
    t.start()
    sampler_started = True

# ---------- SUPABASE LOGGER ----------
def supabase_logger_loop():
    global last_db_insert_ms

    if supabase is None:
        print("[datalog] Supabase not configured. Set SUPABASE_URL and SUPABASE_SECRET_KEY.")
        return

    last_logged_sample_ms = 0

    while True:
        try:
            with trend_lock:
                latest = trend_buffer[-1] if trend_buffer else None

            if latest:
                row = {
                    "ts": iso_utc_now(),
                    "temperature": latest["temperature"],
                    "pressure": latest["pressure"],
                    "status": "OK",
                }
            else:
                row = {
                    "ts": iso_utc_now(),
                    "temperature": None,
                    "pressure": None,
                    "status": "PLC_DISCONNECTED",
                }

            supabase.table("scada_logs").insert(row).execute()


        except Exception as e:
            print("[datalog] insert error:", e)

        time.sleep(LOG_SECONDS)


def start_logger_once():
    """Start DB logger once; avoid double thread with Flask reloader."""
    global logger_started
    if logger_started:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    t = threading.Thread(target=supabase_logger_loop, daemon=True)
    t.start()
    logger_started = True

# ---------------- ROUTES ----------------
@app.route("/plc-status")
def plc_status():
    connected = is_plc_connected(ip=PLC_IP, port=PLC_PORT)
    return jsonify({"connected": connected})

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

@app.route("/Trends")
def Trends():
    if "user" not in session:
        return redirect(url_for("login"))
    start_sampler_once()
    return render_template("Trends.html", user=session.get("user"))

@app.route("/DataLog")
def DataLog():
    if "user" not in session:
        return redirect(url_for("login"))
    # Start sampler + logger so DB fills automatically
    start_sampler_once()
    start_logger_once()
    return render_template("DataLog.html", user=session.get("user"))

@app.route("/fetch_data")
@login_required
def fetch_data():
    """Latest PLC read (optional)."""
    try:
        regs = read_plc_registers(
            ip=PLC_IP,
            port=PLC_PORT,
            address=40001,
            count=4,
            device_id=PLC_UNIT_ID
        )

        if not regs or len(regs) < 2:
            return jsonify({"temperature": None, "pressure": None, "error": "PLC data invalid"}), 200

        return jsonify({
            "temperature": float(regs[0]) * TEMP_SCALE,
            "pressure": float(regs[1]) * PRESS_SCALE,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------- Trends API (windowed points) --------
@app.get("/api/trends")
@login_required
def api_trends():
    start_sampler_once()

    window_min = max(1, min(int(request.args.get("window", "60")), 1440))
    step_sec = max(0, int(request.args.get("step", "0")))
    cutoff_ms = utc_ms_now() - (window_min * 60 * 1000)

    with trend_lock:
        buf = list(trend_buffer)

    if not buf:
        return jsonify({"ok": True, "window_min": window_min, "sample_seconds": SAMPLE_SECONDS, "points": []})

    ts_list = [p["ts"] for p in buf]
    start_idx = bisect_left(ts_list, cutoff_ms)
    points = buf[start_idx:]

    if step_sec > 0 and points:
        min_gap = step_sec * 1000
        filtered = []
        last_ts = 0
        for p in points:
            if p["ts"] - last_ts >= min_gap:
                filtered.append(p)
                last_ts = p["ts"]
        points = filtered

    return jsonify({
        "ok": True,
        "window_min": window_min,
        "sample_seconds": SAMPLE_SECONDS,
        "points": points
    })

# -------- DataLog API (reads from Supabase) --------
@app.get("/api/logs")
@login_required
def api_logs():
    if supabase is None:
        return jsonify({"error": "Supabase not configured"}), 500

    limit = int(request.args.get("limit", "100"))
    limit = max(1, min(limit, 1000))

    preset = request.args.get("preset")  # "10m" | "1h" | "24h"
    from_iso = request.args.get("from")
    to_iso = request.args.get("to")

    q = supabase.table("scada_logs").select("ts,temperature,pressure").order("ts", desc=True)

    now = datetime.now(timezone.utc)
    if preset == "10m":
        q = q.gte("ts", (now - timedelta(minutes=10)).isoformat())
    elif preset == "1h":
        q = q.gte("ts", (now - timedelta(hours=1)).isoformat())
    elif preset == "24h":
        q = q.gte("ts", (now - timedelta(hours=24)).isoformat())

    if from_iso:
        q = q.gte("ts", from_iso)
    if to_iso:
        q = q.lte("ts", to_iso)

    resp = q.limit(limit).execute()
    rows = resp.data or []

    # return oldest -> newest (better for reading in table)
    rows.reverse()

    return jsonify([
        {"timestamp": r["ts"], "temperature": r["temperature"], "pressure": r["pressure"]}
        for r in rows
    ])
    
    
# write to plc code

# ---------------- WRITE TO PLC (VALVES) ----------------

def _parse_valve_payload():
    """
    Accept JSON body:
      - {"percent": 0..100}   OR
      - {"command": "open"|"close"}
    Returns: (mode, value) where mode in {"percent","command"}
    """
    data = request.get_json(silent=True) or {}

    # command mode
    cmd = data.get("command")
    if isinstance(cmd, str):
        cmd = cmd.strip().lower()
        if cmd in ("open", "close"):
            return ("command", cmd)

    # percent mode
    if "percent" in data:
        try:
            pct = int(float(data["percent"]))
            pct = max(0, min(100, pct))
            return ("percent", pct)
        except Exception:
            pass

    return (None, None)


@app.post("/api/valve1")
@login_required
def api_valve1_write():
    mode, value = _parse_valve_payload()
    if mode is None:
        return jsonify({"ok": False, "error": "Send JSON: {'percent':0..100} OR {'command':'open'|'close'}"}), 400

    # Use your same PLC config
    if mode == "command":
        if value == "open":
            msg = valve1_open(ip=PLC_IP, port=PLC_PORT, slave_id=PLC_UNIT_ID)
        else:
            msg = valve1_close(ip=PLC_IP, port=PLC_PORT, slave_id=PLC_UNIT_ID)
        return jsonify({"ok": True, "valve": 1, "command": value, "result": msg})

    # percent mode
    msg = set_valve1_percent(value, ip=PLC_IP, port=PLC_PORT, slave_id=PLC_UNIT_ID)
    return jsonify({"ok": True, "valve": 1, "percent": value, "result": msg})


@app.post("/api/valve2")
@login_required
def api_valve2_write():
    mode, value = _parse_valve_payload()
    if mode is None:
        return jsonify({"ok": False, "error": "Send JSON: {'percent':0..100} OR {'command':'open'|'close'}"}), 400

    if mode == "command":
        if value == "open":
            msg = valve2_open(ip=PLC_IP, port=PLC_PORT, slave_id=PLC_UNIT_ID)
        else:
            msg = valve2_close(ip=PLC_IP, port=PLC_PORT, slave_id=PLC_UNIT_ID)
        return jsonify({"ok": True, "valve": 2, "command": value, "result": msg})

    msg = set_valve2_percent(value, ip=PLC_IP, port=PLC_PORT, slave_id=PLC_UNIT_ID)
    return jsonify({"ok": True, "valve": 2, "percent": value, "result": msg})


@app.route("/write-plc")
def write_plc_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("write_plc.html", user=session.get("user"))



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
