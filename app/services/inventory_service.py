from app.database.database import get_db_connection


def get_inventory(restaurant_name: str, food_name: str):
    """
    根據「分店名稱 + 餐點名稱」查詢庫存。

    例如：
    restaurant_name = "斗六中山店"
    food_name = "玉米鍋貼"

    回傳：
    {
        "restaurant_name": "八方雲集斗六中山店",
        "food_name": "玉米鍋貼",
        "option_name": "單顆",
        "unit": "顆",
        "price": Decimal("7.00"),
        "stock_quantity": 230,
        "stock_status": "available"
    }

    如果找不到資料：
    None
    """

    connection = get_db_connection()

    # 檢查資料庫連線
    if connection is None or not connection.is_connected():
        return None

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                r.restaurant_id,
                r.restaurant_name,
                m.food_id,
                m.food_name,
                mo.option_id,
                mo.option_name,
                mo.unit,
                mo.price,
                i.stock_quantity,
                i.stock_status,
                i.updated_at
            FROM inventory AS i

            JOIN restaurant AS r
                ON i.restaurant_id = r.restaurant_id

            JOIN menu_option AS mo
                ON i.option_id = mo.option_id

            JOIN menu AS m
                ON mo.food_id = m.food_id

            WHERE r.restaurant_name LIKE %s
              AND m.food_name = %s
              AND r.is_active = TRUE
              AND m.is_available = TRUE
              AND mo.is_active = TRUE

            ORDER BY mo.option_id

            LIMIT 1
        """

        cursor.execute(
            sql,
            (
                f"%{restaurant_name}%",
                food_name
            )
        )

        result = cursor.fetchone()

        return result

    except Exception as error:
        print(f"查詢庫存發生錯誤：{error}")
        return None

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()