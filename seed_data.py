"""
Run this ONCE to create the database tables and a test teacher login.
Usage:  python seed_data.py
"""
from werkzeug.security import generate_password_hash
from app import app
from models import db, User

with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="teacher1").first():
        teacher = User(
            username="teacher1",
            password_hash=generate_password_hash("teacher123"),
            role="teacher",
        )
        db.session.add(teacher)
        db.session.commit()
        print("Created teacher account -> username: teacher1 | password: teacher123")
    else:
        print("Teacher account already exists.")

    print("Database ready. Log in as the teacher, then use 'Manage Students' to add")
    print("students (each gets its own student login automatically), then 'New Session'")
    print("to create a test session and mark attendance by hand.")
