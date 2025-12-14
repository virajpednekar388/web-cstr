# app.py
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from plc_logic import read_plc_registers

# ---------- Configuration ----------
PLC_IP = "192.168.1.1"
PLC_PORT = 502
PLC_UNIT_ID = 1

# ---------- Flask setup ----------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supersecretkey"

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

# ---------- LIVE PLC DATA (No Database) ----------
@app.route("/fetch_data")
def fetch_data():
    try:
        regs = read_plc_registers(
            ip=PLC_IP,
            port=PLC_PORT,
            address=40001,
            count=4,
            device_id=PLC_UNIT_ID
        )

        if not regs or len(regs) < 2:
            return jsonify({
                "temperature": None,
                "pressure": None,
                "error": "PLC data invalid"
            }), 200

        data = {
            "temperature": regs[0],
            "pressure": regs[1],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Startup ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
