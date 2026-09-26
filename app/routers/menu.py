from fastapi import APIRouter, HTTPException

from app.database.database import get_db_connection


router = APIRouter(
    prefix="/api/menu",
    tags=["Menu"]
)


@router.get("")
def get_menu(
    category: str | None = None,
    food_name: str | None = None
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

        sql = """
            SELECT
                m.food_id,
                fc.category_name,
                m.food_name,
                m.description,
                m.is_spicy,
                m.is_vegetarian,
                mo.option_id,
                mo.option_name,
                mo.quantity_value,
                mo.unit,
                mo.price
            FROM menu AS m
            JOIN food_category AS fc
                ON m.category_id = fc.category_id
            JOIN menu_option AS mo
                ON m.food_id = mo.food_id
            WHERE m.is_available = TRUE
                AND fc.is_active = TRUE
                AND mo.is_active = TRUE
                AND (%s IS NULL OR fc.category_name = %s)
                AND (%s IS NULL OR m.food_name = %s)
            ORDER BY
                fc.sort_order,
                m.food_id,
                mo.option_id;
        """
        cursor.execute(
            sql,
            (category, category, food_name, food_name)
        )
        menu_data = cursor.fetchall()

        return {
            "success": True,
            "count": len(menu_data),
            "data": menu_data
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"查詢菜單失敗：{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection.is_connected():
            connection.close()