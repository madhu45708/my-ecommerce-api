from datetime import date
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request,Depends
from auth_utils import get_current_user,admin_required
from typing import Optional, List
import os, uuid, shutil, re
from pydantic import BaseModel
from db import get_conn,TIMEZONE
import os, uuid, shutil
from logger import get_logger
from zoneinfo import ZoneInfo
from datetime import datetime

# Create router instance
router = APIRouter(prefix="/products", tags=["Products"])

logger = get_logger(__name__)

def get_current_time():
    return datetime.now(
        ZoneInfo(TIMEZONE)
    )


class ProductResponse(BaseModel):
    status: str
    message: str

# Utility Functions
def clean_null(value):
    if value is None:
        return None
    if isinstance(value, str):
        val = value.strip().lower()
        if val in ["", "null", "[null]", "undefined"]:
            return None
    return value

# Generate URL-friendly slug from product name
def generate_slug(name: str):
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")

#get products
@router.get("/products")
def get_products(user=Depends(get_current_user),):
    logger.info("Fetching all products")
    admin_required(user)

    conn = get_conn()
    cursor = conn.cursor()

    try:
          # Fetch products with images and colors
        cursor.execute("""
            SELECT p.*,
            (SELECT json_agg(pi) FROM product_image_galleries pi WHERE pi.product_id = p.id) AS images,
            (SELECT json_agg(pc) FROM product_colors pc WHERE pc.product_id = p.id) AS colors
            FROM products p
            ORDER BY p.id DESC;
        """)
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

#create products
@router.post("/products")
def create_product(
    name: str = Form(None),
    short_description: Optional[str] = Form(None),
    long_description: Optional[str] = Form(None),
    price: float = Form(None),
    qty: int = Form(None),
    vendor_id: int = Form(None),
    category_id: int = Form(None),
    sub_category_id: Optional[int] = Form(None),
    child_category_id: Optional[int] = Form(None),
    images: List[UploadFile] = File(...),
    sku: Optional[str] = Form(None),
    video_link: Optional[str] = Form(None),
    offer_price: Optional[int] = Form(None),
    offer_start_date: Optional[date] = Form(None),
    offer_end_date: Optional[date] = Form(None),
    product_type: Optional[str] = Form(None),
    seo_title: Optional[str] = Form(None),
    seo_description: Optional[str] = Form(None),
    colors: List[str] = Form(None),
    user=Depends(get_current_user),
):
    admin_required(user)
    logger.info(f"Create product request: name={name}")

    conn = get_conn()
    cursor = conn.cursor()

    try:
        if not images or len(images) == 0:
            raise HTTPException(400, "At least one image required")

        final_slug = generate_slug(name)

        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        image_paths = []

        for file in images:
            if not file.filename:
                continue

            if not file.content_type.startswith("image/"):
                raise HTTPException(400, "Only image files allowed")

            ext = file.filename.split(".")[-1]
            filename = f"{uuid.uuid4().hex[:8]}.{ext}"
            file_path = os.path.join(upload_dir, filename).replace("\\", "/")

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            image_paths.append(file_path)

        if not image_paths:
            raise HTTPException(400, "No valid images uploaded")
        # Insert product into DB
        cursor.execute(
            """
    INSERT INTO products (
        name, short_description, long_description, slug,
        price, qty, sku, thumb_image,
        category_id, sub_category_id, child_category_id, vendor_id,
        video_link, offer_price, offer_start_date, offer_end_date, product_type,seo_title,seo_description,created_at,updated_at
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    RETURNING id;
""",
            (
                name,
                clean_null(short_description),
                long_description,
                final_slug,
                price,
                qty,
                clean_null(sku),
                image_paths[0],
                category_id,
                sub_category_id,
                child_category_id,
                vendor_id,
                video_link,
                offer_price,
                offer_start_date,
                offer_end_date,
                product_type,
                seo_title,
                seo_description,
                get_current_time(),
                get_current_time()
                
            ),
        )

        product_id = cursor.fetchone()["id"]
        # Insert gallery images
        cursor.executemany(
            "INSERT INTO product_image_galleries (product_id, image) VALUES (%s, %s)",
            [(product_id, img) for img in image_paths],
        )

        color_list = []
        if colors:
            temp = []
            for c in colors:
                if "," in c:
                    temp.extend(c.split(","))
                else:
                    temp.append(c)

            color_list = [clean_null(c.strip()) for c in temp if clean_null(c.strip())]

        if color_list:
            cursor.executemany(
                "INSERT INTO product_colors (product_id, color_code) VALUES (%s, %s)",
                [(product_id, c) for c in color_list],
            )

        conn.commit()

        return {"status": "success", "message": "Product created successfully"}
    except HTTPException as e:
        conn.rollback()
        raise e
    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(500, str(e))

    finally:
        cursor.close()
        conn.close()

#update products
@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    name: str = Form(...),
    short_description: Optional[str] = Form(None),
    long_description: Optional[str] = Form(None),
    price: float = Form(None),
    qty: int = Form(None),
    vendor_id: int = Form(None),
    category_id: int = Form(None),
    sub_category_id: Optional[int] = Form(None),
    child_category_id: Optional[int] = Form(None),
    images: List[UploadFile] = File(None),
    sku: Optional[str] = Form(None),
    video_link: Optional[str] = Form(None),
    offer_price: Optional[int] = Form(None),
    offer_start_date: Optional[date] = Form(None),
    offer_end_date: Optional[date] = Form(None),
    product_type: Optional[str] = Form(None),
    seo_title: Optional[str] = Form(None),
    seo_description: Optional[str] = Form(None),
    colors: List[str] = Form(None),
    user=Depends(get_current_user),
):
    admin_required(user)
    logger.info(f"Update request: product_id={product_id}")
    conn = get_conn()
    cursor = conn.cursor()

    try:

        cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cursor.fetchone()

        if not product:
            raise HTTPException(404, "Product not found")

        updated_name = name or product["name"]
        updated_short_desc = (
            clean_null(short_description)
            if short_description is not None
            else product["short_description"]
        )
        # Prepare updated values
        updated_long_desc = long_description or product["long_description"]
        updated_price = price or product["price"]
        updated_qty = qty or product["qty"]
        updated_category = category_id or product["category_id"]
        updated_vendor = vendor_id or product["vendor_id"]
        updated_sku = clean_null(sku) if sku is not None else product["sku"]
        updated_sub_cat = sub_category_id or product["sub_category_id"]
        updated_child_cat = child_category_id or product["child_category_id"]
        updated_video_link = video_link or product["video_link"]
        updated_offer_price = offer_price or product["offer_price"]
        updated_offer_start = offer_start_date or product["offer_start_date"]
        updated_offer_end = offer_end_date or product["offer_end_date"]
        updated_product_type = product_type or product["product_type"]
        updated_seo_title = seo_title or product["seo_title"]
        updated_seo_description = seo_description or product["seo_description"]
        
        # Generate slug
        final_slug = generate_slug(updated_name)

        image_paths = []
        
        # If new images uploaded
        if images and any(file.filename for file in images):

            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)

            for file in images:
                if not file or not file.filename:
                    continue

                if not file.content_type or not file.content_type.startswith("image/"):
                    raise HTTPException(400, "Only image files allowed")

                ext = file.filename.split(".")[-1]
                filename = f"{uuid.uuid4().hex[:8]}.{ext}"
                file_path = os.path.join(upload_dir, filename).replace("\\", "/")

                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                image_paths.append(file_path)

            if not image_paths:
                raise HTTPException(400, "No valid images uploaded")

            thumb_path = image_paths[0]
            gallery_images = image_paths[1:]

            cursor.execute(
                "DELETE FROM product_image_galleries WHERE product_id=%s", (product_id,)
            )

            if gallery_images:
                cursor.executemany(
                    "INSERT INTO product_image_galleries (product_id, image) VALUES (%s, %s)",
                    [(product_id, img) for img in gallery_images],
                )

        else:

            thumb_path = product["thumb_image"]
        # Update product table
        cursor.execute(
            """
            UPDATE products SET
                name=%s,
                short_description=%s,
                long_description=%s,
                slug=%s,
                price=%s,
                qty=%s,
                sku=%s,
                thumb_image=%s,
                category_id=%s,
                sub_category_id=%s,
                child_category_id=%s,
                vendor_id=%s,
                video_link=%s,
                offer_price=%s,
                offer_start_date=%s,
                offer_end_date=%s,
                product_type=%s,
                seo_title=%s,
                seo_description=%s,
                updated_at=%s
                WHERE id=%s
        """,
            (
                updated_name,
                updated_short_desc,
                updated_long_desc,
                final_slug,
                updated_price,
                updated_qty,
                updated_sku,
                thumb_path,
                updated_category,
                updated_sub_cat,
                updated_child_cat,
                updated_vendor,
                updated_video_link,
                updated_offer_price,
                updated_offer_start,
                updated_offer_end,
                updated_product_type,
                updated_seo_title,
                updated_seo_description,
                get_current_time(),
                product_id,
            ),
        )
         # Update colors if provided
        if colors is not None:
            cursor.execute(
                "DELETE FROM product_colors WHERE product_id=%s", (product_id,)
            )

            color_list = []
            for c in colors:
                if c:
                    color_list.extend(c.split(","))

            color_list = [
                clean_null(c.strip()) for c in color_list if clean_null(c.strip())
            ]

            if color_list:
                cursor.executemany(
                    "INSERT INTO product_colors (product_id, color_code) VALUES (%s, %s)",
                    [(product_id, c) for c in color_list],
                )

        conn.commit()

        return {"status": "success", "message": "Product updated successfully"}

    except HTTPException as e:
        conn.rollback()
        raise e

    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(500, "Internal Server Error")

    finally:
        cursor.close()
        conn.close()

#delete the product
@router.delete("/products/{product_id}")
def delete_product(product_id: int,user=Depends(get_current_user),):
    admin_required(user)
    logger.info(f"Delete request: product_id={product_id}")
    conn = get_conn()
    cursor = conn.cursor()

    try:
         # Check product exists
        cursor.execute("SELECT id FROM products WHERE id=%s", (product_id,))
        product = cursor.fetchone()

        if not product:
            raise HTTPException(404, "Product not found")
        # Get product images
        cursor.execute(
            "SELECT image FROM product_image_galleries WHERE product_id=%s",
            (product_id,),
        )
        images = cursor.fetchall()
        # Delete images from server
        for img in images:
            img_path = img["image"]  
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception:
                pass
        # Delete related data
        cursor.execute(
            "DELETE FROM product_image_galleries WHERE product_id=%s", (product_id,)
        )
        cursor.execute("DELETE FROM product_colors WHERE product_id=%s", (product_id,))
         # Delete product
        cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))

        conn.commit()

        return {"status": "success", "message": "Deleted successfully"}

    except Exception as e:
        conn.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(500, str(e))

    finally:
        cursor.close()
        conn.close()
