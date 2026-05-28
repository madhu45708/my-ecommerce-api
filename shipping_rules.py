from fastapi import APIRouter, HTTPException, Form, Depends
from auth_utils import get_current_user, admin_required
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional
from db import get_conn

# Shipping rule router
router = APIRouter(prefix="/shipping-rule", tags=["Shipping Rule"])


# getting shipping rules
@router.get("/")
def get_shipping_rules(user=Depends(get_current_user)):
    admin_required(user)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Fetch all shipping rules
        cur.execute("SELECT * FROM shipping_rules ORDER BY created_at DESC")
        data = cur.fetchall()
        return {"status": "success", "data": data}

    finally:
        cur.close()
        conn.close()


# create shipping rules
@router.post("/")
def create_shipping_rule(
    name: str = Form(...),
    type: str = Form(...),
    min_cost: Optional[int] = Form(None),
    cost: int = Form(...),
    status: int = Form(...),
    user=Depends(get_current_user),
):
    admin_required(user)
    if type == "paid":
        type ="free"
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Insert new shipping rule
        cur.execute(
            """
            INSERT INTO shipping_rules (name, type, min_cost, cost, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """,
            (name, type, min_cost, cost, status, datetime.utcnow(), datetime.utcnow()),
        )

        data = cur.fetchone()
        conn.commit()

        return {"status": "success", "message": "Created Successfully", "data": data}

    finally:
        cur.close()
        conn.close()


# update shipping rule
@router.patch("/{id}")
def update_shipping_rule(
    id: int,
    name: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    min_cost: Optional[int] = Form(None),
    cost: Optional[int] = Form(None),
    status: Optional[int] = Form(None),
    user=Depends(get_current_user),
):
    admin_required(user)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        fields = []
        values = []
        # Dynamically build update query
        if name is not None:
            fields.append("name=%s")
            values.append(name)

        if type is not None:
            fields.append("type=%s")
            values.append(type)

        if min_cost is not None:
            fields.append("min_cost=%s")
            values.append(min_cost)

        if cost is not None:
            fields.append("cost=%s")
            values.append(cost)

        if status is not None:
            fields.append("status=%s")
            values.append(status)

        # Always update timestamp
        fields.append("updated_at=%s")
        values.append(datetime.utcnow())

        values.append(id)

        query = f"""
            UPDATE shipping_rules
            SET {', '.join(fields)}
            WHERE id=%s
            RETURNING *
        """

        cur.execute(query, tuple(values))

        data = cur.fetchone()

        if not data:
            raise HTTPException(404, "Shipping Rule not found")

        conn.commit()

        return {"status": "success", "message": "Updated Successfully", "data": data}

    finally:
        cur.close()
        conn.close()


# delete shipping rules
@router.delete("/{id}")
def delete_shipping_rule(id: int, user=Depends(get_current_user)):
    admin_required(user)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Delete rule
        cur.execute(
            """ 
                    DELETE FROM shipping_rules WHERE id=%s RETURNING id """,
            (id,),
        )
        data = cur.fetchone()
        if not data:
            raise HTTPException(404, "Shipping Rule not found")
        conn.commit()
        return {"status": "success", "message": "Deleted Successfully"}
    finally:
        cur.close()
        conn.close()


# change status
@router.post("/change-status")
def change_status(
    id: int = Form(...), status: int = Form(...), user=Depends(get_current_user)
):
    admin_required(user)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Update only status field
        cur.execute(
            """
            UPDATE shipping_rules
            SET status=%s, updated_at=%s
            WHERE id=%s
            RETURNING *
        """,
            (status, datetime.utcnow(), id),
        )

        data = cur.fetchone()

        if not data:
            raise HTTPException(404, "Shipping Rule not found")

        conn.commit()

        return {"status": "success", "message": "Status updated"}

    finally:
        cur.close()
        conn.close()
