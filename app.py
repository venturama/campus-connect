
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "campusconnect.db")

app = Flask(__name__)
app.secret_key = "demo-secret-key"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            DROP TABLE IF EXISTS payments;
            DROP TABLE IF EXISTS registrations;
            DROP TABLE IF EXISTS students;
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
                seatsUsed INTEGER DEFAULT 0,
                tuition_fee REAL DEFAULT 1000
            );

            CREATE TABLE students (
                student_id TEXT PRIMARY KEY,
                name TEXT
            );

            CREATE TABLE registrations (
                reg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(student_id, course_id)
            );

            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                amount_paid REAL NOT NULL,
                payment_method TEXT,
                paid_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    courses = [
        {
            "id": "CSCI101-A",
            "dept": "CSCI",
            "number": 101,
            "title": "Intro to Programming",
            "credits": 3,
            "prereq": None,
            "modality": "In-person",
            "max": 30,
            "instructor": "Dr. Smith",
            "when_text": "Mon/Wed 9:00–10:15",
            "location": "Hibbs 120",
            "seatsUsed": 12,
            "tuition_fee": 900,
        },
        {
            "id": "INFO361-01",
            "dept": "INFO",
            "number": 361,
            "title": "Systems Analysis & Design",
            "credits": 3,
            "prereq": "CSCI101-A",
            "modality": "In-person",
            "max": 30,
            "instructor": "Prof. Lee",
            "when_text": "Tue/Thu 11:00–12:15",
            "location": "Snead 205",
            "seatsUsed": 30,
            "tuition_fee": 1100,
        },
        {
            "id": "CSCI245-B",
            "dept": "CSCI",
            "number": 245,
            "title": "Data Structures",
            "credits": 3,
            "prereq": "CSCI101-A",
            "modality": "Online",
            "max": 25,
            "instructor": "Dr. Johnson",
            "when_text": "Asynchronous",
            "location": "Canvas",
            "seatsUsed": 22,
            "tuition_fee": 1050,
        },
    ]

    conn = get_db()
    try:
        conn.executemany(
            """
            INSERT OR REPLACE INTO courses
            (id, dept, number, title, credits, prereq, modality, max,
             instructor, when_text, location, seatsUsed, tuition_fee)
            VALUES
            (:id, :dept, :number, :title, :credits, :prereq, :modality, :max,
             :instructor, :when_text, :location, :seatsUsed, :tuition_fee)
            """,
            courses,
        )
        conn.commit()
    finally:
        conn.close()


@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()
        seed_db()


def compute_billing(student_id: str):
    conn = get_db()
    try:
        due_row = conn.execute(
            """
            SELECT COALESCE(SUM(c.tuition_fee), 0) AS total_due
            FROM registrations r
            JOIN courses c ON c.id = r.course_id
            WHERE r.student_id = ?
            """,
            (student_id,),
        ).fetchone()
        amount_due = due_row["total_due"] if due_row else 0

        paid_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount_paid), 0) AS total_paid
            FROM payments
            WHERE student_id = ?
            """,
            (student_id,),
        ).fetchone()
        total_paid = paid_row["total_paid"] if paid_row else 0

        last_payment = conn.execute(
            """
            SELECT amount_paid, payment_method, paid_at
            FROM payments
            WHERE student_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id,),
        ).fetchone()
    finally:
        conn.close()

    if amount_due == 0:
        status = "NO BALANCE"
    elif total_paid >= amount_due:
        status = "PAID"
    else:
        status = "NOT PAID"

    return amount_due, total_paid, status, last_payment


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        sid = request.form.get("student_id", "").strip()
        if not name or not sid:
            flash("Please enter both name and student ID.", "warning")
            return redirect(url_for("login"))

        session["student_name"] = name
        session["student_id"] = sid
        session.pop("is_admin", None)
        flash(f"Welcome, {name}!", "success")

        conn = get_db()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO students (student_id, name) VALUES (?, ?)",
                (sid, name),
            )
            conn.commit()
        finally:
            conn.close()

        return redirect(url_for("my_courses"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/search")
def search():
    # Use original search.html template
    return render_template("search.html")


@app.route("/register/<course_id>", methods=["POST"])
def register(course_id):
    if "student_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    sid = session["student_id"]
    conn = get_db()
    try:
        course = conn.execute(
            "SELECT * FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
        if not course:
            flash("Course not found.", "danger")
            return redirect(request.headers.get("Referer") or url_for("my_courses"))

        prereq_id = course["prereq"]
        if prereq_id:
            has_prereq = conn.execute(
                """
                SELECT 1 FROM registrations
                WHERE student_id = ? AND course_id = ?
                """,
                (sid, prereq_id),
            ).fetchone()
            if not has_prereq:
                flash(
                    f"Prerequisite required: {prereq_id}. You must complete it before registering for {course['id']}.",
                    "warning",
                )
                return redirect(
                    request.headers.get("Referer") or url_for("my_courses")
                )

        if course["seatsUsed"] >= course["max"]:
            flash("Course is full. No seats remaining.", "warning")
            return redirect(request.headers.get("Referer") or url_for("my_courses"))

        try:
            conn.execute(
                "INSERT INTO registrations (student_id, course_id) VALUES (?, ?)",
                (sid, course_id),
            )
            conn.execute(
                "UPDATE courses SET seatsUsed = seatsUsed + 1 WHERE id = ?",
                (course_id,),
            )
            conn.commit()
            flash("Registered successfully.", "success")
        except sqlite3.IntegrityError:
            flash("You are already registered for this course.", "info")
    finally:
        conn.close()

    return redirect(request.headers.get("Referer") or url_for("my_courses"))


@app.route("/drop/<course_id>", methods=["POST"])
def drop(course_id):
    if "student_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    sid = session["student_id"]
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM registrations WHERE student_id = ? AND course_id = ?",
            (sid, course_id),
        )
        conn.execute(
            """
            UPDATE courses
            SET seatsUsed = CASE WHEN seatsUsed > 0 THEN seatsUsed - 1 ELSE 0 END
            WHERE id = ?
            """
            ,
            (course_id,),
        )
        conn.commit()
        flash("Dropped the course.", "warning")
    finally:
        conn.close()

    return redirect(request.headers.get("Referer") or url_for("my_courses"))


@app.route("/my-courses")
def my_courses():
    if "student_id" not in session:
        flash("Please log in to view your courses.", "warning")
        return redirect(url_for("login"))

    sid = session.get("student_id")
    sname = session.get("student_name", "Demo Student")

    conn = get_db()
    try:
        enrolled = conn.execute(
            """
            SELECT c.*
            FROM registrations r
            JOIN courses c ON c.id = r.course_id
            WHERE r.student_id = ?
            ORDER BY c.dept, c.number
            """,
            (sid,),
        ).fetchall()

        available = conn.execute(
            """
            SELECT c.*
            FROM courses c
            WHERE c.id NOT IN (
                SELECT course_id FROM registrations WHERE student_id = ?
            )
            ORDER BY c.dept, c.number
            """,
            (sid,),
        ).fetchall()
    finally:
        conn.close()

    amount_due, total_paid, payment_status, _ = compute_billing(sid)

    return render_template(
        "my_courses.html",
        student_name=sname,
        student_id=sid,
        enrolled=enrolled,
        available=available,
        payment_status=payment_status,
        amount_due=amount_due,
        total_paid=total_paid,
    )


@app.route("/billing")
def billing():
    if "student_id" not in session:
        flash("Please log in to view billing.", "warning")
        return redirect(url_for("login"))

    sid = session["student_id"]
    sname = session.get("student_name", "Demo Student")

    conn = get_db()
    try:
        enrolled = conn.execute(
            """
            SELECT c.*
            FROM registrations r
            JOIN courses c ON c.id = r.course_id
            WHERE r.student_id = ?
            ORDER BY c.dept, c.number
            """,
            (sid,),
        ).fetchall()
    finally:
        conn.close()

    amount_due, total_paid, status, last_payment = compute_billing(sid)

    return render_template(
        "billing.html",
        student_name=sname,
        student_id=sid,
        enrolled=enrolled,
        amount_due=amount_due,
        total_paid=total_paid,
        payment_status=status,
        last_payment=last_payment,
    )


@app.route("/pay", methods=["POST"])
def pay():
    if "student_id" not in session:
        flash("Please log in to make a payment.", "warning")
        return redirect(url_for("login"))

    sid = session["student_id"]
    payment_method = request.form.get("payment_method", "Credit Card")

    amount_due, total_paid, status, _ = compute_billing(sid)
    remaining = max(amount_due - total_paid, 0)

    if amount_due == 0:
        flash("You have no outstanding balance.", "info")
        return redirect(url_for("billing"))

    if remaining <= 0:
        flash("Your tuition is already marked as PAID.", "info")
        return redirect(url_for("billing"))

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO payments (student_id, amount_paid, payment_method)
            VALUES (?, ?, ?)
            """,
            (sid, remaining, payment_method),
        )
        conn.commit()
    finally:
        conn.close()

    flash(
        f"Payment of ${remaining:,.2f} received via {payment_method}. Your balance is now PAID.",
        "success",
    )
    return redirect(url_for("billing"))


def require_admin():
    if not session.get("is_admin"):
        flash("Admin access required.", "warning")
        return False
    return True


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["is_admin"] = True
            flash("Logged in as admin.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.", "danger")
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
        courses = conn.execute(
            """
            SELECT id, dept, number, title, instructor, seatsUsed, max
            FROM courses
            ORDER BY dept, number
            """
        ).fetchall()
    finally:
        conn.close()

    return render_template("admin_dashboard.html", courses=courses)


@app.route("/admin/course/<course_id>")
def admin_course(course_id):
    if not require_admin():
        return redirect(url_for("admin_login"))

    conn = get_db()
    try:
        course = conn.execute(
            "SELECT * FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
        students = conn.execute(
            """
            SELECT r.student_id
            FROM registrations r
            WHERE r.course_id = ?
            ORDER BY r.student_id
            """,
            (course_id,),
        ).fetchall()
    finally:
        conn.close()

    return render_template("admin_students.html", course=course, students=students)


if __name__ == "__main__":
    app.run(debug=True)
