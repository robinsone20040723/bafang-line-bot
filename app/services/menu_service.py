from app.database.database import get_db_connection


# ==================================================
# 1. 根據餐點名稱查詢價格
# ==================================================
def get_food_price(food_name: str):

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return None

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

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
            ORDER BY mo.option_id
            LIMIT 1
        """

        cursor.execute(sql, (food_name,))
        result = cursor.fetchone()

        return result

    except Exception as error:
        print(f"查詢餐點價格發生錯誤：{error}")
        return None

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


# ==================================================
# 2. 根據分類查詢餐點
# ==================================================
def get_foods_by_category(category_name: str):

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return []

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                fc.category_name,
                m.food_id,
                m.food_name,
                m.is_spicy,
                mo.option_id,
                mo.option_name,
                mo.unit,
                mo.price
            FROM food_category AS fc
            JOIN menu AS m
                ON fc.category_id = m.category_id
            JOIN menu_option AS mo
                ON m.food_id = mo.food_id
            WHERE fc.category_name = %s
              AND fc.is_active = TRUE
              AND m.is_available = TRUE
              AND mo.is_active = TRUE
            ORDER BY m.food_id, mo.option_id
        """

        cursor.execute(sql, (category_name,))
        results = cursor.fetchall()

        return results

    except Exception as error:
        print(f"查詢餐點分類發生錯誤：{error}")
        return []

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
# ==================================================
# 3. 麵的分類
# ==================================================
def get_foods_by_categories(category_names: list[str]):
    """
    查詢多個分類的所有餐點。
    例如：["乾麵", "湯麵"]
    """

    all_foods = []

    for category_name in category_names:
        foods = get_foods_by_category(category_name)
        all_foods.extend(foods)

    return all_foods


# ==================================================
# 4. 根據餐點名稱關鍵字查詢
# ==================================================
def get_foods_by_keyword(keyword: str):

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return []

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                fc.category_name,
                m.food_id,
                m.is_spicy,
                m.food_name,
                mo.option_id,
                mo.option_name,
                mo.unit,
                mo.price
            FROM food_category AS fc
            JOIN menu AS m
                ON fc.category_id = m.category_id
            JOIN menu_option AS mo
                ON m.food_id = mo.food_id
            WHERE m.food_name LIKE %s
              AND fc.is_active = TRUE
              AND m.is_available = TRUE
              AND mo.is_active = TRUE
            ORDER BY fc.sort_order, m.food_id, mo.option_id
        """

        cursor.execute(sql, (f"%{keyword}%",))

        results = cursor.fetchall()

        return results

    except Exception as error:
        print(f"關鍵字查詢餐點發生錯誤：{error}")
        return []

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

# ==================================================
# 5. 根據分類、辣度、預算推薦餐點
# ==================================================
def get_recommended_foods(
    category_name: str,
    spicy: bool | None = None,
    budget: float | None = None,
    limit: int = 3
):

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return []

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                fc.category_name,
                m.food_id,
                m.food_name,
                m.is_spicy,
                mo.option_id,
                mo.option_name,
                mo.unit,
                mo.price
            FROM food_category AS fc
            JOIN menu AS m
                ON fc.category_id = m.category_id
            JOIN menu_option AS mo
                ON m.food_id = mo.food_id
            WHERE fc.category_name = %s
              AND fc.is_active = TRUE
              AND m.is_available = TRUE
              AND mo.is_active = TRUE
        """

        params = [category_name]

        # 如果使用者有指定辣度
        if spicy is not None:
            sql += " AND m.is_spicy = %s"
            params.append(spicy)

        # 如果使用者有指定預算
        if budget is not None:
            sql += " AND mo.price <= %s"
            params.append(budget)

        sql += """
            ORDER BY mo.price ASC, m.food_id ASC
            LIMIT %s
        """

        params.append(limit)

        cursor.execute(sql, tuple(params))

        return cursor.fetchall()

    except Exception as error:
        print(f"推薦餐點查詢發生錯誤：{error}")
        return []

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
# ==================================================
# 6. 取得所有有效餐點名稱
# ==================================================
def get_all_food_names():
    """
    從資料庫取得目前所有有效餐點名稱。

    用途：
    讓 entity.py 可以直接依照資料庫中的餐點名稱
    進行實體擷取，而不需要在 Python 裡手動維護
    food_names 清單。

    回傳範例：
    [
        "招牌鍋貼",
        "韭菜鍋貼",
        "玉米鍋貼",
        "招牌水餃",
        "鮮蝦水餃"
    ]
    """

    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        return []

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT DISTINCT
                m.food_name
            FROM menu AS m
            JOIN food_category AS fc
                ON m.category_id = fc.category_id
            WHERE m.is_available = TRUE
              AND fc.is_active = TRUE
            ORDER BY m.food_name
        """

        cursor.execute(sql)

        results = cursor.fetchall()

        food_names = [
            row["food_name"]
            for row in results
            if row.get("food_name")
        ]

        return food_names

    except Exception as error:
        print(f"取得所有餐點名稱發生錯誤：{error}")
        return []

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

#7.使用關鍵字模糊搜尋餐點名稱。
def search_food_names(keyword):
    """
    使用關鍵字模糊搜尋餐點名稱。

    例如：
    玉米 -> 玉米鍋貼
    鮮蝦 -> 鮮蝦水餃

    只搜尋目前有效的餐點。
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                food_id,
                food_name,
                category_id
            FROM menu
            WHERE food_name LIKE %s
              AND is_available = 1
            ORDER BY food_id
        """

        search_keyword = f"%{keyword}%"

        cursor.execute(
            query,
            (search_keyword,)
        )

        results = cursor.fetchall()

        return results

    except Exception as e:

        print(
            f"[Menu Service] 模糊搜尋餐點失敗：{e}"
        )

        return []

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()