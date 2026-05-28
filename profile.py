from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from psycopg2.extras import RealDictCursor
from db import get_conn,TIMEZONE
from auth_utils import get_current_user
from logger import get_logger
import os
from datetime import datetime
from typing import Optional, List
import shutil
import uuid
from zoneinfo import ZoneInfo
# Profile router
router = APIRouter(prefix="/profile", tags=["Profile"])
logger = get_logger(__name__)# Logger instance
def get_current_time():
    return datetime.now(
        ZoneInfo(TIMEZONE)
    )

#get profile
@router.get("/")
def get_profile(user=Depends(get_current_user)):
    logger.info(f"Fetch profile for user_id={user['user_id']}")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
         # Fetch user data from DB
        cur.execute(
            """
            SELECT 
                id,
                username,
                email,
                phone_number,
                profile_image,
                otp_sent_at,
                otp_expired_at,
                no_of_otps,
                user_role,
                email_verified_at,
                phone_verified_at,
                user_comment_for_delete,
                is_active,
                created_at,
                updated_at
            FROM users
            WHERE id = %s
        """,
            (user["user_id"],),
        )

        user_data = cur.fetchone()
          # If user not found
        if not user_data:
            logger.warning(f"User not found: id={user['user_id']}")
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"Profile fetched successfully for user_id={user['user_id']}")

        return {"status": "success", "data": user_data}

    except Exception as e:
        logger.error(f"Error fetching profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        cur.close()
        conn.close()

#Update profile
@router.patch("/")
def update_profile(
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    images: List[UploadFile] = File(None),
    user=Depends(get_current_user),
):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        fields = []
        values = []   

        if username:
            fields.append("username = %s")
            values.append(username)

        if email:
            fields.append("email = %s")
            values.append(email)

        if phone_number:
            fields.append("phone_number = %s")
            values.append(phone_number)
        #image upload
        if images:
            os.makedirs("uploads", exist_ok=True)

            image_paths = []
            # Validate image type
            for file in images:
                if not file.content_type.startswith("image/"):
                    raise HTTPException(status_code=400, detail="Only images allowed")
                 # Validate file extension
                allowed_ext = ["jpg", "jpeg", "png"]
                ext = file.filename.split(".")[-1].lower()

                if ext not in allowed_ext:
                    raise HTTPException(status_code=400, detail="Invalid image format")

                file_name = f"{user['user_id']}_{uuid.uuid4()}.{ext}"
                file_path = f"uploads/{file_name}"

                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                image_paths.append(file_path)
             # Save image path in DB
            fields.append("profile_image = %s")
            values.append(image_paths)

        if not fields:
            raise HTTPException(status_code=400, detail="No data to update")
        fields.append("updated_at = %s")
        values.append(get_current_time())

        values.append(user["user_id"])
         # Final SQL query
        query = f"""
            UPDATE users
            SET {', '.join(fields)}
            WHERE id = %s
            RETURNING id, username, email, phone_number, profile_image, updated_at
        """
        cur.execute(query, values)
        updated = cur.fetchone()

        conn.commit()

        return {"status": "successfully updated", "data": updated}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        cur.close()
        conn.close()
