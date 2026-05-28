from fastapi import APIRouter,HTTPException,Depends,Form,File,UploadFile
from psycopg2.extras import RealDictCursor
from datetime import datetime
from auth_utils import get_current_user,admin_required
from db import get_conn
from logger import get_logger
from typing import List,Optional
import os
from uuid import uuid4
import re

router = APIRouter(prefix="/child_categories", tags=["child_categories"])

logger = get_logger(__name__)

# generate slug
def generate_slug(name: str):
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug

@router.post("/")
def create_child_categories(
    category_id : int = Form(...),
    sub_category_id: int = Form(...),
    name : str = Form(...),
    child_cat_image : List[UploadFile] = File(...),
    seo_title : Optional[str] = Form(None),
    seo_description : Optional[str] = Form(None),
    seo_keywords :Optional[str] = Form(None),
    description : Optional[str] = Form(None),
    status : int = Form(...),
    user = Depends(get_current_user)
):
    admin_required(user)
    conn=get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # generate slug
        slug = generate_slug(name)

        # check category exists
        cur.execute(
            "SELECT id FROM categories WHERE id=%s",
            (category_id,)
        )

        category = cur.fetchone()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        # check sub category exists
        cur.execute(
            "SELECT id FROM sub_categories WHERE id=%s",
            (sub_category_id,)
        )

        sub_category = cur.fetchone()

        if not sub_category:
            raise HTTPException(
                status_code=404,
                detail="Sub Category not found"
            )

        # create upload folder
        os.makedirs("uploads/child_categories", exist_ok=True)

        # upload image
        file = child_cat_image[0]

        filename = f"{uuid4()}_{file.filename}"
        file_path = f"uploads/child_categories/{filename}"

        with open(file_path, "wb") as f:
            f.write(file.file.read())

        image_url = f"/{file_path}"

        # insert data
        cur.execute(
            """
            INSERT INTO child_categories
            (
                category_id,
                sub_category_id,
                name,
                slug,
                child_cat_image,
                seo_title,
                seo_description,
                seo_keywords,
                description,
                status,
                created_at,
                updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
            """,
            (
                category_id,
                sub_category_id,
                name,
                slug,
                image_url,
                seo_title,
                seo_description,
                seo_keywords,
                description,
                status,
                datetime.utcnow(),
                datetime.utcnow()
            )
        )

        data = cur.fetchone()

        conn.commit()

        return {
            "status": "success",
            "message": "Child Category Created Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()
    
# get all child categories
@router.get("/")
def get_child_category(user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute(
            """
            SELECT 
                cc.*,
                c.name AS category_name,
                sc.name AS sub_category_name
            FROM child_categories cc
            LEFT JOIN categories c
                ON cc.category_id = c.id
            LEFT JOIN sub_categories sc
                ON cc.sub_category_id = sc.id
            ORDER BY cc.created_at DESC
            """
        )

        data = cur.fetchall()
        
        return{
            "status":"success",
            "data": data
        }
    finally:
        cur.close()
        conn.close()
        
# update child category
@router.patch("/{id}")
def update_child_category(
    id: int,
    category_id: Optional[int] = Form(None),
    sub_category_id: Optional[int] = Form(None),
    name: Optional[str] = Form(None),
    child_cat_image: List[UploadFile] = File(...),
    seo_title: Optional[str] = Form(None),
    seo_description: Optional[str] = Form(None),
    seo_keywords: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[int] = Form(None),
    user=Depends(get_current_user)
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        fields = []
        values = []

        # check category exists
        if category_id is not None:

            cur.execute(
                "SELECT id FROM categories WHERE id=%s",
                (category_id,)
            )

            category = cur.fetchone()

            if not category:
                raise HTTPException(
                    status_code=404,
                    detail="Category not found"
                )

            fields.append("category_id=%s")
            values.append(category_id)

        # check sub category exists
        if sub_category_id is not None:

            cur.execute(
                "SELECT id FROM sub_categories WHERE id=%s",
                (sub_category_id,)
            )

            sub_category = cur.fetchone()

            if not sub_category:
                raise HTTPException(
                    status_code=404,
                    detail="Sub Category not found"
                )

            fields.append("sub_category_id=%s")
            values.append(sub_category_id)

        # update name and slug
        if name is not None:

            slug = generate_slug(name)

            fields.append("name=%s")
            values.append(name)

            fields.append("slug=%s")
            values.append(slug)

        # update image
        if child_cat_image is not None:

            os.makedirs("uploads/child_categories", exist_ok=True)

            filename = f"{uuid4()}_{child_cat_image.filename}"

            file_path = f"uploads/child_categories/{filename}"

            with open(file_path, "wb") as f:
                f.write(child_cat_image.file.read())

            image_url = f"/{file_path}"

            fields.append("child_cat_image=%s")
            values.append(image_url)

        # update seo title
        if seo_title is not None:
            fields.append("seo_title=%s")
            values.append(seo_title)

        # update seo description
        if seo_description is not None:
            fields.append("seo_description=%s")
            values.append(seo_description)

        # update seo keywords
        if seo_keywords is not None:
            fields.append("seo_keywords=%s")
            values.append(seo_keywords)

        # update description
        if description is not None:
            fields.append("description=%s")
            values.append(description)

        # update status
        if status is not None:
            fields.append("status=%s")
            values.append(status)

        # updated time
        fields.append("updated_at=%s")
        values.append(datetime.utcnow())

        values.append(id)

        query = f"""
            UPDATE child_categories
            SET {', '.join(fields)}
            WHERE id=%s
            RETURNING *
        """

        cur.execute(query, tuple(values))

        data = cur.fetchone()

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Child Category not found"
            )

        conn.commit()

        return {
            "status": "success",
            "message": "Child Category Updated Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()
        
@router.delete("/{id}")
def delete_child_category(
    id: int,
    user=Depends(get_current_user)
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # check child category exists
        cur.execute(
            "SELECT * FROM child_categories WHERE id=%s",
            (id,)
        )

        child_category = cur.fetchone()

        if not child_category:
            raise HTTPException(
                status_code=404,
                detail="Child Category not found"
            )

        # delete image from folder
        if child_category["child_cat_image"]:

            image_path = child_category["child_cat_image"].lstrip("/")

            if os.path.exists(image_path):
                os.remove(image_path)

        # delete from database
        cur.execute(
            """
            DELETE FROM child_categories
            WHERE id=%s
            RETURNING *
            """,
            (id,)
        )

        data = cur.fetchone()

        conn.commit()

        return {
            "status": "success",
            "message": "Child Category Deleted Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()
        
# change status
@router.post("/change-status")
def change_status(
    id: int = Form(...),
    status: int = Form(...),
    user=Depends(get_current_user)
):
    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # check child category exists
        cur.execute(
            "SELECT * FROM child_categories WHERE id=%s",
            (id,)
        )

        child_category = cur.fetchone()

        if not child_category:
            raise HTTPException(
                status_code=404,
                detail="Child Category not found"
            )

        # update status
        cur.execute(
            """
            UPDATE child_categories
            SET status=%s,
                updated_at=%s
            WHERE id=%s
            RETURNING *
            """,
            (
                status,
                datetime.utcnow(),
                id
            )
        )

        data = cur.fetchone()

        conn.commit()

        return {
            "status": "success",
            "message": "Status Updated Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()