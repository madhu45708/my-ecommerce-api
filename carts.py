from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from db import get_conn, TIMEZONE
from auth_utils import get_current_user
from logger import get_logger
from datetime import datetime
from zoneinfo import ZoneInfo
from psycopg2.extras import RealDictCursor

# Cart router
router = APIRouter(prefix="/carts", tags=["Carts"])
logger = get_logger(__name__)


def get_current_time():
    return datetime.now(ZoneInfo(TIMEZONE))


class CartRequest(BaseModel):
    product_id: int
    quantity: int = 1


# ADD TO CART
@router.post("/")
def add_to_cart(data: CartRequest, user=Depends(get_current_user)):

    # Only frontend users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access cart"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(
        f"User {user_id} → Add product {data.product_id} to cart"
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        product_id = data.product_id
        quantity = data.quantity

        # Check product exists
        cur.execute(
            "SELECT * FROM products WHERE id=%s",
            (product_id,)
        )

        product = cur.fetchone()

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        # Check already in cart
        cur.execute(
            """
            SELECT *
            FROM carts
            WHERE user_id=%s
            AND product_id=%s
            """,
            (user_id, product_id),
        )

        existing = cur.fetchone()

        if existing:
            logger.warning(
                f"Product already exists in cart: user={user_id}"
            )

            return {
                "message": "Product already exists in cart",
                "data": existing
            }

        # Calculate total
        total_price = product["price"] * quantity

        # Insert cart item
        cur.execute(
            """
            INSERT INTO carts
            (
                user_id,
                product_id,
                quantity,
                price,
                total_price,
                created_at,
                updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
            """,
            (
                user_id,
                product_id,
                quantity,
                product["price"],
                total_price,
                get_current_time(),
                get_current_time(),
            ),
        )

        new_item = cur.fetchone()

        conn.commit()

        logger.info(
            f"Added to cart: user={user_id} product={product_id}"
        )

        return {
            "message": "Added to cart successfully",
            "data": new_item
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Error adding cart item: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# INCREASE QUANTITY
@router.put("/increase")
def increase_quantity(
    data: CartRequest,
    user=Depends(get_current_user)
):

    # Only frontend users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access cart"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(
        f"User {user_id} → Increase quantity product={data.product_id}"
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        product_id = data.product_id
        quantity = data.quantity

        # Get cart item
        cur.execute(
            """
            SELECT *
            FROM carts
            WHERE user_id=%s
            AND product_id=%s
            """,
            (user_id, product_id),
        )

        cart = cur.fetchone()

        if not cart:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        new_quantity = cart["quantity"] + quantity
        total_price = new_quantity * cart["price"]

        cur.execute(
            """
            UPDATE carts
            SET quantity=%s,
                total_price=%s,
                updated_at=%s
            WHERE id=%s
            RETURNING *
            """,
            (
                new_quantity,
                total_price,
                get_current_time(),
                cart["id"]
            ),
        )

        updated = cur.fetchone()

        conn.commit()

        return {
            "message": "Quantity increased successfully",
            "data": updated
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Error increasing quantity: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# DECREASE QUANTITY
@router.put("/decrease")
def decrease_quantity(
    data: CartRequest,
    user=Depends(get_current_user)
):

    # Only frontend users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access cart"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(
        f"User {user_id} → Decrease quantity product={data.product_id}"
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        product_id = data.product_id
        quantity = data.quantity

        # Get cart item
        cur.execute(
            """
            SELECT *
            FROM carts
            WHERE user_id=%s
            AND product_id=%s
            """,
            (user_id, product_id),
        )

        cart = cur.fetchone()

        if not cart:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        if cart["quantity"] <= quantity:
            raise HTTPException(
                status_code=400,
                detail="Quantity cannot be less than 1"
            )

        new_quantity = cart["quantity"] - quantity
        total_price = new_quantity * cart["price"]

        cur.execute(
            """
            UPDATE carts
            SET quantity=%s,
                total_price=%s,
                updated_at=%s
            WHERE id=%s
            RETURNING *
            """,
            (
                new_quantity,
                total_price,
                get_current_time(),
                cart["id"]
            ),
        )

        updated = cur.fetchone()

        conn.commit()

        return {
            "message": "Quantity decreased successfully",
            "data": updated
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Error decreasing quantity: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# GET CART
@router.get("/")
def get_cart(user=Depends(get_current_user)):

    # Only frontend users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access cart"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(f"User {user_id} → Fetch cart")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            SELECT *
            FROM carts
            WHERE user_id=%s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        items = cur.fetchall()

        total_items = len(items)

        total_value = sum(
            item["total_price"] for item in items
        )

        return {
            "data": items,
            "total_items": total_items,
            "total_value": total_value
        }

    except Exception as e:

        logger.error(f"Error fetching cart: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# DELETE CART ITEM
@router.delete("/{id}")
def delete_cart_item(
    id: int,
    user=Depends(get_current_user)
):

    # Only frontend users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access cart"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(
        f"User {user_id} → Delete cart item id={id}"
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check item exists
        cur.execute(
            """
            SELECT *
            FROM carts
            WHERE id=%s
            AND user_id=%s
            """,
            (id, user_id)
        )

        item = cur.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        # Delete item
        cur.execute(
            """
            DELETE FROM carts
            WHERE id=%s
            """,
            (id,)
        )

        conn.commit()

        return {
            "message": "Removed from cart successfully"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Error deleting cart item: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()