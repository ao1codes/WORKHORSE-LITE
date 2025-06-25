import imaplib, email, smtplib
from email.mime.text import MIMEText
from google.generativeai import GenerativeModel, configure

# === Setup ===
email_user = input("Enter your Gmail: ")
email_pass = input("Enter your app password: ")
API_KEY = input("Enter your Gemini API key: ")
configure(api_key=API_KEY)

# === Login ===
imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(email_user, email_pass)
imap.select("inbox")

# === Search unread emails ===
_, messages = imap.search(None, "UNSEEN")
for num in messages[0].split():
    _, data = imap.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(data[0][1])
    sender = email.utils.parseaddr(msg["From"])[1]

    # === Extract email body ===
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = msg.get_payload(decode=True).decode()

    # === Get AI response ===
    model = GenerativeModel("gemini-1.5-flash")  # You can change the model if needed
    prompt = f"Reply to this email: {body.strip()}"
    try:
        response = model.generate_content(prompt).text
    except:
        response = "Sorry, I couldn't generate a response."

    # === Send reply ===
    smtp = smtplib.SMTP("smtp.gmail.com", 587)
    smtp.starttls()
    smtp.login(email_user, email_pass)

    reply = MIMEText(response)
    reply["Subject"] = "Re: " + msg["Subject"]
    reply["From"] = email_user
    reply["To"] = sender

    smtp.send_message(reply)
    smtp.quit()
    print(f"Replied to {sender}")

imap.logout()
