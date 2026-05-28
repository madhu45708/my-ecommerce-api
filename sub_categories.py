from fastapi import APIRouter,HTTPException,File,UploadFile,Depends,Form
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional,List
from db import get_conn
from auth_utils import get_current_user,admin_required
import re

router = APIRouter(
    prefix="/sub-categories",
    tags=["Sub Categories"]
)

# generate slug automatically
def generate_slug(name: str):
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug

@router.post("/")
def create_sub_category(
    category_id: int = Form(...),
    name: str = Form(...),
    sub_cat_image:list[UploadFile]=File(...),
    seo_title: Optional[str] = Form(None),
    seo_description: Optional[str] = Form(None),
    seo_keywords: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: int = Form(...),
    user=Depends(get_current_user)
):
    admin_required(user)
    conn =get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        slug = generate_slug(name)
        
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
        cur.execute(
            """ insert into sub_categories
            INSERT INTO sub_categories
            (
                category_id,
                name,
                slug,
                sub_cat_image,
                seo_title,
                seo_description,
                seo_keywords,
                description,
                status,
                created_at,
                updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
            """,
            (
                category_id,
                name,
                slug,
                sub_cat_image,
                seo_title,
                seo_description,
                seo_keywords,
                description,
                status,
                datetime.utcnow(),
                datetime.utcnow()
            ))
        data = cur.fetchone()

        conn.commit()

        return {
            "status": "success",
            "message": "Sub Category Created Successfully",
            "data": data
        }
    finally:
        conn.close()
        cur.close()
        
# get all sub categories
@router.get("/")
def get_sub_categories(user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    

    try:

        cur.execute("""
            SELECT 
            sc.*,
            c.name AS category_name
            FROM sub_categories sc
            LEFT JOIN categories c
            ON sc.category_id = c.id
            ORDER BY sc.created_at DESC
        """)

        data = cur.fetchall()

        return {
            "status": "success",
            "data": data
        }

    finally:
        cur.close()
        conn.close()

# update sub category
@router.put("/{id}")
def update_sub_category(
    id: int,
    category_id: Optional[int] = Form(None),
    name: Optional[str] = Form(None),
    sub_cat_image: List[UploadFile] = File(...),
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

        if name is not None:

            slug = generate_slug(name)

            fields.append("name=%s")
            values.append(name)

            fields.append("slug=%s")
            values.append(slug)

        if sub_cat_image is not None:
            fields.append("sub_cat_image=%s")
            values.append(sub_cat_image)

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

        fields.append("updated_at=%s")
        values.append(datetime.utcnow())

        values.append(id)

        query = f"""
            UPDATE sub_categories
            SET {', '.join(fields)}
            WHERE id=%s
            RETURNING *
        """

        cur.execute(query, tuple(values))

        data = cur.fetchone()

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Sub Category not found"
            )

        conn.commit()

        return {
            "status": "success",
            "message": "Sub Category Updated Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()
 
#delete sub_category       
@router.delete("/{id}")
def delete_sub_category(
    id: int,
    user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        cur.execute(
            """
            DELETE FROM sub_categories
            WHERE id=%s
            RETURNING *
            """,
            (id,)
        )

        data = cur.fetchone()

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Sub Category not found"
            )

        conn.commit()

        return {
            "status": "success",
            "message": "Sub Category Deleted Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()

#change status
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

        cur.execute(
            """
            UPDATE sub_categories
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

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Sub Category not found"
            )

        conn.commit()

        return {
            "status": "success",
            "message": "Status Updated Successfully",
            "data": data
        }

    finally:
        cur.close()
        conn.close()