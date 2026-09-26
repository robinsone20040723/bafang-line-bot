from fastapi import APIRouter, HTTPException

from app.database.database import get_db_connection


router = APIRouter(
    prefix="/api/restaurants",
    tags=["Restaurant"]
)


@router.get("")
def get_restaurants(restaurant: str | None = None):
    connection = get_db_connection()

    if connection is None or not connection.is_connected():
        raise HTTPException(
            status_code=500,
            detail="資料庫連線失敗"
        )

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                r.restaurant_id,
                r.restaurant_name,
                r.address,
                r.phone,
                rh.period_no,
                rh.open_time,
                rh.close_time,
                rh.note
            FROM restaurant AS r
            LEFT JOIN restaurant_hours AS rh
                ON r.restaurant_id = rh.restaurant_id
            WHERE r.is_active = TRUE
        """

        params = []

        if restaurant:
            sql += " AND r.restaurant_name LIKE %s"
            params.append(f"%{restaurant}%")

        sql += """
            ORDER BY
                r.restaurant_id,
                rh.period_no
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        if len(rows) == 0:
            return {
                "success": True,
                "count": 0,
                "message": "查無符合條件的分店資料",
                "data": []
            }

        restaurants = {}

        for row in rows:
            restaurant_id = row["restaurant_id"]

            if restaurant_id not in restaurants:
                restaurants[restaurant_id] = {
                    "restaurant_id": restaurant_id,
                    "restaurant_name": row["restaurant_name"],
                    "address": row["address"],
                    "phone": row["phone"],
                    "business_hours": []
                }

            if row["open_time"] is not None:
                restaurants[restaurant_id]["business_hours"].append({
                    "period_no": row["period_no"],
                    "open_time": str(row["open_time"]),
                    "close_time": str(row["close_time"]),
                    "note": row["note"]
                })

        restaurant_data = list(restaurants.values())

        return {
            "success": True,
            "count": len(restaurant_data),
            "data": restaurant_data
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"查詢分店資料失敗：{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection.is_connected():
            connection.close()