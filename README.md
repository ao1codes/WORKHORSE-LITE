# 📩 ao1codes' MailMind

**Email an AI. Get smart replies. No login needed.**

An AI email responder that replies to Gmail messages using Google Gemini. Works without a login or app—just send an email to get a response.

---

## Features

-  Auto-checks Gmail inbox for new emails
-  AI-generated responses using Gemini 1.5 Flash
-  Full HTML-formatted replies with original message included
-  Skips image/file attachments and responds accordingly
-  Self-reconnecting IMAP loop with delay handling
-  Uses `.env` for secure credential loading
-  Sleep cycles to avoid Gmail rate limits
-  Supports full conversation history across all emails
---

## Installation

1. Clone this repository  
   ```bash
   git clone https://github.com/ao1codes/workhorse-lite
   cd workhorse-lite
   ```

2. Install dependencies  
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file  
   ```
   EMAIL_ADDRESS=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   GEMINI_API_KEYS=your_gemini_api_keys
   ```

---

## Running the Bot

```bash
python workhorse-lite.py
```

The bot will start watching your Gmail inbox and reply to new, plain-text emails automatically.

---

## Limitations

- Attachments are ignored — users are notified not to send files.
- This is a personal-use tool; for large-scale deployment, consider API rate limits and auth security.

---

## Live Demo

Want to try it? Just email:

```
ao1codes.ai@gmail.com
```

No signup. No dashboard. Just email an AI and get a reply.

---
