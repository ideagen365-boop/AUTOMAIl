import os
import smtplib
import ssl
import time
import threading
import mimetypes
from email.message import EmailMessage
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from bulk_mails import send_bulk_emails



# ------------------------------
# Load environment variables
# ------------------------------
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_ADDR = os.getenv("FROM_ADDR", SMTP_USER)
RATE_PER_MINUTE = int(os.getenv("RATE_PER_MINUTE", "30"))  # throttle to avoid spam flags

# Basic validation and helpful hints
def _validate_config():
    errors = []
    if not SMTP_HOST:
        errors.append("SMTP_HOST is empty.")
    if not SMTP_PORT:
        errors.append("SMTP_PORT is empty or invalid.")
    if not SMTP_USER:
        errors.append("SMTP_USER (sender login email) is empty.")
    if not SMTP_PASS:
        errors.append("SMTP_PASS (App Password) is empty.")
    if not FROM_ADDR:
        errors.append("FROM_ADDR (From email) is empty.")
    # Gmail specific hints
    if SMTP_HOST == "smtp.gmail.com":
        if not SMTP_USER.endswith("@gmail.com"):
            errors.append("For Gmail, SMTP_USER should be your Gmail address.")
        if " " in SMTP_PASS:
            errors.append("SMTP_PASS contains spaces. Paste the 16-char App Password without spaces.")
    return errors

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXCEL_EXTS = {"xlsx", "xls"}
ALLOWED_RESUME_EXTS = {"pdf", "doc", "docx"}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---- Job State ----
job_lock = threading.Lock()
job_state = {
    "recipients": [],         # list of emails
    "total": 0,               # total recipients
    "sent": 0,                # count sent successfully
    "running": False,         # is job active
    "stop_event": threading.Event(),
    "last_error": None,
    "log": [],                # list of dicts {email, status, error}
    "resume_path": None       # path to the attached resume (optional)
}

# ------------------------------
# Helpers
# ------------------------------

# def ext_of(filename: str) -> str:
#     return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
#
# def allowed_excel(filename):
#     return ext_of(filename) in ALLOWED_EXCEL_EXTS
#
# def allowed_resume(filename):
#     return ext_of(filename) in ALLOWED_RESUME_EXTS

# def load_recipients_from_excel(filepath):
#     """
#     Expect an Excel file with a column named 'email' (case-insensitive).
#     Supports .xlsx (openpyxl) and .xls (xlrd).
#     """
#     extension = ext_of(filepath)
#     if extension == "xlsx":
#         df = pd.read_excel(filepath, engine="openpyxl")
#     elif extension == "xls":
#         df = pd.read_excel(filepath, engine="xlrd")
#     else:
#         raise ValueError("Unsupported Excel format. Use .xlsx or .xls")
#
#     # Normalize column names
#     lower_map = {c.lower().strip(): c for c in df.columns}
#     if "email" not in lower_map:
#         raise ValueError("Excel must contain a column named 'email'.")
#
#     emails = df[lower_map["email"]].dropna().astype(str).str.strip()
#     # Basic validation + dedup
#     emails = [e for e in emails if "@" in e]
#     unique_emails = sorted(set(emails))
#     return unique_emails

# def send_email_smtp(to_addr, subject, body_text, attachment_path=None):
#     """
#     Send a plain text email; optionally attach a file.
#     Raises exceptions if SMTP or login fails so we can surface the error in UI.
#     """
#     msg = EmailMessage()
#     msg["From"] = FROM_ADDR
#     msg["To"] = to_addr
#     msg["Subject"] = subject
#     msg.set_content(body_text)
#
#     if attachment_path and os.path.exists(attachment_path):
#         mime_type, _ = mimetypes.guess_type(attachment_path)
#         if mime_type is None:
#             maintype, subtype = "application", "octet-stream"
#         else:
#             maintype, subtype = mime_type.split("/", 1)
#         with open(attachment_path, "rb") as f:
#             msg.add_attachment(
#                 f.read(),
#                 maintype=maintype,
#                 subtype=subtype,
#                 filename=os.path.basename(attachment_path)
#             )
#
#     # SMTP send
#     context = ssl.create_default_context()
#     with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
#         server.ehlo()
#         # Use STARTTLS for Gmail/Office365
#         server.starttls(context=context)
#         server.ehlo()
#         # Authentication
#         server.login(SMTP_USER, SMTP_PASS)
#         server.send_message(msg)
#
# def worker_send_emails(message_text, subject="Notification"):
#     """
#     Background thread: sends emails sequentially with throttling.
#     """
#     per_email_delay = 60.0 / max(RATE_PER_MINUTE, 1)
#
#     with job_lock:
#         recipients = list(job_state["recipients"])
#         resume_path = job_state["resume_path"]
#         job_state["running"] = True
#         job_state["stop_event"].clear()
#         job_state["last_error"] = None
#
#     for email in recipients:
#         if job_state["stop_event"].is_set():
#             break
#
#         try:
#             send_email_smtp(email, subject, message_text, attachment_path=resume_path)
#             with job_lock:
#                 job_state["sent"] += 1
#                 job_state["log"].append({"email": email, "status": "sent", "error": None})
#         except smtplib.SMTPAuthenticationError as e:
#             # Authentication errors (e.g., bad app password) -> stop the job and surface cause
#             with job_lock:
#                 job_state["last_error"] = f"SMTP auth failed: {str(e)}. Hint: Use Gmail App Password (no spaces)."
#                 job_state["log"].append({"email": email, "status": "failed", "error": job_state['last_error']})
#             break
#         except Exception as e:
#             # Continue on other transient failures
#             with job_lock:
#                 job_state["last_error"] = str(e)
#                 job_state["log"].append({"email": email, "status": "failed", "error": str(e)})
#         finally:
#             time.sleep(per_email_delay)
#
#     with job_lock:
#         job_state["running"] = False
#
# # ------------------------------
# # Routes
# # ------------------------------
#
# @app.route("/")
# def home():
#     return render_template("home.html", page_message="welcome to automate mails")   # home page message
#
# @app.route("/", methods=["GET"])
# def index():
#     # Show config validation warnings in console (not UI) for quick debugging
#     cfg_errors = _validate_config()
#     if cfg_errors:
#         print("[CONFIG WARN] " + " | ".join(cfg_errors))
#     return render_template("index.html")
#
# @app.route("/upload-excel", methods=["POST"])
# def upload_excel():
#     file = request.files.get("file")
#     if not file or file.filename == "":
#         return jsonify({"ok": False, "error": "No file uploaded."}), 400
#     if not allowed_excel(file.filename):
#         return jsonify({"ok": False, "error": "Only .xlsx or .xls files allowed."}), 400
#
#     fname = secure_filename(file.filename)
#     path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
#     file.save(path)
#
#     try:
#         recipients = load_recipients_from_excel(path)
#     except Exception as e:
#         return jsonify({"ok": False, "error": f"Failed to parse Excel: {e}"}), 400
#
#     with job_lock:
#         job_state["recipients"] = recipients
#         job_state["total"] = len(recipients)
#         job_state["sent"] = 0
#         job_state["log"] = []
#         job_state["last_error"] = None
#
#     return jsonify({"ok": True, "total": len(recipients)})
#
# @app.route("/start", methods=["POST"])
# def start_sending():
#     """
#     Accepts:
#       - form fields: message, subject
#       - optional file: resume
#     """
#     message_text = request.form.get("message", "").strip()
#     subject = request.form.get("subject", "Notification")
#     resume_file = request.files.get("resume")
#
#     with job_lock:
#         if job_state["running"]:
#             return jsonify({"ok": False, "error": "Job already running."}), 409
#         if job_state["total"] == 0:
#             return jsonify({"ok": False, "error": "No recipients loaded. Upload Excel first."}), 400
#
#     if not message_text:
#         return jsonify({"ok": False, "error": "Message (ENTER TEXT) cannot be empty."}), 400
#
#     # Save resume (optional)
#     resume_path = None
#     if resume_file and resume_file.filename:
#         if not allowed_resume(resume_file.filename):
#             return jsonify({"ok": False, "error": "Resume must be .pdf, .doc, or .docx"}), 400
#         safe_name = secure_filename(resume_file.filename)
#         ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#         safe_name = f"{ts}_{safe_name}"
#         resume_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
#         resume_file.save(resume_path)
#
#     with job_lock:
#         job_state["sent"] = 0
#         job_state["log"] = []
#         job_state["last_error"] = None
#         job_state["stop_event"].clear()
#         job_state["resume_path"] = resume_path
#
#     # Validate config before launching worker
#     cfg_errors = _validate_config()
#     if cfg_errors:
#         return jsonify({"ok": False, "error": "Config error: " + " | ".join(cfg_errors)}), 400
#
#     t = threading.Thread(target=worker_send_emails, args=(message_text, subject), daemon=True)
#     t.start()
#
#     return jsonify({"ok": True, "message": "Started sending."})
#
# @app.route("/stop", methods=["POST"])
# def stop_sending():
#     with job_lock:
#         job_state["stop_event"].set()
#     return jsonify({"ok": True, "message": "Stop requested."})
#
# @app.route("/status", methods=["GET"])
# def status():
#     with job_lock:
#         return jsonify({
#             "ok": True,
#             "running": job_state["running"],
#             "total": job_state["total"],
#             "sent": job_state["sent"],
#             "last_error": job_state["last_error"],
#             "log": job_state["log"][-10:],  # last 10 entries
#             "has_resume": bool(job_state["resume_path"])
#         })


@app.route("/send_mails", methods=["POST"])
def automate_mails():
    data = request.get_json()
    excel_sheet = data['excel_sheet']
    email_content = data['content']
    email_subject = data['subject']
    resume = data['resume']
    response = send_bulk_emails(excel_sheet, email_content, email_subject, resume)
    return jsonify(
        {
            "message": response['message'],
            "sent_count": response['count']
        }
    )






if __name__ == "__main__":
    # Helpful console print to confirm loaded config
    # print(f"[SMTP] Host={SMTP_HOST} Port={SMTP_PORT} User={SMTP_USER} From={FROM_ADDR} Rate/min={RATE_PER_MINUTE}")
    app.run(debug=True)
