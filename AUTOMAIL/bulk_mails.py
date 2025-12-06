import smtplib, ssl
from email.message import EmailMessage
import pandas as pd


# SMTP_HOST = "smtp.gmail.com"
# SMTP_PORT = 587
# SMTP_USER = "manojyadhav965@gmail.com"
# SMTP_PASS = "yoydjsgslyqvvmjg"  # App Password (no spaces)
# FROM_ADDR = "manojyadhav965@gmail.com"
# TO_ADDR = "mannemsaiteja76@gmail.com"  # send to yourself
#
# msg = EmailMessage()
# msg["Subject"] = "SMTP test"
# msg["From"] = FROM_ADDR
# msg["To"] = TO_ADDR
# msg.set_content("mail check chesko!! mail from Rajesh.")
#
# context = ssl.create_default_context()
#
# # to handle errors used try-except
# try:
#     with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
#         server.starttls(context=context)
#         server.login(SMTP_USER, SMTP_PASS)
#         server.send_message(msg)
#         print("message: mail sent successfully")
# except Exception as e:
#     print(f'message: mail unsuccessful, {str(e)}')



def send_bulk_emails(excel_sheet, email_content, email_subject, resume):
    """
    Expect an Excel file with a column named 'email' (case-insensitive).
    Supports .xlsx (openpyxl) and .xls (xlrd).
    """
    # extension = ext_of(filepath)
    # if extension == "xlsx":
    #     df = pd.read_excel(filepath, engine="openpyxl")
    # elif extension == "xls":
    #     df = pd.read_excel(filepath, engine="xlrd")
    # else:
    #     raise ValueError("Unsupported Excel format. Use .xlsx or .xls")
    #
    # # Normalize column names
    # lower_map = {c.lower().strip(): c for c in df.columns}
    # if "email" not in lower_map:
    #     raise ValueError("Excel must contain a column named 'email'.")
    #
    # emails = df[lower_map["email"]].dropna().astype(str).str.strip()
    # # Basic validation + dedup
    # emails = [e for e in emails if "@" in e]
    # unique_emails = sorted(set(emails))
    # return unique_emails
    try:
        df = pd.read_excel(excel_sheet)
        # print(df.columns.tolist())
        # print(df['mails'].tolist())
        SMTP_HOST = "smtp.gmail.com"
        SMTP_PORT = 587
        SMTP_USER = "manojyadhav965@gmail.com"
        SMTP_PASS = "yoydjsgslyqvvmjg"  # App Password (no spaces)
        FROM_ADDR = "manojyadhav965@gmail.com"

        msg = EmailMessage()
        msg["Subject"] = email_subject
        msg["From"] = FROM_ADDR
        msg.set_content(email_content)

        context = ssl.create_default_context()
        # to handle errors used try-except
        try:
            msg["BCC"] = ",".join(df['mails'].tolist()) # do not use for loop throws error like -->  this There may be at most 1 To headers in a message.Because multiple mails should be separated by comma's.
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
                # print("message: mail sent successfully")
        except Exception as e:
            # print(f'message: mail unsuccessful, {str(e)}')
            return (
                {
                    "message": f"mail sent failed: {str(e)}",
                    "count": 0
                }
            )

    except FileNotFoundError:
        # print("file not found")
        return (
            {
                "message": f"file not found",
                "count": 0
            }
        )

    return {
            "message": "mail sent successfully",
            "count": len(df['mails'])
        }


