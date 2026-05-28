from fastapi import APIRouter, Depends
from auth_utils import get_current_user, admin_required
from psycopg2.extras import RealDictCursor
from sqlalchemy.orm import Session
from db import get_conn
from pydantic import BaseModel

router = APIRouter(prefix="/customer-management", tags=["Customer Management"])


class Customer(BaseModel):
    id:int
    is_active: bool


# get api
@router.get("/")
def get_customer_management(user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            select username,email,phone_number,is_active 
            from users
            where user_role = 'user' 
            order by created_at desc 
            """
        )
        data = cur.fetchall()

        return {"status": "success", "data": data}
    finally:
        conn.close()
        cur.close()


@router.post("/customer-status")
def update_customer_status(
    payload: Customer,
    user=Depends(get_current_user)
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            UPDATE users
            SET is_active = %s
            WHERE id = %s
            RETURNING id, is_active
            """,
            (payload.is_active, payload.id)
        )

        updated_user = cur.fetchone()
        conn.commit()

        return {
            "status": True,
            "message": "User status updated successfully",
            "data": updated_user
        }
    except Exception as e:
        conn.rollback()
        return {
            "status": False,
            "message": str(e),
            "data": None
        }


    finally:
        cur.close()
        conn.close()