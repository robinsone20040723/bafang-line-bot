import math

from fastapi import APIRouter, HTTPException

from app.database.database import get_db_connection
from app.schemas.order import (
    CalculateOrderRequest,
    CalculateOrderByNameRequest
)


router = APIRouter(
    prefix="/api/orders",
    tags=["Order"]
)




@router.post("/calculate")
def calculate_order(request: CalculateOrderRequest):

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        raise HTTPException(
            status_code=500,
            detail="資料庫連線失敗"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        result_items = []
        total_amount = 0.0

        for item in request.items:

            sql = """
                SELECT
                    m.food_id,
                    m.food_name,
                    mo.option_id,
                    mo.option_name,
                    mo.unit,
                    mo.price
                FROM menu_option AS mo
                JOIN menu AS m
                    ON mo.food_id = m.food_id
                WHERE mo.option_id = %s
                  AND mo.is_active = TRUE
                  AND m.is_available = TRUE
            """

            cursor.execute(
                sql,
                (item.option_id,)
            )

            product = cursor.fetchone()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到 option_id = {item.option_id} 的商品"
                )

            unit_price = float(product["price"])

            subtotal = unit_price * item.quantity

            total_amount += subtotal

            result_items.append({
                "food_id": product["food_id"],
                "food_name": product["food_name"],
                "option_id": product["option_id"],
                "option_name": product["option_name"],
                "unit": product["unit"],
                "quantity": item.quantity,
                "unit_price": unit_price,
                "subtotal": subtotal
            })


        rounded_total = math.ceil(total_amount)

        return {
            "success": True,
            "items": result_items,
            "original_total": total_amount,
            "total_amount": rounded_total,
            "message": f"總金額為 {rounded_total} 元"
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"計算訂單失敗：{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()



@router.post("/calculate-by-name")
def calculate_order_by_name(
    request: CalculateOrderByNameRequest
):

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        raise HTTPException(
            status_code=500,
            detail="資料庫連線失敗"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        result_items = []
        total_amount = 0.0

        for item in request.items:

            sql = """
                SELECT
                    m.food_id,
                    m.food_name,
                    mo.option_id,
                    mo.option_name,
                    mo.unit,
                    mo.price
                FROM menu AS m
                JOIN menu_option AS mo
                    ON m.food_id = mo.food_id
                WHERE m.food_name = %s
                  AND m.is_available = TRUE
                  AND mo.is_active = TRUE
                LIMIT 1
            """

            cursor.execute(
                sql,
                (item.food_name,)
            )

            product = cursor.fetchone()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到餐點：{item.food_name}"
                )

            unit_price = float(product["price"])

            subtotal = unit_price * item.quantity

            total_amount += subtotal

            result_items.append({
                "food_id": product["food_id"],
                "food_name": product["food_name"],
                "option_id": product["option_id"],
                "option_name": product["option_name"],
                "unit": product["unit"],
                "quantity": item.quantity,
                "unit_price": unit_price,
                "subtotal": subtotal
            })

        # 無條件進位
        rounded_total = math.ceil(total_amount)

        return {
            "success": True,
            "items": result_items,
            "original_total": total_amount,
            "total_amount": rounded_total,
            "message": f"總金額為 {rounded_total} 元"
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"依餐點名稱計算訂單失敗：{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()