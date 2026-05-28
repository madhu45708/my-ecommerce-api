from fastapi import APIRouter, HTTPException, Form, File, UploadFile,Depends
from auth_utils import get_current_user,admin_required
from psycopg2.extras import RealDictCursor
from datetime import datetime
from db import get_conn
from logger import get_logger
from typing import List
import os
from uuid import uuid4

router = APIRouter(prefix="/banner", tags=["Banner"])

logger = get_logger(__name__)


# get banners
@router.get("/")
def get_banners(user=Depends(get_current_user)):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT *
            FROM banners
            ORDER BY created_at DESC
        """)

        return {
            "status": True,
            "data": cur.fetchall()
        }

    finally:
        cur.close()
        conn.close()


# create banners
@router.post("/")
def create_banner(
    banner: List[UploadFile] = File(...),
    banner_title: str = Form(...),
    banner_content: str = Form(None),
    starting_price: str = Form(None),
    status: int = Form(1),
    user=Depends(get_current_user)
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # create upload folder
        upload_dir = "uploads/banners"
        os.makedirs(upload_dir, exist_ok=True)

        uploaded_files = []

        # save all uploaded images
        for file in banner:

            file_ext = file.filename.split(".")[-1]
            file_name = f"{uuid4()}.{file_ext}"

            file_path = os.path.join(upload_dir, file_name)

            with open(file_path, "wb") as buffer:
                buffer.write(file.file.read())

            uploaded_files.append(file_path)

        # convert list to comma separated string
        banner_paths = ",".join(uploaded_files)
        
        cur.execute(
            """
            INSERT INTO banners (
                banner,
                banner_title,
                banner_content,
                starting_price,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """,
            (
                file_path,
                banner_title,
                banner_content,
                starting_price,
                status,
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )

        conn.commit()
        return {"status": True, "message": "Banner created", "data": cur.fetchone()}
    finally:
        conn.close()
        cur.close()


# update banners
@router.put("/{banner_id}")
def update_banner(
    banner_id: int,
    banner: str = Form(None),
    banner_title: str = Form(None),
    banner_content: str = Form(None),
    starting_price: str = Form(None),
    status: int = Form(None),
    user=Depends(get_current_user)
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("SELECT * FROM banners WHERE id=%s", (banner_id,))
        existing = cur.fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Banner not found")

        fields = []
        values = []

        if banner:
            fields.append("banner=%s")
            values.append(banner)

        if banner_title:
            fields.append("banner_title=%s")
            values.append(banner_title)

        if banner_content:
            fields.append("banner_content=%s")
            values.append(banner_content)

        if starting_price:
            fields.append("starting_price=%s")
            values.append(starting_price)

        if status is not None:
            fields.append("status=%s")
            values.append(status)

        fields.append("updated_at=%s")
        values.append(datetime.utcnow())

        values.append(banner_id)

        query = f"""
            UPDATE banners
            SET {", ".join(fields)}
            WHERE id=%s
            RETURNING *
        """

        cur.execute(query, values)
        conn.commit()

        return {"status": True, "message": "Banner updated", "data": cur.fetchone()}

    finally:
        cur.close()
        conn.close()


# delete banner
@router.delete("/{banner_id}")
def delete_banner(banner_id: int,user=Depends(get_current_user)):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM banners WHERE id=%s", (banner_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Banner not found")

        cur.execute("DELETE FROM banners WHERE id=%s", (banner_id,))
        conn.commit()

        return {"status": True, "message": "Banner deleted"}

    finally:
        cur.close()
        conn.close()
