import os
from email.mime.text import MIMEText
from smtplib import SMTP

from pydantic import EmailStr


async def  send_reset_email(to_email: EmailStr, reset_link: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    subject = "Reset your password"
    body = f"""
    Hi there,
    Click the link below to reset your password:
    {reset_link}

    This link will expire in 15 minutes.
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    with SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
