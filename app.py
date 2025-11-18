
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "campusconnect.db")

app = Flask(__name__)
app.secret_key = "demo-secret-key"  # replace in production

# --- Admin credentials for Sprint 2 demo ---
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    try:
        conn.executescript("""
        PRAGMA foreign_keys=ON;
        DROP TABLE IF EXISTS registrations;
        DROP TABLE IF EXISTS courses;
        CREATE TABLE courses (
            id TEXT PRIMARY KEY,
            dept TEXT,
            number INTEGER,
            title TEXT,
            credits INTEGER,
            prereq TEXT,
            modality TEXT,
            max INTEGER,
            instructor TEXT,
            when_text TEXT,
            location TEXT,
            seatsUsed INTEGER
        );
        CREATE TABLE registrations (
            reg_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            UNIQUE(student_id, course_id)
        );
        """)
        conn.commit()
    finally:
        conn.close()

def seed_db():
    courses = [
        {"id":"CSCI101-A","dept":"CSCI","number":101,"title":"Intro to Programming","credits":3,"prereq":"None","modality":"In-person","max":30,"instructor":"Dr.Smith","when_text":"Mon/Wed 9:00–10:15","location":"Hibbs 120","seatsUsed":12},
        {"id":"INFO361-01","dept":"INFO","number":361,"title":"Systems Analysis & Design","credits":3,"prereq":"INFO 202","modality":"Hybrid","max":35,"instructor":"Prof.Lee","when_text":"Tue/Thu 11:00–12:15","location":"Snead 205","seatsUsed":30},
        {"id":"CSCI245-B","dept":"CSCI","number":245,"title":"Data Structures","credits":4,"prereq":"CSCI 101","modality":"Online","max":25,"instructor":"Dr.Smith","when_text":"Asynchronous","location":"Canvas","seatsUsed":22},
    ]
    conn = get_db()
    try:
        conn.executemany("""
            INSERT OR REPLACE INTO courses (id, dept, number, title, credits, prereq, modality, max, instructor, when_text, location, seatsUsed)
            VALUES (:id, :dept, :number, :title, :credits, :prereq, :modality, :max, :instructor, :when_text, :location, :seatsUsed)
        """, courses)
        conn.commit()
    finally:
        conn.close()

@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()
        seed_db()

# -------------- Student-facing routes --------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        sid = request.form.get("student_id","").strip()
        if not name or not sid:
            flash("Please enter both name and student ID.", "warning")
            return redirect(url_for("login"))
        session["student_name"] = name
        session["student_id"] = sid
        session.pop("is_admin", None)  # ensure clean context
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("my_courses"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/register/<course_id>", methods=["POST"])
def register(course_id):
    if "student_id" not in session:
        session["student_name"] = "Demo Student"
        session["student_id"] = "100234"
    sid = session["student_id"]
    conn = get_db()
    try:
        try:
            conn.execute("INSERT INTO registrations (student_id, course_id) VALUES (?,?)", (sid, course_id))
            conn.commit()
            flash("Registered successfully.", "success")
        except sqlite3.IntegrityError:
            flash("Already registered for this course.", "info")
    finally:
        conn.close()
    ref = request.headers.get("Referer")
    return redirect(ref or url_for("my_courses"))

@app.route("/drop/<course_id>", methods=["POST"])
def drop(course_id):
    if "student_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    sid = session["student_id"]
    conn = get_db()
    try:
        conn.execute("DELETE FROM registrations WHERE student_id=? AND course_id=?", (sid, course_id))
        conn.commit()
        flash("Dropped the course.", "warning")
    finally:
        conn.close()
    ref = request.headers.get("Referer")
    return redirect(ref or url_for("my_courses"))

@app.route("/my-courses")
def my_courses():
    sid = session.get("student_id", "100234")
    sname = session.get("student_name", "Demo Student")
    conn = get_db()
    try:
        enrolled = conn.execute("""
            SELECT c.* FROM registrations r
            JOIN courses c ON c.id=r.course_id
            WHERE r.student_id=?
            ORDER BY c.dept, c.number
        """, (sid,)).fetchall()
        available = conn.execute("""
            SELECT c.* FROM courses c
            WHERE c.id NOT IN (SELECT course_id FROM registrations WHERE student_id=?)
            ORDER BY c.dept, c.number
        """, (sid,)).fetchall()
    finally:
        conn.close()
    return render_template("my_courses.html", student_name=sname, student_id=sid, enrolled=enrolled, available=available)

# -------------- Admin routes --------------
def require_admin():
    if not session.get("is_admin"):
        flash("Admin access required.", "warning")
        return False
    return True

@app.route("/admin-login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username","").strip()
        pw = request.form.get("password","").strip()
        if user == ADMIN_USER and pw == ADMIN_PASS:
            # clear student state for separation
            session.clear()
            session["is_admin"] = True
            flash("Welcome, Admin.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "warning")
        return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("index"))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))
    conn = get_db()
    try:
        courses = conn.execute("""
            SELECT id, dept, number, title, instructor, seatsUsed, max
            FROM courses
            ORDER BY dept, number
        """).fetchall()
    finally:
        conn.close()
    return render_template("admin_dashboard.html", courses=courses)

@app.route("/admin/course/<course_id>")
def admin_course(course_id):
    if not require_admin():
        return redirect(url_for("admin_login"))
    conn = get_db()
    try:
        course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        students = conn.execute("""
            SELECT r.student_id
            FROM registrations r
            WHERE r.course_id=?
            ORDER BY r.student_id
        """, (course_id,)).fetchall()
    finally:
        conn.close()
    return render_template("admin_students.html", course=course, students=students)

if __name__ == "__main__":
    app.run(debug=True)
