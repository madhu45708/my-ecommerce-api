from fastapi import APIRouter, HTTPException, Depends
from db import get_conn
from auth_utils import get_current_user
from logger import get_logger

# Location router (countries, states, etc.)
router = APIRouter(prefix="/location", tags=["Location"])
logger = get_logger(__name__)


# get countries
@router.get("/countries")
def get_countries(user=Depends(get_current_user)):
    logger.info(f"user {user['user_id']}->fetch countries")
    conn = get_conn()
    cur = conn.cursor()

    try:
        # Fetch all countries
        cur.execute("SELECT id, name FROM countries ORDER BY name")
        countries = cur.fetchall()

        return {"status": True, "data": countries}

    finally:
        cur.close()
        conn.close()


# get states for country
@router.get("/states/{country_id}")
def get_states(country_id: int, user=Depends(get_current_user)):
    logger.info(f"User {user['user_id']} → Fetch states for country_id={country_id}")
    conn = get_conn()
    cur = conn.cursor()

    try:
        # Fetch states for given country
        cur.execute(
            """
            SELECT id, name, country_id
            FROM states
            WHERE country_id = %s
            ORDER BY name
            """,
            (country_id,),
        )

        states = cur.fetchall()
        # If no states found
        if not states:
            return {"status": False, "message": "No states found", "data": []}

        return {"status": True, "country_id": country_id, "data": states}

    finally:
        cur.close()
        conn.close()
