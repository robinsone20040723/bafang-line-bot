from app.database.database import get_db_connection


def get_restaurant_info(restaurant_name: str):
    """
    查詢指定分店的基本資料與營業時間。
    """

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return None

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        # 查詢分店基本資料
        restaurant_sql = """
            SELECT
                restaurant_id,
                restaurant_name,
                address,
                phone
            FROM restaurant
            WHERE restaurant_name LIKE %s
              AND is_active = TRUE
            LIMIT 1
        """

        cursor.execute(
            restaurant_sql,
            (f"%{restaurant_name}%",)
        )

        restaurant = cursor.fetchone()

        if restaurant is None:
            return None

        # 查詢營業時間
        hours_sql = """
            SELECT
                period_no,
                open_time,
                close_time,
                note
            FROM restaurant_hours
            WHERE restaurant_id = %s
            ORDER BY period_no
        """

        cursor.execute(
            hours_sql,
            (restaurant["restaurant_id"],)
        )

        business_hours = cursor.fetchall()

        restaurant["business_hours"] = business_hours

        return restaurant

    except Exception as error:
        print(f"查詢分店資料發生錯誤：{error}")
        return None

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
def get_all_restaurants():
    """
    查詢所有目前啟用中的分店。

    使用情境：
    - 有哪些店
    - 有哪些分店
    - 有什麼分店
    - 分店有哪些
    """

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return []

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                restaurant_id,
                restaurant_name,
                address,
                phone
            FROM restaurant
            WHERE is_active = TRUE
            ORDER BY restaurant_id
        """

        cursor.execute(sql)

        restaurants = cursor.fetchall()

        return restaurants

    except Exception as error:
        print(f"查詢所有分店發生錯誤：{error}")
        return []

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()