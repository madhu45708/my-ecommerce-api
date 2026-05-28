from fastapi import APIRouter,Depends,HTTPException
from db import get_conn,TIMEZONE
from pydantic import BaseModel,Field
from datetime import datetime
from typing import List
from auth_utils import get_current_user,admin_required
from logger import get_logger
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/home-sections",
    tags=["Home Sections"])
logger = get_logger(__name__)

def get_current_time():
    return datetime.now(
        ZoneInfo(TIMEZONE)
    )
    
class HomeSectionCreate(BaseModel):
    name: str
    status: bool
    product_ids: List[int] = Field(default_factory=list)


class HomeSectionUpdate(BaseModel):
    name: str
    status: bool
    product_ids: List[int] = Field(default_factory=list)
    
class ChangeStatus(BaseModel):
    status: bool

#get api
@router.get("/")
def get_home_sections(
    user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                hs.name,
                hs.status,
                hsp.product_id
            FROM home_sections hs
            LEFT JOIN home_section_products hsp
            ON hs.id = hsp.home_section_id
            ORDER BY hs.id DESC
        """)

        rows = cursor.fetchall()

        result = {}

        for row in rows:

            section_name = row["name"]

            if section_name not in result:

                result[section_name] = {
                    "name": row["name"],
                    "status": row["status"],
                    "product_ids": []
                }

            if row["product_id"] is not None:
                result[section_name]["product_ids"].append(
                    row["product_id"]
                )

        return list(result.values())

    finally:
        cursor.close()
        conn.close()


        
#post api
@router.post("/")
def create_home_section(
    data: HomeSectionCreate,
    user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO home_sections (
                name,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            data.name,
            data.status,
            get_current_time(),
            get_current_time()
        ))

        section_id = cursor.fetchone()["id"]

        for product_id in data.product_ids:

            cursor.execute("""
                INSERT INTO home_section_products (
                    home_section_id,
                    product_id
                )
                VALUES (%s, %s)
            """, (
                section_id,
                product_id
            ))

        conn.commit()

        return {
            "status": "success",
            "message": "Home section created successfully"
        }

    except Exception as e:

        conn.rollback()
        raise HTTPException(500, str(e))

    finally:
        cursor.close()
        conn.close()
        
#update api
@router.put("/{section_id}")
def update_home_section(
    section_id: int,
    data: HomeSectionUpdate,
    user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cursor = conn.cursor()

    try:
        # Check section exists
        cursor.execute("""
            SELECT id
            FROM home_sections
            WHERE id = %s
        """, (section_id,))

        section = cursor.fetchone()

        if not section:
            raise HTTPException(
                status_code=404,
                detail="Home section not found"
            )

        # Update home section
        cursor.execute("""
            UPDATE home_sections
            SET
                name = %s,
                status = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            data.name,
            data.status,
            get_current_time(),
            section_id
        ))

        # Delete old product mappings
        cursor.execute("""
            DELETE FROM home_section_products
            WHERE home_section_id = %s
        """, (section_id,))

        # Insert new product mappings
        for product_id in data.product_ids:

            cursor.execute("""
                INSERT INTO home_section_products (
                    home_section_id,
                    product_id
                )
                VALUES (%s, %s)
            """, (
                section_id,
                product_id
            ))

        conn.commit()

        return {
            "status": "success",
            "message": "Home section updated successfully"
        }

    except Exception as e:

        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        conn.close()    
        
#delete api
@router.delete("/{section_id}")
def delete_home_section(
    section_id: int,
    user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cursor = conn.cursor()

    try:

        # Check section exists
        cursor.execute("""
            SELECT id
            FROM home_sections
            WHERE id = %s
        """, (section_id,))

        section = cursor.fetchone()

        if not section:
            raise HTTPException(
                status_code=404,
                detail="Home section not found"
            )

        # Delete product mappings first
        cursor.execute("""
            DELETE FROM home_section_products
            WHERE home_section_id = %s
        """, (section_id,))

        # Delete home section
        cursor.execute("""
            DELETE FROM home_sections
            WHERE id = %s
        """, (section_id,))

        conn.commit()

        return {
            "status": "success",
            "message": "Home section deleted successfully"
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        conn.close()
        
#change status api
@router.post("/{section_id}/change-status")
def change_home_section_status(
    section_id: int,
    data: ChangeStatus,
    user=Depends(get_current_user)
):

    admin_required(user)

    conn = get_conn()
    cursor = conn.cursor()

    try:

        # Check section exists
        cursor.execute("""
            SELECT id
            FROM home_sections
            WHERE id = %s
        """, (section_id,))

        section = cursor.fetchone()

        if not section:
            raise HTTPException(
                status_code=404,
                detail="Home section not found"
            )

        # Update status
        cursor.execute("""
            UPDATE home_sections
            SET
                status = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            data.status,
            get_current_time(),
            section_id
        ))

        conn.commit()

        return {
            "status": "success",
            "message": "Home section status updated successfully"
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        conn.close()