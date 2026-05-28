# importing packages
import re
import bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import jwt
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from logger import get_logger
from db import get_conn
import random
import smtplib
from email.mime.text import MIMEText
from auth_utils import get_current_user
from db import TIMEZONE
from zoneinfo import ZoneInfo

load_dotenv()  # .env file

router = APIRouter(prefix="/auth", tags=["Auth"])  # App Router
logger = get_logger(__name__)


# Secret key used to encode and decode JWT token
SECRET_KEY = os.getenv("SECRET_KEY") or "mysecret123"

# JWT encryption algorithm
ALGORITHM = os.getenv("ALGORITHM") or "HS256"

# Token expiry time in minutes
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def get_current_time():
    return datetime.now(
        ZoneInfo(TIMEZONE)
    )


# Function to send OTP email
def send_email_otp(to_email, otp):
    sender_email = "madhu45708@gmail.com"  # sender mail
    sender_password = "mshefemkjfdekcqy"  # gmail app password

    msg = MIMEText(f"Your OTP is: {otp}")
    msg["Subject"] = "Your OTP Code"
    msg["From"] = sender_email  # sender email
    msg["To"] = to_email  # receiver eamil

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)  # Connect to Gmail SMTP server
        server.starttls()  # Start TLS security
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print("Email failed:", str(e))


class RegisterRequest(BaseModel):
    username: str
    email: str
    phone_number: str
    password: str
    confirm_password: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str
    confirm_password: str


class ChangePasswordRequest(BaseModel):
    email: str
    old_password: str
    new_password: str
    confirm_password: str


# Regiter API
@router.post("/register")
# function for user regidteration
def register(data: RegisterRequest):
    logger.info(f"Register attempt: {data.email}")

    # Check password and confirm password match
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Validate email format
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", data.email):
        raise HTTPException(status_code=400, detail="Invalid email")

    password = data.password
    # Validate for Password
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter",
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter",
        )

    if not re.search(r"[0-9]", password):
        raise HTTPException(
            status_code=400, detail="Password must contain at least one number"
        )

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character",
        )

    # validate for phone_no
    if not data.phone_number.isdigit() or len(data.phone_number) != 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    # Database connection
    conn = get_conn()
    # cursor in dict form
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check user already exists
        cur.execute("SELECT id, is_active FROM users WHERE email=%s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        now = get_current_time() # Current UTC time
        expiry = now + timedelta(minutes=10)  # OTP expiry time

        # Hash password using bcrypt
        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

        # Insert user data into database
        cur.execute(
            """
    INSERT INTO users (
        username, email, phone_number, password,
        otp, otp_sent_at, otp_expired_at,
        no_of_otps, is_active,
        created_at, updated_at
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""",
            (
                data.username,
                data.email,
                data.phone_number,
                hashed,
                otp,
                now,
                expiry,
                1,
                False,
                now,
                now,
            ),
        )

        conn.commit()  # save changes
        send_email_otp(data.email, otp)  # send otp

        return {"message": "OTP sent to email"}  # response

    finally:
        cur.close()  # close cursor
        conn.close()  # close database connection


# verify otp API
@router.post("/verify-otp")
# Function to verify user OTP
def verify_otp(data: VerifyOtpRequest):
    # databse connection
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)  # Cursor in dictionary format

    try:
        # Get user by email
        cur.execute("SELECT * FROM users WHERE email=%s", (data.email,))
        user = cur.fetchone()
        # Check user exists or not
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # Check account already verified
        if user["is_active"]:
            raise HTTPException(status_code=400, detail="Already verified")
        # Check OTP expiry
        if get_current_time() > user["otp_expired_at"]:
            raise HTTPException(status_code=400, detail="OTP expired")
        # Check OTP is correct or not
        if user["otp"] != data.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        # Update user as verified
        cur.execute(
            """
            UPDATE users
            SET is_active=TRUE,
                otp=NULL,
                otp_sent_at=NULL,
                otp_expired_at=NULL
            WHERE id=%s
        """,
            (user["id"],),
        )

        conn.commit()  # save changes
        return {"message": "Account verified"}  # response

    finally:
        cur.close()  # close cursor
        conn.close()  # close database connection


# login api
@router.post("/login")
# function for user login
def login(data: LoginRequest):
    logger.info(f"Login attempt: {data.email}")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Get user by email
        cur.execute("SELECT * FROM users WHERE email=%s", (data.email,))
        user = cur.fetchone()
        # Check user exists or not
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check account is verified or not
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Account not verified")
        # Verify password using bcrypt
        if not bcrypt.checkpw(data.password.encode(), user["password"].encode()):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Generate JWT access token
        token = jwt.encode(
            {
                "user_id": user["id"],  # Store user id in token
                "role": user["user_role"],
                "exp": get_current_time()
                + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            },
            SECRET_KEY,  # Secret key for token encryption
            algorithm=ALGORITHM,  # JWT encryption algorithm
        )

        return {"access_token": token, "token_type": "Bearer"}

    finally:
        cur.close()
        conn.close()


# forget password api
@router.post("/forgot-password")
# function for forgetpassword
def forgot_password(data: ForgotPasswordRequest):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Get user by email
        cur.execute("SELECT * FROM users WHERE email=%s", (data.email,))
        user = cur.fetchone()
        # Check user exists or not
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
        now = get_current_time()# Current UTC time
        expiry = now + timedelta(minutes=10)  # OTP expiry time

        # Update OTP details in database
        cur.execute(
            """
            UPDATE users
            SET otp=%s, otp_sent_at=%s, otp_expired_at=%s
            WHERE id=%s
        """,
            (otp, now, expiry, user["id"]),
        )

        conn.commit()
        send_email_otp(data.email, otp)

        return {"message": "OTP sent"}

    finally:
        cur.close()
        conn.close()


# reset password api
@router.post("/reset-password")
# function for resetpassword
def reset_password(data: ResetPasswordRequest):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check new password and confirm password match
        if data.new_password != data.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        # Get user by email
        cur.execute("SELECT * FROM users WHERE email=%s", (data.email,))
        user = cur.fetchone()
        # Check user exists or not
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # Verify OTP
        if user["otp"] != data.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        # Check OTP expiry
        if get_current_time() > user["otp_expired_at"]:
            raise HTTPException(status_code=400, detail="OTP expired")
        # Hash new password using bcrypt
        hashed = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()

        # Update new password and clear OTP details
        cur.execute(
            """
            UPDATE users
            SET password=%s, otp=NULL, otp_sent_at=NULL, otp_expired_at=NULL
            WHERE id=%s
        """,
            (hashed, user["id"]),
        )

        conn.commit()
        return {"message": "Password reset successful"}

    finally:
        cur.close()
        conn.close()


# change password api
@router.post("/change-password")
# function for change password
def change_password(
    data: ChangePasswordRequest, current_user: dict = Depends(get_current_user)
):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check new password and confirm password match
        if data.new_password != data.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        # Check password minimum length
        if len(data.new_password) < 8:
            raise HTTPException(
                status_code=400, detail="Password must be at least 8 characters"
            )
        # Get current logged-in user
        cur.execute("SELECT * FROM users WHERE id=%s", (current_user["id"],))
        user = cur.fetchone()
        # Check user exists or not
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # Verify old password
        if not bcrypt.checkpw(
            data.old_password.encode("utf-8"), user["password"].encode("utf-8")
        ):
            raise HTTPException(status_code=401, detail="Old password incorrect")
        # Check new password is different from old password
        if bcrypt.checkpw(
            data.new_password.encode("utf-8"), user["password"].encode("utf-8")
        ):
            raise HTTPException(
                status_code=400, detail="New password must be different"
            )
        # Hash new password using bcrypt
        hashed = bcrypt.hashpw(
            data.new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode()
        # Update new password in database
        cur.execute(
            """
            UPDATE users
            SET password=%s, updated_at=%s
            WHERE id=%s
        """,
            (hashed, get_current_time(), user["id"]),
        )

        conn.commit()

        return {"message": "Password changed successfully"}

    finally:
        cur.close()
        conn.close()


# logout API
@router.post("/logout")
# function for user logout
def logout(current_user: dict = Depends(get_current_user)):
    return {"status": "success", "message": "Logged out successfully"}
