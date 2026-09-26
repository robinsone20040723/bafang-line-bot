from fastapi import APIRouter, HTTPException

from app.database.database import get_db_connection


router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"]
)


@router.get("")
def get_inventory(
    restaurant: str | None = None,
    food_name: str | None = None
):
    # 1. 建立資料庫連線
    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        raise HTTPException(
            status_code=500,
            detail="資料庫連線失敗"
        )

    cursor = None

    try:
        # 2. 建立 cursor
        # dictionary=True 會讓查詢結果以字典形式回傳
        cursor = connection.cursor(dictionary=True)

        # 3. 建立庫存查詢 SQL
        sql = """
            SELECT
                r.restaurant_id,
                r.restaurant_name,
                m.food_id,
                m.food_name,
                mo.option_id,
                mo.option_name,
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
            WHERE r.is_active = TRUE
              AND m.is_available = TRUE
              AND mo.is_active = TRUE
        """

        # 4. 儲存 SQL 查詢參數
        params = []

        # 如果使用者有輸入分店名稱，就加入分店搜尋條件
        if restaurant:
            sql += " AND r.restaurant_name LIKE %s"
            params.append(f"%{restaurant}%")

        # 如果使用者有輸入餐點名稱，就加入餐點搜尋條件
        if food_name:
            sql += " AND m.food_name LIKE %s"
            params.append(f"%{food_name}%")

        # 5. 設定查詢結果排序方式
        sql += """
            ORDER BY
                r.restaurant_id,
                m.food_id,
                mo.option_id
        """

        # 6. 執行 SQL
        cursor.execute(sql, params)

        # 7. 取得全部查詢結果
        inventory_data = cursor.fetchall()

        # 8. 如果完全查不到資料
        if len(inventory_data) == 0:
            return {
                "success": True,
                "count": 0,
                "message": "查無符合條件的庫存資料",
                "data": []
            }

        # 9. 取得第一筆查詢結果
        item = inventory_data[0]

        # 10. 判斷商品是否有庫存
        if (
            item["stock_status"] == "available"
            and item["stock_quantity"] is not None
            and item["stock_quantity"] > 0
        ):
            message = (
                f'{item["restaurant_name"]}的'
                f'{item["food_name"]}目前有貨，'
                f'庫存約 {item["stock_quantity"]} 顆。'
            )
        else:
            message = (
                f'{item["restaurant_name"]}的'
                f'{item["food_name"]}目前缺貨。'
            )

        # 11. 回傳 API 結果
        return {
            "success": True,
            "count": len(inventory_data),
            "message": message,
            "data": inventory_data
        }

    except Exception as error:
        # 發生錯誤時回傳 HTTP 500
        raise HTTPException(
            status_code=500,
            detail=f"查詢庫存失敗：{error}"
        )

    finally:
        # 不論成功或失敗，都關閉 cursor
        if cursor is not None:
            cursor.close()

        # 關閉資料庫連線
        if connection.is_connected():
            connection.close()