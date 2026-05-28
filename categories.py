from fastapi import APIRouter, HTTPException, Form, Depends, File, UploadFile
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from datetime import datetime
from db import get_conn
from auth_utils import get_current_user, admin_required
import re

router = APIRouter(prefix="/categories", tags=["categories"])


def generate_slug(name):
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


# get all categories
@router.get("/")
def get_categories(user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            select * from categories order by created_at desc """)
        data = cur.fetchall()

        return {"status": "success", "data": data}
    finally:
        conn.close()
        cur.close()


# create categories
@router.post("/")
def create_categories(
    name: str = Form(...),
    cat_image: List[UploadFile] = File(...),
    seo_title: Optional[str] = File(None),
    seo_description: Optional[str] = Form(None),
    seo_keywords: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: int = Form(...),
    user=Depends(get_current_user),
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        slug = generate_slug(name)

        cur.execute("select id from categories where slug=%s", (slug,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="slug already exists")

        cur.execute(
            """
                    insert into categories
                    (
                        name,
                        slug,
                        cat_iamge,
                        seo_title,
                        seo_description,
                        seo_keywords,
                        description,
                        status,
                        created_at,
                        updated_at
                        )
                        values
                        (%s,%s,%s,%s,%s,%s,%s.%s,%s,%s)
                        returning *
                        """,
            (
                name,
                slug,
                seo_title,
                seo_description,
                seo_keywords,
                description,
                status,
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )
        data = cur.fetchone()
        conn.commit()
        return {
            "success": "success",
            "message": "categories created successfully",
            "data": data,
        }
    finally:
        cur.close()
        conn.close()


# update categories
@router.put("/")
def update_categories(
    id: int,
    name: Optional[str] = Form(None),
    cat_image: Optional[str] = Form(None),
    seo_title: Optional[str] = Form(None),
    seo_description: Optional[str] = Form(None),
    seo_keywords: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[int] = Form(None),
    user=Depends(get_current_user),
):
    admin_required(user)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        fields = []
        values = []

        # update name and auto update slug
        if name is not None:

            slug = generate_slug(name)

            fields.append("name=%s")
            values.append(name)

            fields.append("slug=%s")
            values.append(slug)

        if cat_image is not None:
            fields.append("cat_image=%s")
            values.append(cat_image)

        if seo_title is not None:
            fields.append("seo_title=%s")
            values.append(seo_title)

        if seo_description is not None:
            fields.append("seo_description=%s")
            values.append(seo_description)

        if seo_keywords is not None:
            fields.append("seo_keywords=%s")
            values.append(seo_keywords)

        if description is not None:
            fields.append("description=%s")
            values.append(description)

        if status is not None:
            fields.append("status=%s")
            values.append(status)

        # updated time
        fields.append("updated_at=%s")
        values.append(datetime.utcnow())

        values.append(id)

        query = f"""
            UPDATE categories
            SET {', '.join(fields)}
            WHERE id=%s
            RETURNING *
        """

        cur.execute(query, tuple(values))

        data = cur.fetchone()

        if not data:
            raise HTTPException(status_code=404, detail="Category not found")

        conn.commit()

        return {
            "status": "success",
            "message": "Category Updated Successfully",
            "data": data,
        }

    finally:
        cur.close()
        conn.close()


# delete categories
@router.delete("/{id}")
def delete_category(id: int, user=Depends(get_current_user)):

    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # delete category
        cur.execute(
            """
            DELETE FROM categories
            WHERE id=%s
            RETURNING *
            """,
            (id,),
        )

        data = cur.fetchone()

        # check category exists or not
        if not data:
            raise HTTPException(status_code=404, detail="Category not found")

        conn.commit()

        return {
            "status": "success",
            "message": "Category Deleted Successfully",
            "data": data,
        }

    finally:
        cur.close()
        conn.close()


# Change Category Status
@router.post("/change-status")
def change_status(
    id: int = Form(...), status: int = Form(...), user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        cur.execute(
            """
            UPDATE categories
            SET status=%s,
                updated_at=%s
            WHERE id=%s
            RETURNING *
        """,
            (status, datetime.utcnow(), id),
        )

        data = cur.fetchone()

        if not data:
            raise HTTPException(status_code=404, detail="Category not found")

        conn.commit()

        return {
            "status": "success",
            "message": "Category Status Updated Successfully",
            "data": data,
        }

    finally:
        cur.close()
        conn.close()
