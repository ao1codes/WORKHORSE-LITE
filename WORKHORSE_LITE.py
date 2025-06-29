import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from google.generativeai import GenerativeModel, configure
from dotenv import load_dotenv
import os
import time
import html
import random
import textwrap

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

# Store conversation history and email counts per user
conversation_history = {}
user_email_counts = {}

def search_all_emails_from_sender(imap, sender_email):
    """Search through ALL emails (sent and received) to build complete conversation history"""
    all_messages = []
    
    # Search in INBOX for emails FROM the sender
    try:
        imap.select("inbox")
        status, inbox_messages = imap.search(None, f'FROM "{sender_email}"')
        if status == "OK" and inbox_messages[0]:
            inbox_nums = inbox_messages[0].split()
            if DEBUG:
                print_info(f"Found {len(inbox_nums)} emails in INBOX from {sender_email}")
            
            for num in inbox_nums:
                try:
                    status, data = imap.fetch(num, "(RFC822)")
                    if status == "OK":
                        msg = email.message_from_bytes(data[0][1])
                        body = extract_email_body(msg)
                        clean_msg = extract_clean_message(body)
                        if clean_msg.strip():
                            all_messages.append({
                                'type': 'user',
                                'message': clean_msg,
                                'date': msg.get('Date', ''),
                                'subject': msg.get('Subject', '')
                            })
                except:
                    continue
    except Exception as e:
        print_warning(f"Error searching inbox: {e}")
    
    # Search in SENT folder for emails TO the sender (our replies)
    try:
        sent_folders = ['"[Gmail]/Sent Mail"', 'INBOX.Sent', 'Sent', '"Sent Messages"']
        for folder in sent_folders:
            try:
                imap.select(folder)
                status, sent_messages = imap.search(None, f'TO "{sender_email}"')
                if status == "OK" and sent_messages[0]:
                    sent_nums = sent_messages[0].split()
                    if DEBUG:
                        print_info(f"Found {len(sent_nums)} emails in {folder} to {sender_email}")
                    
                    for num in sent_nums:
                        try:
                            status, data = imap.fetch(num, "(RFC822)")
                            if status == "OK":
                                msg = email.message_from_bytes(data[0][1])
                                body = extract_email_body(msg)
                                if 'ao1codes' not in body.lower() and 'ai assistant' not in body.lower():
                                    clean_msg = extract_clean_message(body)
                                    if clean_msg.strip():
                                        all_messages.append({
                                            'type': 'ai',
                                            'message': clean_msg,
                                            'date': msg.get('Date', ''),
                                            'subject': msg.get('Subject', '')
                                        })
                        except:
                            continue
                    break
            except:
                continue
    except Exception as e:
        print_warning(f"Error searching sent folders: {e}")
    
    all_messages.sort(key=lambda x: x['date'])
    
    return all_messages

def extract_email_body(msg):
    """Extract body text from email message"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in cdisp:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="ignore")
    return body

def build_conversation_from_email_history(sender_email, imap, current_message):
    """Build conversation history by searching through all emails from this sender"""
    if DEBUG:
        print_info(f"Building conversation history for {sender_email}...")
    
    all_messages = search_all_emails_from_sender(imap, sender_email)

    # Remove duplicates of current message
    all_messages = [msg for msg in all_messages if extract_clean_message(msg['message']) != extract_clean_message(current_message)]
    
    if not all_messages:
        print_info("No previous emails found")
        return 0
    
    user_email_count = len([msg for msg in all_messages if msg['type'] == 'user'])
    
    conversation_history[sender_email] = all_messages[-20:]
    user_email_counts[sender_email] = user_email_count
    
    if DEBUG:
        print_success(f"Found {user_email_count} previous emails from {sender_email}")
        print_success(f"Loaded {len(conversation_history[sender_email])} messages into context")
    
    return user_email_count

def extract_clean_message(body):
    lines = body.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        if (stripped.startswith('>') or 
            'wrote:' in stripped.lower() or
            'original message' in stripped.lower() or
            'ai assistant' in stripped.lower() or
            'ao1codes' in stripped.lower() or
            '<html>' in stripped.lower() or
            stripped.startswith('--') or
            'sent from my' in stripped.lower()):
            break
        clean_lines.append(line)
    
    clean_message = '\n'.join(clean_lines).strip()
    return clean_message if clean_message else body.strip()

def update_conversation_history(sender_email, user_message, ai_response):
    if sender_email not in conversation_history:
        conversation_history[sender_email] = []
    if sender_email not in user_email_counts:
        user_email_counts[sender_email] = 0
        
    conversation_history[sender_email].append({
        'type': 'user', 
        'message': user_message, 
        'date': time.strftime('%a, %d %b %Y %H:%M:%S'),
        'email_number': user_email_counts[sender_email]
    })
    conversation_history[sender_email].append({
        'type': 'ai', 
        'message': ai_response, 
        'date': time.strftime('%a, %d %b %Y %H:%M:%S')
    })
    
    if len(conversation_history[sender_email]) > 30:
        conversation_history[sender_email] = conversation_history[sender_email][-30:]

def build_conversation_context(sender_email, current_message):
    if sender_email not in conversation_history or not conversation_history[sender_email]:
        return current_message
    
    context_parts = []
    
    history = conversation_history[sender_email][-10:]
    for entry in history:
        role = "USER" if entry['type'] == 'user' else "AI_ASSISTANT"
        context_parts.append(f"{role}: {entry['message']}")
    
    context_parts.append(f"USER: {current_message}")
    
    return "\n\n".join(context_parts)

def get_user_email_count(sender_email):
    return user_email_counts.get(sender_email, 0)

def create_html_body(latest_message, ai_response, email_count):
    def safe_html(text): return html.escape(text).replace('\n', '<br>')
    
    email_info = f" • Email #{email_count} from you"
    
    return f"""<html><head><style>
    body {{ font-family: Arial, sans-serif; background-color: #f9f9f9; margin: 0; padding: 20px; }}
    .container {{ max-width: 700px; margin: auto; background: white; padding: 20px;
        border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #ddd; }}
    h2 {{ color: #333; font-size: 20px; border-bottom: 2px solid #007bff; padding-bottom: 8px; }}
    p {{ font-size: 15px; color: #555; line-height: 1.5; }}
    .response-box {{ background-color: #f0f4ff; border: 1px solid #b3c7ff; padding: 15px;
        border-radius: 6px; color: #222; font-size: 15px; white-space: pre-wrap; margin-top: 10px; }}
    .footer {{ margin-top: 30px; font-size: 13px; color: #888; text-align: center; font-style: italic; }}
    </style></head><body>
    <div class="container">
        <h2>You asked:</h2><p>{safe_html(latest_message)}</p>
        <h2>AI Response:</h2><div class="response-box">{safe_html(ai_response)}</div>
        <div class="footer">AI Assistant • ao1codes{email_info}</div>
    </div></body></html>"""

def get_random_model():
    keys = os.getenv("GEMINI_API_KEYS", "").split(",")
    keys = [k.strip() for k in keys if k.strip()]
    if not keys:
        raise ValueError("No API keys found in GEMINI_API_KEYS")
    
    random_key = random.choice(keys)
    if DEBUG:
        print_info(f"Using API Key: {random_key[:10]}...")
    
    configure(api_key=random_key)
    return GenerativeModel("gemini-1.5-flash")

def main():
    print_header("ao1codes Email Bot v2.0 - Email History Search Mode")
    load_dotenv()
    
    email_user = os.getenv("EMAIL_ADDRESS")
    email_pass = os.getenv("EMAIL_PASSWORD")

    print_info("Connecting to Gmail IMAP...")
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(email_user, email_pass)
        print_success("Logged in to Gmail!")
    except Exception as e:
        print_error(f"Login failed: {e}")
        return

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
                try: 
                    imap.logout()
                except: 
                    pass
                imap = imaplib.IMAP4_SSL("imap.gmail.com")
                imap.login(email_user, email_pass)
                continue

            email_nums = messages[0].split()
            if not email_nums:
                if DEBUG: 
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
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition", ""))
                        if ctype.startswith("image/") or "attachment" in cdisp:
                            has_attachment = True
                        elif ctype == "text/plain" and "attachment" not in cdisp:
                            payload = part.get_payload(decode=True)
                            if payload: 
                                body = payload.decode(errors="ignore")
                else:
                    payload = msg.get_payload(decode=True)
                    if payload: 
                        body = payload.decode(errors="ignore")

                clean_message = extract_clean_message(body)
                email_count = build_conversation_from_email_history(sender_email, imap, clean_message)
                # If no previous emails found, start at 1, else increment
                email_count = email_count if email_count > 0 else 0
                email_count += 1

                conversation_context = build_conversation_context(sender_email, clean_message)

                previous_count = len([msg for msg in conversation_history.get(sender_email, []) if msg['type'] == 'user'])
                if previous_count > 0:
                    print_info(f"📧 Continuing conversation with {sender_email} (Email #{email_count}, {previous_count} previous emails found)")
                    prompt_for_ai = textwrap.dedent(f"""\
                        You're an AI assistant replying casually and directly to this user.
                        
                        FULL CONVERSATION HISTORY:
                        {conversation_context}

                        GUIDELINES:
                        - This is email #{email_count} from the user
                        - You have {previous_count} previous emails in context
                        - Respond casually and directly
                        - Do NOT include greetings like "Dear..." or mention the email subject
                        - Answer their question or request head-on, no stalling or overformal tone
                        - If they gave a task or command, just do it

                        Now respond to their latest message:""")
                else:
                    print_info(f"📧 Starting new conversation with {sender_email} (Email #1)")
                    prompt_for_ai = clean_message.strip() or "(No message content provided)"

                first_line = clean_message.splitlines()[0].strip() if clean_message.strip() else "Your message"
                reply_subject = f"Re: {first_line[:50]}{'...' if len(first_line) > 50 else ''}"

                if has_attachment:
                    print_warning(f"{sender_email} sent an attachment. Providing standard response.")
                    response = "Thanks for reaching out! I currently don't process emails with attachments. Please resend your message without files, and I'll be happy to help!"
                else:
                    print_info(f"Generating AI response for: {first_line[:60]}...")
                    try:
                        model = get_random_model()
                        response = model.generate_content(prompt_for_ai).text.strip()
                        print_success("Generated AI response!")
                    except Exception as e:
                        print_error(f"AI generation failed: {e}")
                        response = "Sorry, I'm having trouble generating a response right now. Please try again in a moment."

                if not has_attachment:
                    update_conversation_history(sender_email, clean_message, response)

                html_body = create_html_body(clean_message, response, email_count)
                reply_msg = MIMEText(html_body, "html")
                reply_msg["Subject"] = reply_subject
                reply_msg["From"] = email_user
                reply_msg["To"] = sender_email

                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                        smtp.starttls()
                        smtp.login(email_user, email_pass)
                        smtp.send_message(reply_msg)
                    
                    print_success(f"Replied to {sender_email} (Email #{email_count})")
                    imap.select("inbox")
                    imap.store(num, '+FLAGS', '\\Seen')
                except Exception as e:
                    print_error(f"Failed to send reply: {e}")

                time.sleep(1)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print_info("Shutting down gracefully...")
        try:
            imap.logout()
        except:
            pass
        print_success("Logged out. Goodbye!")

if __name__ == "__main__":
    main()