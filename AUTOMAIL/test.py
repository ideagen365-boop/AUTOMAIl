import requests



json_data = {
    "excel_sheet": "mailid's.xlsx",
    "content": "Hi Mannem Saiteja, this is an automated mail please do not reply to it",
    "subject": "automation of mails",
    "resume": "pdf/word file"
}
res = requests.post("http://127.0.0.1:5000/send_mails", json=json_data).json()
print(res)