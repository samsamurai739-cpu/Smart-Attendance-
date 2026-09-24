# Smart Attendance System — Website Starter

A working Flask website with:
- Login (teacher / student roles)
- Teacher dashboard: create class sessions, manage students, mark attendance by hand
  (so you can test everything before the camera exists), export each session to Excel
- Student dashboard: view your own attendance history

This is the **website only** (Phases 2, 3, 4 from your roadmap). The camera / face
recognition program is a separate piece you connect later — it will simply create
`Attendance` rows the same way the "mark attendance" buttons do here.

---

## 1. Run it on your own computer first

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database + a test teacher account
python seed_data.py

# 4. Run the site
python app.py
```

Open **http://localhost:5000** in your browser.

Log in as the teacher with:
- **Username:** `teacher1`
- **Password:** `teacher123`

Then:
1. Go to **Manage Students** and add a few students (name, code, class, optional photo).
   Each student automatically gets a login: username = their student code, password =
   their student code too.
2. Go to **+ New Session**, create a session for that class.
3. Open the session and mark students **Present**, or add an **Unknown Detection** to
   simulate an unrecognized face — this lets you test the whole flow without a camera.
4. Click **Download Excel** to see the generated attendance sheet.
5. Log out and log back in with a student's username/password to see the student view.

---

## 2. Publish it online (no terminal needed afterward)

These steps use **Render** as an example (Railway and PythonAnywhere follow a similar
pattern):

1. Push this project to a **GitHub repository** (Render deploys directly from GitHub).
2. Go to [render.com](https://render.com), sign up, and click **New → Web Service**.
3. Connect your GitHub repository.
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Add an environment variable `SECRET_KEY` with any random text value (for security).
6. Click **Create Web Service**. Render builds and deploys it automatically.
7. After a minute or two, your site is live at a permanent address like
   `https://your-project-name.onrender.com` — this keeps working with no terminal
   window open on your computer.

**Important limitation to know for your report:** on Render's free tier, the local
SQLite file (`attendance.db`) is **not permanent** — it resets whenever the app
restarts or redeploys. This is fine for demos, but for a real deployment you would
switch `DATABASE_URL` to a free hosted PostgreSQL database (Render offers one) instead
of SQLite. The code already reads `DATABASE_URL` from an environment variable, so this
is a config change, not a code rewrite.

---

## 3. What to build next

- The camera / face-recognition program (Phase 1) — it should call the same kind of
  logic as `mark_attendance()` in `app.py`, but automatically, based on what it
  recognizes, instead of a teacher clicking a button.
- Optional: let students change their password after first login.
- Optional: store face-recognition "faceprints" as a new column on `Student`, generated
  automatically from the uploaded photo.
