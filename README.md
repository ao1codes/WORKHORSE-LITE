# 📩 ao1codes' MailMind

**Email an AI. Get smart replies. No login needed.**

ao1codes is an email-based AI responder. Just send an email to `ao1codes.ai@gmail.com` and you'll get a clean, professional response powered by Google's Gemini AI — no web apps, no accounts, just email.

---

## ✨ Features

- 📥 Auto-checks Gmail inbox for new emails
- 🤖 AI-generated responses using Gemini 1.5 Flash
- 💬 Full HTML-formatted replies with original message included
- 📷 Skips image/file attachments and responds accordingly
- 🔁 Self-reconnecting IMAP loop with delay handling
- 🔐 Uses `.env` for secure credential loading
- 💤 Sleep cycles to avoid Gmail rate limits

---

## 📦 Installation

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
   GEMINI_API_KEY=your_gemini_api_key
   ```

---

## 🛠️ Running the Bot

```bash
python workhorse-lite.py
```

The bot will start watching your Gmail inbox and reply to new, plain-text emails automatically.

---

## 🚫 Limitations

- Attachments are ignored — users are notified not to send files.
- This is a personal-use tool; for large-scale deployment, consider API rate limits and auth security.

---

## 🌐 Live Demo

Want to try it? Just email:

```
ao1codes.ai@gmail.com
```

No signup. No dashboard. Just email an AI and get a reply.

---

## 📄 License

MIT License © 2025 ao1codes
