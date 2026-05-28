from fastapi import APIRouter, HTTPException, Depends
from db import get_conn
from auth_utils import get_current_user, admin_required
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
from datetime import datetime
import pytz

router = APIRouter(prefix="/contact", tags=["Contact"])

kolkata_tz = pytz.timezone("Asia/Kolkata")



class ContantMessage(BaseModel):
    name: str
    email: str
    subject: str
    message: str


# create api
@router.post("/")
def send_contact_message(data: ContantMessage):

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        current_time = datetime.now(kolkata_tz)
        cur.execute(
            """
                insert into user_contact_message_details
                (name,email,subject,message,created_at,updated_at)
                values(%s,%s,%s,%s,%s,%s)
                returning *
                """,
            (data.name, data.email, data.subject, data.message,current_time,current_time),
        )
        result = cur.fetchone()
        conn.commit()

        return {
            "status": True,
            "message": "Message sent successfully",
            "id": result["id"],
        }

    finally:
        cur.close()
        conn.close()


# get api
@router.get("/")
def get_contact_messages(user=Depends(get_current_user)):

    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT id, name, email, subject, message, created_at,updated_at
            FROM user_contact_message_details
            ORDER BY created_at DESC
            """)

        data = cur.fetchall()

        return {"status": True, "data": data}
    finally:
        cur.close()
        conn.close()
