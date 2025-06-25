import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from google.generativeai import GenerativeModel, configure

print("Initializing AI email assistant...\n")

# --- User Authentication ---
email_user = input("Enter your Gmail address: ")
email_pass = input("Enter your Gmail app password: ")
API_KEY = input("Enter your Gemini API key: ")

configure(api_key=API_KEY)

# --- Connect to Gmail ---
print("Connecting to Gmail and scanning inbox...")
try:
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(email_user, email_pass)
except imaplib.IMAP4.error:
    print("Login failed. Check your credentials and try again.")
    exit()

imap.select("inbox")

status, messages = imap.search(None, "UNSEEN")
if status != "OK":
    print("Failed to search inbox.")
    imap.logout()
    exit()

email_nums = messages[0].split()

if not email_nums:
    print("No unread emails. Assistant is on standby.")
    imap.logout()
    exit()
else:
    print(f"Detected {len(email_nums)} unread email(s). Generating replies...\n")

model = GenerativeModel("gemini-1.5-flash")

for num in email_nums:
    status, data = imap.fetch(num, "(RFC822)")
    if status != "OK":
        print(f"Failed to retrieve email #{num.decode()}. Skipping.")
        continue

    msg = email.message_from_bytes(data[0][1])
    sender = email.utils.parseaddr(msg.get("From", ""))[1]
    subject = msg.get("Subject", "(No Subject)")

    # --- Extract plain text body ---
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_dispo = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_dispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="ignore")

    # --- Check for image attachments ---
    has_image = any(part.get_content_type().startswith("image/") for part in msg.walk())
    if has_image:
        print(f"Email from {sender} includes an image attachment. (AI currently does not process images.)")

    print(f"Replying to {sender} | Subject: \"{subject}\"")

    # --- AI-generated reply ---
    prompt = f"Write a professional and polite reply to this email:\n\n{body.strip()}"
    try:
        response = model.generate_content(prompt).text.strip()
    except Exception as e:
        print(f"AI error while generating response: {e}")
        response = "Apologies, I'm currently unable to respond properly."

    reply_body = (
        f"Hello,\n\n"
        f"{response}\n\n"
        f"Best regards,\n"
        f"{email_user.split('@')[0]}"
    )

    reply_msg = MIMEText(reply_body)
    reply_msg["Subject"] = "Re: " + subject
    reply_msg["From"] = email_user
    reply_msg["To"] = sender

    # --- Send AI-generated email ---
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(email_user, email_pass)
            smtp.send_message(reply_msg)
        print(f"Replied to {sender} successfully.\n")
    except Exception as e:
        print(f"Failed to send reply to {sender}: {e}")

imap.logout()
print("All done. Assistant is idle.")
