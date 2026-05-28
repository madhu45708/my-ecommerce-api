from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from db import get_conn, TIMEZONE
from auth_utils import get_current_user
from logger import get_logger
from zoneinfo import ZoneInfo
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])
logger = get_logger(__name__)


def get_current_time():
    return datetime.now(
        ZoneInfo(TIMEZONE)
    )


class WishlistRequest(BaseModel):
    product_id: int


# GET WISHLIST
@router.get("/")
def get_wishlist(user=Depends(get_current_user)):

    # Only normal users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access wishlist"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        logger.info(f"User {user_id} → Fetch wishlist")

        cur.execute(
            "SELECT * FROM wishlists WHERE user_id=%s",
            (user_id,)
        )

        data = cur.fetchall()

        return data

    except Exception as e:
        logger.error(f"Error fetching wishlist: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# ADD TO WISHLIST
@router.post("/")
def add_to_wishlist(
    data: WishlistRequest,
    user=Depends(get_current_user)
):

    # Only normal users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access wishlist"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        logger.info(
            f"User {user_id} → Add product {data.product_id} to wishlist"
        )

        cur.execute(
            """
            SELECT id
            FROM wishlists
            WHERE user_id=%s AND product_id=%s
            """,
            (user_id, data.product_id),
        )

        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="Item already exists in wishlist"
            )

        cur.execute(
            """
            INSERT INTO wishlists
            (user_id, product_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                data.product_id,
                get_current_time(),
                get_current_time(),
            ),
        )

        conn.commit()

        return {"message": "Added to wishlist"}

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding wishlist: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# DELETE WISHLIST
@router.delete("/{id}")
def delete(id: int, user=Depends(get_current_user)):

    # Only normal users allowed
    if user.get("user_role") != "user":
        raise HTTPException(
            status_code=403,
            detail="Admin cannot access wishlist"
        )

    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        logger.info(f"User {user_id} → Delete wishlist id={id}")

        cur.execute(
            "SELECT * FROM wishlists WHERE id=%s",
            (id,)
        )

        item = cur.fetchone()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Not found"
            )

        if item["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not allowed"
            )

        cur.execute(
            "DELETE FROM wishlists WHERE id=%s",
            (id,)
        )

        conn.commit()

        return {"message": "Deleted"}

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Error deleting wishlist: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()