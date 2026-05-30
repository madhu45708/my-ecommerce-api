from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from auth import router as auth_router
from products import router as product_router
from wishlist import router as wishlist_router
from carts import router as cart_router
from locations import router as location_router
from user_address import router as address_router
from profile import router as profile_router
from shipping_rules import router as shipping_rules_router
from banners import router as banner_router
from categories import router as categories
from sub_categories import router as sub_categories
from child_categories import router as child_categories
from customer_management import router as customer_management
from contact_us import router as contact_us
from home_page import router as home_page
from orders import router as orders
from products_frontend import router as products_frontend_router

app = FastAPI(
    title="E-Commerce API", description="Complete E-Commerce Backend", version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(product_router)
app.include_router(wishlist_router)
app.include_router(cart_router)
app.include_router(location_router)
app.include_router(address_router)
app.include_router(shipping_rules_router)
app.include_router(banner_router)
app.include_router(categories)
app.include_router(sub_categories)
app.include_router(child_categories)
app.include_router(customer_management)
app.include_router(contact_us)
app.include_router(home_page)
app.include_router(orders)
app.include_router(products_frontend_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
