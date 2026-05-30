from fastapi import APIRouter, HTTPException, Depends,Query
from psycopg2.extras import RealDictCursor
from db import get_conn, TIMEZONE
from auth_utils import get_current_user, admin_required
from zoneinfo import ZoneInfo
from datetime import datetime

router = APIRouter(prefix="/orders", tags=["orders"])


def get_current_time():
    return datetime.now(
        ZoneInfo(TIMEZONE)
    )


@router.get("/")
def get_all_orders(user=Depends(get_current_user)):
    admin_required(user)
    conn = get_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = """
        SELECT
            orders.id,
            orders.invoice_id,
            orders.user_id,
            orders.sub_total,
            orders.amount,
            orders.product_qty,
            orders.payment_method,
            orders.payment_status,
            orders.order_address,
            orders.shipping_method,
            orders.order_status,
            orders.created_at,

            order_products.product_id,
            order_products.vendor_id,
            order_products.product_name,
            order_products.unit_price,
            order_products.qty

        FROM orders
        INNER JOIN order_products
            ON orders.id = order_products.order_id
            WHERE orders.order_status IN (
            'delivered',
            'cancelled',
            'processing',
            'shipped',
            'pending')
        """
        
        cursor.execute(query)
        result = cursor.fetchall()
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        conn.close()
        
@router.get("/orders/new")
def get_new_orders(user=Depends(get_current_user)):
    admin_required(user)
    conn =get_conn()
    cursor=conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query="""
        select 
         orders.id,
            orders.invoice_id,
            orders.user_id,
            orders.sub_total,
            orders.amount,
            orders.product_qty,
            orders.payment_method,
            orders.payment_status,
            orders.order_address,
            orders.shipping_method,
            orders.order_status,
            orders.created_at,

            order_products.product_id,
            order_products.vendor_id,
            order_products.product_name,
            order_products.unit_price,
            order_products.qty
            
        from orders  
        INNER JOIN order_products
            ON orders.id = order_products.order_id

        WHERE orders.order_status = 'new'
        and orders.created_at >= Now()-interval '7days'
    """
        cursor.execute(query)
        result = cursor.fetchall()
    
        return result

    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@router.get("/orders/delivered")
def get_delivered_orders(user=Depends(get_current_user)):
    admin_required(user)
    conn=get_conn()
    cursor= conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
        select 
         orders.id,
            orders.invoice_id,
            orders.user_id,
            orders.sub_total,
            orders.amount,
            orders.product_qty,
            orders.payment_method,
            orders.payment_status,
            orders.order_address,
            orders.shipping_method,
            orders.order_status,
            orders.created_at,

            order_products.product_id,
            order_products.vendor_id,
            order_products.product_name,
            order_products.unit_price,
            order_products.qty
            
            from orders
            inner join order_products
              on orders.id= order_products.order_id
              
            where orders.order_status = 'delivered'
        """
        cursor.execute(query)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
    finally:
        cursor.close()
        conn.close()
        
@router.get("/orders/cancelled")
def get_cancelled_orders(user=Depends(get_current_user)):
    admin_required(user)
    conn=get_conn()
    cursor= conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
        select 
         orders.id,
            orders.invoice_id,
            orders.user_id,
            orders.sub_total,
            orders.amount,
            orders.product_qty,
            orders.payment_method,
            orders.payment_status,
            orders.order_address,
            orders.shipping_method,
            orders.order_status,
            orders.created_at,

            order_products.product_id,
            order_products.vendor_id,
            order_products.product_name,
            order_products.unit_price,
            order_products.qty
            
            from orders
            inner join order_products
              on orders.id= order_products.order_id
              
            where orders.order_status = 'cancelled'
        """
        cursor.execute(query)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
    finally:
        cursor.close()
        conn.close()
        
@router.get("/orders/pending")
def get_pending_orders(user=Depends(get_current_user)):
    admin_required(user)
    conn=get_conn()
    cursor= conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
        select 
         orders.id,
            orders.invoice_id,
            orders.user_id,
            orders.sub_total,
            orders.amount,
            orders.product_qty,
            orders.payment_method,
            orders.payment_status,
            orders.order_address,
            orders.shipping_method,
            orders.order_status,
            orders.created_at,

            order_products.product_id,
            order_products.vendor_id,
            order_products.product_name,
            order_products.unit_price,
            order_products.qty
            
            from orders
            inner join order_products
              on orders.id= order_products.order_id
              
            where orders.order_status = 'pending'
        """
        cursor.execute(query)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
    finally:
        cursor.close()
        conn.close()
        

        

        
        
        
    
        