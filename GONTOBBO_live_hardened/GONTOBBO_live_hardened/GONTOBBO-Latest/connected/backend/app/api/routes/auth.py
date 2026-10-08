import os
import asyncio
import random
import smtplib
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.exceptions import UserAlreadyExists
from pydantic import BaseModel, EmailStr

from app.db import User
from app.users import UserCreate, UserManager, get_jwt_strategy, get_user_manager

router = APIRouter(prefix="/api", tags=["auth"])

otp_store = {}

load_dotenv(override=True)

# SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")  # Replace with your Gmail address
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")  # Replace with your 16-character Gmail App Password


class SendOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


def send_email_sync(to_email: str, otp: str):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "Your Verification Code - Gontobbo"

    body = f"Hello,\n\nYour OTP code for signing in is: {otp}\n\nThis code will expire in 5 minutes."
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)


@router.post("/send-otp")
async def send_otp(payload: SendOTPRequest):
    otp = f"{random.randint(100000, 999999)}"
    otp_store[payload.email] = {
        "otp": otp,
        "expires_at": time.time() + 300,
    }

    try:
        # Send email asynchronously to prevent blocking FastAPI
        await asyncio.to_thread(send_email_sync, payload.email, otp)
    except Exception as e:
        print(f"Email delivery error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email.",
        )

    return {"status": "success", "message": f"OTP sent to {payload.email}"}


@router.post("/verify-otp")
async def verify_otp(
    payload: VerifyOTPRequest,
    user_manager: UserManager = Depends(get_user_manager),
    jwt_strategy=Depends(get_jwt_strategy),
):
    record = otp_store.get(payload.email)

    if not record or record["expires_at"] < time.time():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired or was not requested.",
        )

    if record["otp"] != payload.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code.",
        )

    del otp_store[payload.email]

    try:
        user = await user_manager.get_by_email(payload.email)
    except Exception:
        user = None

    if not user:
        random_password = uuid.uuid4().hex
        user_create = UserCreate(email=payload.email, password=random_password)
        try:
            user = await user_manager.create(user_create)
        except UserAlreadyExists:
            user = await user_manager.get_by_email(payload.email)

    token = await jwt_strategy.write_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
    }