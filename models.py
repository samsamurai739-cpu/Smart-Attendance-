from datetime import date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(db.Model, UserMixin):
    """A login account. Can belong to a teacher, or be linked to one student."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'

    # Only set when role == 'student'
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=True)
    student = db.relationship("Student", backref=db.backref("user", uselist=False))


class Student(db.Model):
    """A student record: basic info + reference photo filename."""
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    student_code = db.Column(db.String(50), unique=True, nullable=False)
    class_name = db.Column(db.String(80), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=True)

    attendance_records = db.relationship("Attendance", backref="student", lazy=True)


class ClassSession(db.Model):
    """One class session (e.g. 'CS101 - 2026-09-25 - 10:00 lecture')."""
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(80), nullable=False)
    session_date = db.Column(db.Date, nullable=False, default=date.today)
    time_label = db.Column(db.String(50), nullable=True)  # e.g. "10:00 - 11:00"

    records = db.relationship(
        "Attendance", backref="session", cascade="all, delete-orphan", lazy=True
    )


class Attendance(db.Model):
    """One row of a session's result: a student's status, or an unknown detection."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("class_session.id"), nullable=False)

    # NULL when status == 'unknown' (no matching student in the database)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=True)

    status = db.Column(db.String(20), nullable=False)  # 'present' | 'absent' | 'unknown'
    time_seen = db.Column(db.String(20), nullable=True)
    note = db.Column(db.String(120), nullable=True)  # optional note for unknown detections
