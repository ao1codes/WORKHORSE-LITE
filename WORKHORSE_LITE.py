import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from google.generativeai import GenerativeModel, configure

print("Welcome! This script will automatically reply to your unread Gmail messages using Gemini AI.\n")
email_user = input("Enter your Gmail address: ")
email_pass = input("Enter your Gmail app password: ")
API_KEY = input("Enter your Gemini API key: ")
configure(api_key=API_KEY)

print("\nLogging in to your Gmail inbox...")

imap = imaplib.IMAP4_SSL("imap.gmail.com")
try:
    imap.login(email_user, email_pass)
except imaplib.IMAP4.error:
    print("Login failed. Please check your email or app password.")
    exit()

imap.select("inbox")

status, messages = imap.search(None, "UNSEEN")

if status != "OK":
    print("Failed to fetch emails.")
    imap.logout()
    exit()

email_nums = messages[0].split()

if not email_nums:
    print("No unread emails found. You're all caught up!")
else:
    print(f"Found {len(email_nums)} unread email(s). Processing...\n")

model = GenerativeModel("gemini-1.5-flash")

for num in email_nums:
    status, data = imap.fetch(num, "(RFC822)")
    if status != "OK":
        print(f"Failed to fetch email #{num.decode()}. Skipping...")
        continue

    msg = email.message_from_bytes(data[0][1])
    sender = email.utils.parseaddr(msg["From"])[1]
    subject = msg.get("Subject", "(No Subject)")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    print(f"Generating reply to email from {sender} with subject: \"{subject}\"...")

    prompt = f"Reply to this email professionally and politely:\n\n{body.strip()}"
    try:
        response = model.generate_content(prompt).text.strip()
    except Exception as e:
        print(f"Error generating response: {e}")
        response = "Sorry, I couldn't generate a response at this time."

    reply_body = (
        f"Hello,\n\n"
        f"{response}\n\n"
        f"Best regards,\n"
        f"{email_user.split('@')[0]}"
    )

    reply = MIMEText(reply_body)
    reply["Subject"] = "Re: " + subject
    reply["From"] = email_user
    reply["To"] = sender

    try:
        smtp = smtplib.SMTP("smtp.gmail.com", 587)
        smtp.starttls()
        smtp.login(email_user, email_pass)
        smtp.send_message(reply)
        smtp.quit()
        print(f"Successfully replied to {sender}.\n")
    except Exception as e:
        print(f"Failed to send reply to {sender}: {e}")

imap.logout()