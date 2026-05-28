from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional

from db import get_conn
from auth_utils import get_current_user
from logger import get_logger

# Address router
router = APIRouter(prefix="/user_address", tags=["User Address"])

logger = get_logger(__name__)


class AddressRequest(BaseModel):
    # User details
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Address details
    address: Optional[str] = None
    city: Optional[str] = None
    state_id: Optional[int] = None
    country_id: Optional[int] = None
    zip: Optional[str] = None

    @validator("*", pre=True)
    def clean_string(cls, v):
        if isinstance(v, str) and v.strip().lower() == "string":
            return None

        if isinstance(v, str) and v.strip() == "":
            return None

        return v


# ADD ADDRESS
@router.post("/")
def add_address(
    data: AddressRequest,
    user=Depends(get_current_user)
):
    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(f"User {user_id} → Add address")

    conn = get_conn()
    cur = conn.cursor()

    try:
        # Validate country
        if data.country_id:
            cur.execute(
                "SELECT id FROM countries WHERE id=%s",
                (data.country_id,)
            )

            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Country not found"
                )

        # Validate state
        if data.state_id and data.country_id:
            cur.execute(
                """
                SELECT id
                FROM states
                WHERE id=%s AND country_id=%s
                """,
                (data.state_id, data.country_id),
            )

            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Invalid state for this country"
                )

        # Insert address
        cur.execute(
            """
            INSERT INTO user_addresses (
                user_id,
                name,
                email,
                phone,
                address,
                city,
                state_id,
                country_id,
                zip,
                created_at,
                updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
            """,
            (
                user_id,
                data.name,
                data.email,
                data.phone,
                data.address,
                data.city,
                data.state_id,
                data.country_id,
                data.zip,
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )

        address = cur.fetchone()

        conn.commit()

        return {
            "message": "Address added successfully",
            "data": address
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Add address error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# GET ADDRESSES
@router.get("/")
def get_addresses(
    user=Depends(get_current_user)
):
    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(f"User {user_id} → Fetch addresses")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                ua.*,
                c.name AS country_name,
                s.name AS state_name
            FROM user_addresses ua
            LEFT JOIN countries c
                ON ua.country_id = c.id
            LEFT JOIN states s
                ON ua.state_id = s.id
            WHERE ua.user_id = %s
            ORDER BY ua.id DESC
            """,
            (user_id,),
        )

        addresses = cur.fetchall()

        return {"data": addresses}

    except Exception as e:
        logger.error(f"Get address error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# UPDATE ADDRESS
@router.put("/{id}")
def update_address(
    id: int,
    data: AddressRequest,
    user=Depends(get_current_user)
):
    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(f"User {user_id} → Update address id={id}")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT *
            FROM user_addresses
            WHERE id=%s AND user_id=%s
            """,
            (id, user_id),
        )

        existing = cur.fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Address not found"
            )

        update_data = {
            k: v
            for k, v in data.dict(exclude_unset=True).items()
            if v is not None
        }

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No valid fields to update"
            )

        fields = []
        values = []

        for key, value in update_data.items():
            fields.append(f"{key}=%s")
            values.append(value)

        fields.append("updated_at=%s")
        values.append(datetime.utcnow())

        values.append(id)

        query = f"""
        UPDATE user_addresses
        SET {", ".join(fields)}
        WHERE id=%s
        RETURNING *;
        """

        cur.execute(query, values)

        updated = cur.fetchone()

        conn.commit()

        return {
            "message": "Address updated successfully",
            "data": updated
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Update address error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()


# DELETE ADDRESS
@router.delete("/{id}")
def delete_address(
    id: int,
    user=Depends(get_current_user)
):
    user_id = (
        user.get("id")
        or user.get("user_id")
        or user.get("_id")
        or user.get("sub")
    )

    logger.info(f"User {user_id} → Delete address id={id}")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT *
            FROM user_addresses
            WHERE id=%s AND user_id=%s
            """,
            (id, user_id),
        )

        address = cur.fetchone()

        if not address:
            raise HTTPException(
                status_code=404,
                detail="Address not found"
            )

        cur.execute(
            "DELETE FROM user_addresses WHERE id=%s",
            (id,)
        )

        conn.commit()

        return {"message": "Address deleted successfully"}

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        logger.error(f"Delete address error: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error"
        )

    finally:
        cur.close()
        conn.close()