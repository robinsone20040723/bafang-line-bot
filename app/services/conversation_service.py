# ==================================================
# conversation_service.py
#
# 功能：
# 暫時保存每位使用者目前的對話狀態。
#
# 目前支援：
# 1. 推薦多輪對話
# 2. 模糊餐點選擇
# 3. 庫存查詢分店選擇
#
# 未來串接 LINE 後：
# user_id 會使用 LINE 提供的 userId。
# ==================================================


# --------------------------------------------------
# 暫存所有使用者的對話狀態
# --------------------------------------------------
conversation_states = {}


# ==================================================
# 1. 取得使用者目前的對話狀態
# ==================================================
def get_conversation_state(user_id: str):

    return conversation_states.get(user_id)


# ==================================================
# 2. 建立 / 重設使用者對話狀態
# ==================================================
def set_conversation_state(
    user_id: str,
    state: str,
    category=None,
    spicy=None,
    budget=None,
    pending_intent=None,
    food_candidates=None,
    selected_food=None,
):

    conversation_states[user_id] = {
        # ------------------------------------------
        # 目前流程狀態
        # ------------------------------------------
        "state": state,

        # ------------------------------------------
        # 推薦流程使用
        # ------------------------------------------
        "category": category,
        "spicy": spicy,
        "budget": budget,

        # ------------------------------------------
        # 模糊餐點搜尋 / 庫存流程使用
        # ------------------------------------------
        "pending_intent": pending_intent,
        "food_candidates": (
            food_candidates
            if food_candidates is not None
            else []
        ),
        "selected_food": selected_food,
    }

    return conversation_states[user_id]


# ==================================================
# 3. 更新其中一個或多個欄位
# ==================================================
def update_conversation_state(user_id: str, **kwargs):

    # --------------------------------------------------
    # 如果使用者目前沒有任何狀態
    # 先建立完整預設結構
    # --------------------------------------------------
    if user_id not in conversation_states:

        conversation_states[user_id] = {
            "state": None,

            # 推薦流程
            "category": None,
            "spicy": None,
            "budget": None,

            # 模糊餐點搜尋 / 庫存流程
            "pending_intent": None,
            "food_candidates": [],
            "selected_food": None,
        }

    # --------------------------------------------------
    # 更新指定欄位
    # --------------------------------------------------
    for key, value in kwargs.items():

        if key in conversation_states[user_id]:
            conversation_states[user_id][key] = value

    return conversation_states[user_id]


# ==================================================
# 4. 清除使用者對話狀態
# ==================================================
def clear_conversation_state(user_id: str):

    if user_id in conversation_states:
        del conversation_states[user_id]


# ==================================================
# 5. 判斷使用者是否正在進行對話流程
# ==================================================
def has_conversation_state(user_id: str) -> bool:

    return user_id in conversation_states