import os
from datetime import datetime, date
from io import BytesIO

from flask import (
    Flask, render_template, redirect, url_for, request, flash, send_file, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from models import db, User, Student, ClassSession, Attendance

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-this")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'attendance.db')}"
)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # create it automatically if missing (e.g. on a fresh deploy)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def teacher_required():
    if not current_user.is_authenticated or current_user.role != "teacher":
        abort(403)


# ---------------------------------------------------------------- Auth ----

@app.route("/", methods=["GET"])
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if current_user.role == "teacher":
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("student_dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Incorrect username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ----------------------------------------------------------- Teacher area --

@app.route("/teacher")
@login_required
def teacher_dashboard():
    teacher_required()
    sessions = ClassSession.query.order_by(ClassSession.session_date.desc()).all()
    return render_template("teacher_dashboard.html", sessions=sessions)


@app.route("/teacher/students", methods=["GET", "POST"])
@login_required
def manage_students():
    teacher_required()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        student_code = request.form.get("student_code", "").strip()
        class_name = request.form.get("class_name", "").strip()
        photo = request.files.get("photo")

        if not full_name or not student_code or not class_name:
            flash("Name, student code and class are all required.", "error")
            return redirect(url_for("manage_students"))

        if Student.query.filter_by(student_code=student_code).first():
            flash("A student with that code already exists.", "error")
            return redirect(url_for("manage_students"))

        photo_filename = None
        if photo and photo.filename and allowed_file(photo.filename):
            photo_filename = secure_filename(f"{student_code}_{photo.filename}")
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], photo_filename))

        student = Student(
            full_name=full_name,
            student_code=student_code,
            class_name=class_name,
            photo_filename=photo_filename,
        )
        db.session.add(student)
        db.session.flush()  # get student.id before creating the login account

        # Create a matching student login account: username = student code,
        # temporary password = student code too (student should change it later
        # if you add that feature).
        user = User(
            username=student_code,
            password_hash=generate_password_hash(student_code),
            role="student",
            student_id=student.id,
        )
        db.session.add(user)
        db.session.commit()

        flash(f"Student '{full_name}' added. Login username: {student_code}", "success")
        return redirect(url_for("manage_students"))

    students = Student.query.order_by(Student.class_name, Student.full_name).all()
    return render_template("add_student.html", students=students)


@app.route("/teacher/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    teacher_required()
    student = Student.query.get_or_404(student_id)
    if student.user:
        db.session.delete(student.user)
    db.session.delete(student)
    db.session.commit()
    flash("Student removed.", "success")
    return redirect(url_for("manage_students"))


@app.route("/teacher/session/new", methods=["GET", "POST"])
@login_required
def new_session():
    teacher_required()

    if request.method == "POST":
        class_name = request.form.get("class_name", "").strip()
        session_date = request.form.get("session_date") or date.today().isoformat()
        time_label = request.form.get("time_label", "").strip()

        session_obj = ClassSession(
            class_name=class_name,
            session_date=datetime.strptime(session_date, "%Y-%m-%d").date(),
            time_label=time_label,
        )
        db.session.add(session_obj)
        db.session.flush()

        # Pre-fill one attendance row per existing student in that class,
        # defaulted to Absent. The teacher (or later, the camera program)
        # updates these to Present / Unknown.
        students = Student.query.filter_by(class_name=class_name).all()
        for s in students:
            db.session.add(Attendance(session_id=session_obj.id, student_id=s.id, status="absent"))

        db.session.commit()
        flash("Session created.", "success")
        return redirect(url_for("session_detail", session_id=session_obj.id))

    class_names = [c[0] for c in db.session.query(Student.class_name).distinct().all()]
    return render_template("new_session.html", class_names=class_names)


@app.route("/teacher/session/<int:session_id>")
@login_required
def session_detail(session_id):
    teacher_required()
    session_obj = ClassSession.query.get_or_404(session_id)
    records = (
        Attendance.query.filter_by(session_id=session_id)
        .order_by(Attendance.status)
        .all()
    )
    return render_template("session_detail.html", session=session_obj, records=records)


@app.route("/teacher/session/<int:session_id>/mark/<int:record_id>", methods=["POST"])
@login_required
def mark_attendance(session_id, record_id):
    teacher_required()
    record = Attendance.query.get_or_404(record_id)
    new_status = request.form.get("status")
    if new_status in ("present", "absent", "unknown"):
        record.status = new_status
        if new_status == "present" and not record.time_seen:
            record.time_seen = datetime.now().strftime("%H:%M")
        db.session.commit()
    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/teacher/session/<int:session_id>/add_unknown", methods=["POST"])
@login_required
def add_unknown(session_id):
    teacher_required()
    note = request.form.get("note", "Unrecognized face")
    record = Attendance(
        session_id=session_id,
        student_id=None,
        status="unknown",
        time_seen=datetime.now().strftime("%H:%M"),
        note=note,
    )
    db.session.add(record)
    db.session.commit()
    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/teacher/session/<int:session_id>/export")
@login_required
def export_session(session_id):
    teacher_required()
    session_obj = ClassSession.query.get_or_404(session_id)
    records = Attendance.query.filter_by(session_id=session_id).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    ws.merge_cells("A1:D1")
    ws["A1"] = f"{session_obj.class_name} — {session_obj.session_date} {session_obj.time_label or ''}"
    ws["A1"].font = Font(bold=True, size=13)

    headers = ["Student ID", "Student Name", "Status", "Time Seen / Note"]
    ws.append([])
    ws.append(headers)
    header_row = ws.max_row
    for col in range(1, 5):
        cell = ws.cell(row=header_row, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="1B2A4A", end_color="1B2A4A", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    present = absent = unknown = 0
    for r in records:
        if r.status == "present":
            present += 1
            ws.append([r.student.student_code, r.student.full_name, "Present", r.time_seen or ""])
        elif r.status == "absent":
            absent += 1
            ws.append([r.student.student_code, r.student.full_name, "Absent", ""])
        else:
            unknown += 1
            ws.append(["-", "Unknown person", "Unknown", r.note or r.time_seen or ""])

    ws.append([])
    ws.append(["", "Present:", present, ""])
    ws.append(["", "Absent:", absent, ""])
    ws.append(["", "Unknown:", unknown, ""])

    for col, width in zip("ABCD", [14, 28, 14, 22]):
        ws.column_dimensions[col].width = width

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"attendance_{session_obj.class_name}_{session_obj.session_date}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ----------------------------------------------------------- Student area --

@app.route("/student")
@login_required
def student_dashboard():
    if current_user.role != "student":
        abort(403)
    student = current_user.student
    records = (
        Attendance.query.filter_by(student_id=student.id)
        .join(ClassSession)
        .order_by(ClassSession.session_date.desc())
        .all()
    )
    return render_template("student_dashboard.html", student=student, records=records)


# --------------------------------------------------------------- Runner ---

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
