# ao1codes Email AI Reply Bot

A Python script that monitors a Gmail inbox, reads incoming emails, sends the email body to an AI language model (Google Gemini API), and replies with a smart, formatted AI-generated response — no login needed beyond email credentials.

---

## Features

- Connects securely to Gmail via IMAP to check new unread emails  
- Reads plain text emails (ignores emails with attachments)  
- Sends email content as prompt to Google Gemini AI model for response  
- Sends back a nicely formatted HTML reply email with the AI's answer  
- Runs continuously, checking inbox every 10 seconds  
- Uses environment variables for credentials and API keys  
- Pretty colored terminal logs for easy debugging  

---

## Requirements

- Python 3.7+  
- Google Gemini API key  
- Gmail account with app password (if 2FA enabled)  
- `google-generativeai` Python package  
- `python-dotenv` package  

---
