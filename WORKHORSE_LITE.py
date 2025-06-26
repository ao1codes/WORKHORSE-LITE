import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv
import os
import time
import html

# === Pretty Terminal Colors ===
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text): print(f"{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.RESET}")
def print_info(text): print(f"{Colors.CYAN}[INFO]{Colors.RESET} {text}")
def print_success(text): print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {text}")
def print_warning(text): print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {text}")
def print_error(text): print(f"{Colors.RED}[ERROR]{Colors.RESET} {text}")

# === HTML Response Builder ===
def create_html_body(original_body, ai_response):
    def safe_html(text): return html.escape(text).replace('\n', '<br>')
    return f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f9f9f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 700px; margin: auto; background: white; padding: 20px;
            border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #ddd; }}
        h2 {{ color: #333; font-size: 20px; border-bottom: 2px solid #007bff; padding-bottom: 8px; }}
        p {{ font-size: 15px; color: #555; line-height: 1.5; }}
        .response-box {{ background-color: #f0f4ff; border: 1px solid #b3c7ff; padding: 15px;
            border-radius: 6px; color: #222; font-size: 15px; white-space: pre-wrap; margin-top: 10px; }}
        .footer {{ margin-top: 30px; font-size: 13px; color: #888; text-align: center; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>You asked:</h2>
        <p>{safe_html(original_body)}</p>
        <h2>AI Response:</h2>
        <div class="response-box">{safe_html(ai_response)}</div>
        <div class="footer">AI Assistant • ao1codes</div>
    </div>
</body>
</html>
"""

def main():
    print_header("ao1codes Email Bot Booting Up")

    # Load credentials from .env file
    load_dotenv()
    email_user = os.getenv("EMAIL_ADDRESS")
    email_pass = os.getenv("EMAIL_PASSWORD")
    api_key = os.getenv("GEMINI_API_KEY")
    configure(api_key=api_key)

    print_info("Connecting to Gmail IMAP...")
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(email_user, email_pass)
        print_success("Logged in to Gmail!")
    except Exception as e:
        print_error(f"Login failed: {e}")
        return

    model = GenerativeModel("gemini-1.5-flash")
    print_info("Watching inbox every 10 seconds...\nCtrl+C to stop.")

    try:
        while True:
            try:
                imap.select("inbox")
                status, messages = imap.search(None, "UNSEEN")
                if status != "OK":
                    print_error("Search failed.")
                    time.sleep(10)
                    continue
            except Exception as e:
                print_error(f"Reconnecting IMAP: {e}")
                time.sleep(5)
                try: imap.logout()
                except: pass
                imap = imaplib.IMAP4_SSL("imap.gmail.com")
                imap.login(email_user, email_pass)
                continue

            email_nums = messages[0].split()
            if not email_nums:
                print_info("No new emails. Snoozing...")
            else:
                print_success(f"Found {len(email_nums)} new email(s)!")

            for num in email_nums:
                status, data = imap.fetch(num, "(RFC822)")
                if status != "OK":
                    print_warning(f"Failed to fetch #{num.decode()}")
                    continue

                msg = email.message_from_bytes(data[0][1])
                sender_name, sender_email = email.utils.parseaddr(msg.get("From", ""))
                subject = msg.get("Subject") or "Your message"

                # === Extract plain body
                body, has_attachment = "", False
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disp = str(part.get("Content-Disposition", ""))
                        if content_type.startswith("image/") or "attachment" in content_disp:
                            has_attachment = True
                        elif content_type == "text/plain" and "attachment" not in content_disp:
                            payload = part.get_payload(decode=True)
                            if payload: body = payload.decode(errors="ignore")
                else:
                    payload = msg.get_payload(decode=True)
                    if payload: body = payload.decode(errors="ignore")

                prompt = body.strip()
                if not prompt:
                    prompt = "(No prompt provided)"
                first_line = prompt.splitlines()[0].strip() if prompt.strip() else "Your message"
                reply_subject = first_line if first_line else "Re: Your question"

                # === Message decision
                if has_attachment:
                    print_warning(f"{sender_email} sent an attachment. Skipping AI.")
                    response = "Thanks for reaching out! We currently don’t process emails with attachments. Please resend your message without files."
                else:
                    print_info(f"Generating AI response for: {first_line[:60]}...")
                    try:
                        response = model.generate_content(prompt).text.strip()
                        print_success("Got response!")
                    except Exception as e:
                        print_error(f"AI failed: {e}")
                        response = "Sorry, I had trouble generating a response to your message. Please try again later."

                html_body = create_html_body(prompt, response)

                reply_msg = MIMEText(html_body, "html")
                reply_msg["Subject"] = reply_subject
                reply_msg["From"] = email_user
                reply_msg["To"] = sender_email

                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                        smtp.starttls()
                        smtp.login(email_user, email_pass)
                        smtp.send_message(reply_msg)
                    print_success(f"Replied to {sender_email}")
                    imap.store(num, '+FLAGS', '\\Seen')
                except Exception as e:
                    print_error(f"Reply failed: {e}")

                time.sleep(1)
            time.sleep(10)

    except KeyboardInterrupt:
        print_info("Shutting down gracefully...")
        imap.logout()
        print_success("Logged out. Bye!")

if __name__ == "__main__":
    main()
