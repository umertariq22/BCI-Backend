from fastapi_mail import FastMail, MessageSchema,ConnectionConfig
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL: str = os.environ.get("MAIL_EMAIL")
PASSWORD: str = os.environ.get("MAIL_PASSWORD")

connection_conf = ConnectionConfig(
    MAIL_USERNAME=EMAIL,
    MAIL_PASSWORD=PASSWORD,
    MAIL_FROM=EMAIL,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_email(email: str, subject: str, message: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=message,
        subtype="html"
    )

    fm = FastMail(connection_conf)
    
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    


    
    