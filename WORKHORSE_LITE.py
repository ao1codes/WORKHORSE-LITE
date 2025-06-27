import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv
import os
import time
import html
import re

DEBUG = False

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

conversation_history = {}

def is_likely_reply(subject, body, sender_email):
    subject_lower = subject.lower() if subject else ""
    has_explicit_reply_subject = subject_lower.startswith('re:')
    
    body_lower = body.lower() if body else ""
    has_quoted_content = ('>' in body or 
                         'wrote:' in body_lower or 
                         'ai assistant' in body_lower or 
                         'ao1codes' in body_lower or
                         '<html>' in body_lower)
    
    body_start = body.strip()[:50].lower()
    continuation_starters = ['and ', 'also ', 'what about', 'how about', 'additionally', 'furthermore']
    is_short_continuation = (len(body.strip()) < 100 and 
                           any(body_start.startswith(starter) for starter in continuation_starters))
    
    references_previous = any(phrase in body_lower for phrase in [
        'you said', 'you mentioned', 'earlier you', 'previously', 'before you',
        'your previous', 'last time', 'you told me'
    ])
    
    if DEBUG:
        print_info(f"Reply detection for {sender_email}:")
        print_info(f"  - Has explicit reply subject: {has_explicit_reply_subject}")
        print_info(f"  - Has quoted content: {has_quoted_content}")
        print_info(f"  - Is short continuation: {is_short_continuation}")
        print_info(f"  - References previous: {references_previous}")
    
    is_reply = (has_explicit_reply_subject or 
                has_quoted_content or 
                is_short_continuation or 
                references_previous)
    
    if DEBUG:
        print_info(f"  - Final decision: {'REPLY' if is_reply else 'NEW CONVERSATION'}")
    return is_reply

def extract_latest_message(body):
    lines = body.split('\n')
    latest_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        if (stripped.startswith('>') or 
            'wrote:' in stripped.lower() or
            'original message' in stripped.lower() or
            'ai assistant' in stripped.lower() or
            '<html>' in stripped.lower()):
            break
            
        if 'ao1codes' in stripped or 'ai assistant' in stripped:
            continue
            
        latest_lines.append(line)
    
    latest_message = '\n'.join(latest_lines).strip()
    
    if not latest_message or len(latest_message) < 5:
        latest_message = body.strip()
    
    return latest_message

def update_conversation_history(sender_email, user_message, ai_response):
    if sender_email not in conversation_history:
        conversation_history[sender_email] = []
    
    conversation_history[sender_email].append({
        'type': 'user',
        'message': user_message,
        'timestamp': time.time()
    })
    
    conversation_history[sender_email].append({
        'type': 'ai',
        'message': ai_response,
        'timestamp': time.time()
    })
    
    if len(conversation_history[sender_email]) > 20:
        conversation_history[sender_email] = conversation_history[sender_email][-20:]

def start_new_conversation(sender_email):
    if sender_email in conversation_history:
        del conversation_history[sender_email]
    if DEBUG:
        print_info(f"Started new conversation thread for {sender_email}")

def build_conversation_context(sender_email, current_message):
    if sender_email not in conversation_history or len(conversation_history[sender_email]) == 0:
        return current_message
    
    context_parts = []
    history = conversation_history[sender_email]
    
    recent_history = history[-6:] if len(history) > 6 else history
    
    for entry in recent_history:
        if entry['type'] == 'user':
            context_parts.append(f"USER: {entry['message']}")
        else:
            context_parts.append(f"AI_ASSISTANT: {entry['message']}")
    
    context_parts.append(f"USER: {current_message}")
    
    return "\n\n".join(context_parts)

def create_html_body(latest_message, ai_response, is_thread=False, thread_count=1):
    def safe_html(text): return html.escape(text).replace('\n', '<br>')
    
    if is_thread and thread_count > 1:
        thread_info = f" • {thread_count} exchanges"
    else:
        thread_info = " • New conversation"
    
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
        .thread-badge {{ background-color: #28a745; color: white; padding: 2px 8px; border-radius: 12px; 
            font-size: 11px; font-weight: bold; margin-left: 10px; }}
        .new-badge {{ background-color: #007bff; color: white; padding: 2px 8px; border-radius: 12px; 
            font-size: 11px; font-weight: bold; margin-left: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>You asked:</h2>
        <p>{safe_html(latest_message)}</p>
        <h2>AI Response:</h2>
        <div class="response-box">{safe_html(ai_response)}</div>
        <div class="footer">AI Assistant • ao1codes{thread_info}</div>
    </div>
</body>
</html>
"""

def main():
    print_header("ao1codes Email Bot Booting Up")

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
    print_info("Watching inbox every 5 seconds...\nCtrl+C to stop.")

    try:
        while True:
            try:
                imap.select("inbox")
                status, messages = imap.search(None, "UNSEEN")
                if status != "OK":
                    print_error("Search failed.")
                    time.sleep(5)
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

                is_thread = is_likely_reply(subject, body, sender_email)
                latest_message = extract_latest_message(body)
                
                if is_thread:
                    thread_count = len(conversation_history.get(sender_email, [])) // 2 + 1
                    print_info(f"📧 Continuing conversation (Exchange #{thread_count})")
                    conversation_context = build_conversation_context(sender_email, latest_message)
                    prompt_for_ai = f"""You are an AI email assistant continuing an ongoing conversation.

CONVERSATION HISTORY:
{conversation_context}

INSTRUCTIONS:
- This is a continuation of our conversation
- Reference previous context when relevant
- Be natural and conversational
- Remember what we discussed before

Please respond to the user's latest message:"""
                else:
                    start_new_conversation(sender_email)
                    thread_count = 1
                    print_info("📧 New conversation started")
                    prompt_for_ai = latest_message.strip() if latest_message.strip() else "(No prompt provided)"

                first_line = latest_message.splitlines()[0].strip() if latest_message.strip() else "Your message"
                reply_subject = f"Prompt: {first_line}" if first_line else "Prompt: Your question"

                if has_attachment:
                    print_warning(f"{sender_email} sent an attachment. Skipping AI.")
                    response = "Thanks for reaching out! We currently don't process emails with attachments. Please resend your message without files."
                else:
                    print_info(f"Generating AI response for: {first_line[:60]}...")
                    try:
                        response = model.generate_content(prompt_for_ai).text.strip()
                        print_success("Got response!")
                    except Exception as e:
                        print_error(f"AI failed: {e}")
                        response = "Sorry, I had trouble generating a response to your message. Please try again later."

                if not has_attachment:
                    update_conversation_history(sender_email, latest_message, response)

                html_body = create_html_body(latest_message, response, is_thread, thread_count)

                reply_msg = MIMEText(html_body, "html")
                reply_msg["Subject"] = reply_subject
                reply_msg["From"] = email_user
                reply_msg["To"] = sender_email

                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                        smtp.starttls()
                        smtp.login(email_user, email_pass)
                        smtp.send_message(reply_msg)
                    thread_indicator = f" (Exchange #{thread_count})" if is_thread else " (New)"
                    print_success(f"Replied to {sender_email}{thread_indicator}")
                    imap.store(num, '+FLAGS', '\\Seen')
                except Exception as e:
                    print_error(f"Reply failed: {e}")

                time.sleep(1)
            time.sleep(5)

    except KeyboardInterrupt:
        print_info("Shutting down gracefully...")
        imap.logout()
        print_success("Logged out. Bye!")

if __name__ == "__main__":
    main()