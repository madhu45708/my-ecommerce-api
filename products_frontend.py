from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor
from db import get_conn
from logger import get_logger
import traceback

router = APIRouter(prefix="/shop", tags=["Frontend Products"])
logger = get_logger(__name__)



# products list
@router.get("/")
def products_index(
    category: str = None,
    subcategory: str = None,
    child_category: str = None,
    search: str = None,
    sort_by: str = None,
    page: int = 1,
    limit: int = 12,
):

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Base query
        query = """
            SELECT
                p.*,
                (
                    SELECT ROUND(AVG(CAST(r.rating AS NUMERIC)), 1)
                    FROM product_reviews r
                    WHERE r.product_id = p.id
                ) AS reviews_avg_rating,
                (
                    SELECT COUNT(*)
                    FROM product_reviews r
                    WHERE r.product_id = p.id
                ) AS reviews_count
            FROM products p
            WHERE p.status = 1
            AND p.is_approved = 1
        """

        values = []

        # category filter
        if category:
            query += """
                AND p.category_id = (
                    SELECT id FROM categories WHERE slug = %s
                )
            """
            values.append(category)

        # subcategory filter
        if subcategory:
            query += """
                AND p.sub_category_id = (
                    SELECT id FROM sub_categories WHERE slug = %s
                )
            """
            values.append(subcategory)

        # child category filter
        if child_category:
            query += """
                AND p.child_category_id = (
                    SELECT id FROM child_categories WHERE slug = %s
                )
            """
            values.append(child_category)

        # sorting
        if sort_by == "Low to High":
            query += " ORDER BY p.price ASC "
        elif sort_by == "High to Low":
            query += " ORDER BY p.price DESC "
        else:
            query += " ORDER BY p.created_at DESC "

        # pagination
        offset = (page - 1) * limit
        query += " LIMIT %s OFFSET %s "
        values.extend([limit, offset])

        # execute query
        cur.execute(query, tuple(values))
        products = cur.fetchall()

        final_products = []

        # enrich products
        for product in products:

            cur.execute(
                "SELECT * FROM categories WHERE id = %s",
                (product["category_id"],),
            )
            product["category"] = cur.fetchone()

            cur.execute(
                "SELECT * FROM product_image_galleries WHERE product_id = %s",
                (product["id"],),
            )
            product["product_image_galleries"] = cur.fetchall()

            product["colors"] = []

            final_products.append(product)

        # total count (IMPORTANT: OUTSIDE LOOP)
        cur.execute("""
            SELECT COUNT(*) AS total
            FROM products
            WHERE status = 1 AND is_approved = 1
        """)
        total_products = cur.fetchone()["total"]

        # categories
        cur.execute("""
            SELECT * FROM categories WHERE status = 1
        """)
        categories = cur.fetchall()

        # color filters (safe)
        try:
            cur.execute("SELECT * FROM product_colors")
            color_filters = cur.fetchall()
        except Exception:
            color_filters = []

        return {
            "status": True,
            "message": "Products fetched successfully",
            "products": {
                "current_page": page,
                "per_page": limit,
                "total": total_products,
                "data": final_products,
            },
            "categories": categories,
            "filter_info": {"colorfilter": color_filters},
        }

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        cur.close()
        conn.close()


# SHIPPING RULES
@router.get("/shipping_rules")
def shipping_rules():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT * FROM shipping_rules
            WHERE status = 1
            ORDER BY created_at DESC
        """)
        return {"status": "success", "data": cur.fetchall()}

    finally:
        cur.close()
        conn.close()

# SINGLE PRODUCT PAGE
@router.get("/{slug}")
def show_product(slug: str):

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT
                p.*,
                (
                    SELECT ROUND(AVG(CAST(r.rating AS NUMERIC)), 1)
                    FROM product_reviews r
                    WHERE r.product_id = p.id
                ) AS reviews_avg_rating,
                (
                    SELECT COUNT(*)
                    FROM product_reviews r
                    WHERE r.product_id = p.id
                ) AS reviews_count
            FROM products p
            WHERE p.slug = %s
            AND p.status = 1
        """,
            (slug,),
        )

        product = cur.fetchone()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # category
        cur.execute(
            "SELECT * FROM categories WHERE id = %s",
            (product["category_id"],),
        )
        product["category"] = cur.fetchone()

        # images
        cur.execute(
            "SELECT * FROM product_image_galleries WHERE product_id = %s",
            (product["id"],),
        )
        product["product_image_galleries"] = cur.fetchall()

        product["colors"] = []

        # reviews
        cur.execute(
            """
            SELECT * FROM product_reviews
            WHERE product_id = %s AND status = True
            ORDER BY created_at DESC
        """,
            (product["id"],),
        )
        reviews = cur.fetchall()

        # related products
        cur.execute(
            """
            SELECT * FROM products
            WHERE category_id = %s
            AND id != %s
            AND status = 1
            LIMIT 20
        """,
            (product["category_id"], product["id"]),
        )
        related_products = cur.fetchall()

        return {
            "status": True,
            "message": "Product details fetched successfully",
            "product": product,
            "reviews": reviews,
            "related_products": related_products,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        cur.close()
        conn.close()