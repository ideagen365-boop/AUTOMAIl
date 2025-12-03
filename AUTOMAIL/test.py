
import smtplib, ssl
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manojyadhav965@gmail.com"
SMTP_PASS = "yoydjsgslyqvvmjg"  # App Password (no spaces)
FROM_ADDR = "manojyadhav965@gmail.com"
TO_ADDR = "mannemsaiteja76@gmail.com"  # send to yourself

msg = EmailMessage()
msg["Subject"] = "SMTP test"
msg["From"] = FROM_ADDR
msg["To"] = TO_ADDR
msg.set_content("mail check chesko!! mail from Rajesh.")

context = ssl.create_default_context()
with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
    server.starttls(context=context)
    server.login(SMTP_USER, SMTP_PASS)
    server.send_message(msg)
