import re
from app.services.menu_service import get_all_food_names

# ==================================================
# 1. 擷取「餐點名稱 + 數量」
# ==================================================
def extract_order_items(message: str) -> list[dict]:
    """
    從使用者訊息中擷取多筆餐點與數量。

    餐點名稱直接從 MySQL 取得。

    支援：
    1. 阿拉伯數字
       7顆玉米鍋貼
       1碗酸辣湯
       2份紅燒牛肉麵

    2. 常用中文數字
       十顆韓式辣味鍋貼
       一碗酸辣湯
       兩份紅燒牛肉麵

    支援購買單位：
    - 顆
    - 份
    - 碗
    - 杯
    """

    message = message.strip()

    if not message:
        return []

    # ==================================================
    # 1. 中文數字轉整數
    # ==================================================
    chinese_digit_map = {
        "零": 0,
        "一": 1,
        "二": 2,
        "兩": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

    def chinese_number_to_int(text: str):
        """
        將專題常見的中文數量轉成整數。

        支援：
        一～九
        十
        十一～十九
        二十、二十一...
        九十九
        """

        # 如果本來就是阿拉伯數字
        if text.isdigit():
            return int(text)

        # 單一中文字
        if text in chinese_digit_map:
            return chinese_digit_map[text]

        # 十
        if text == "十":
            return 10

        # 十一～十九
        if text.startswith("十"):
            ones = text[1:]

            if ones in chinese_digit_map:
                return 10 + chinese_digit_map[ones]

        # 二十～九十九
        if "十" in text:
            parts = text.split("十")

            tens_text = parts[0]
            ones_text = parts[1]

            if tens_text in chinese_digit_map:
                tens = chinese_digit_map[tens_text] * 10

                if ones_text == "":
                    return tens

                if ones_text in chinese_digit_map:
                    return tens + chinese_digit_map[ones_text]

        return None

    # ==================================================
    # 2. 從 MySQL 取得所有有效餐點
    # ==================================================
    food_names = get_all_food_names()

    if not food_names:
        return []

    # 長名稱優先，避免短名稱先被匹配
    sorted_food_names = sorted(
        food_names,
        key=len,
        reverse=True
    )

    matched_items = []

    # ==================================================
    # 3. 找出每一個餐點與數量
    # ==================================================
    for food_name in sorted_food_names:

        escaped_food_name = re.escape(food_name)

        # 支援：
        # 7顆玉米鍋貼
        # 10 顆 玉米鍋貼
        # 十顆韓式辣味鍋貼
        # 一碗酸辣湯
        # 兩份紅燒牛肉麵
        pattern = (
            rf"(\d+|[零一二兩三四五六七八九十]+)"
            rf"\s*(?:顆|份|碗|杯)\s*"
            rf"{escaped_food_name}"
        )

        match = re.search(pattern, message)

        if match:

            quantity_text = match.group(1)

            quantity = chinese_number_to_int(
                quantity_text
            )

            if quantity is None:
                continue

            matched_items.append({
                "food_name": food_name,
                "quantity": quantity,
                "_position": match.start()
            })

    # ==================================================
    # 4. 按照使用者原句順序排列
    # ==================================================
    matched_items.sort(
        key=lambda item: item["_position"]
    )

    # ==================================================
    # 5. 移除內部排序欄位
    # ==================================================
    items = []

    for item in matched_items:
        items.append({
            "food_name": item["food_name"],
            "quantity": item["quantity"]
        })

    return items


# ==================================================
# 2. 擷取「餐點名稱」
# ==================================================
def extract_food_name(message: str):
    """
    從使用者訊息中擷取餐點名稱。

    餐點名稱不再寫死在 Python 中，
    而是直接從 MySQL 的 menu 資料表取得。

    例如：
    玉米鍋貼多少錢
    → 玉米鍋貼

    我想問招牌水餃還有嗎
    → 招牌水餃

    鮮蝦生水餃多少錢
    → 鮮蝦生水餃

    如果沒有找到餐點：
    → None
    """

    message = message.strip()

    if not message:
        return None

    # ==================================================
    # 從 MySQL 取得所有有效餐點名稱
    # ==================================================
    food_aliases = {
            "玉米口味": "玉米",
            "玉米的": "玉米",
            "鮮蝦口味": "鮮蝦",
            "鮮蝦的": "鮮蝦",
            "招牌口味": "招牌",
            "招牌的": "招牌",
            "韓式辣味": "韓式辣味",
            "韓式": "韓式辣味",
        }
    
    for alias, normalized_name in food_aliases.items():
        if alias in message:
            return normalized_name
        
    food_names = get_all_food_names()

    if not food_names:
        return None

    # ==================================================
    # 長名稱優先判斷
    #
    # 例如資料庫同時存在：
    #
    # 香濃豆漿
    # 香濃豆漿（無加糖）
    # 香濃豆漿（無加糖）家庭號
    #
    # 必須先檢查最長名稱，
    # 避免「香濃豆漿」提早匹配。
    # ==================================================
    sorted_food_names = sorted(
        food_names,
        key=len,
        reverse=True
    )

    for food_name in sorted_food_names:
        if food_name in message:
            return food_name

    return None


# ==================================================
# 3. 擷取「分店名稱」
# ==================================================
def extract_restaurant_name(message: str):
    """
    從使用者訊息中擷取八方雲集斗六地區分店。

    支援較自然的說法：

    中山店
    中山那間
    中山那家
    中山路那間

    文化店
    文化那間

    鎮北店
    鎮北那間

    石榴店
    石榴那間
    """

    message = message.strip()

    if not message:
        return None

    restaurant_aliases = {

        # ---------- 斗六中山店 ----------
        "八方雲集斗六中山店": "斗六中山店",
        "斗六中山店": "斗六中山店",
        "中山路那間": "斗六中山店",
        "中山路那家": "斗六中山店",
        "中山那間": "斗六中山店",
        "中山那家": "斗六中山店",
        "中山店": "斗六中山店",

        # ---------- 斗六文化店 ----------
        "八方雲集斗六文化店": "斗六文化店",
        "斗六文化店": "斗六文化店",
        "文化路那間": "斗六文化店",
        "文化路那家": "斗六文化店",
        "文化那間": "斗六文化店",
        "文化那家": "斗六文化店",
        "文化店": "斗六文化店",

        # ---------- 雲林斗六店 ----------
        "八方雲集雲林斗六店": "雲林斗六店",
        "雲林斗六店": "雲林斗六店",
        "雲林路那間": "雲林斗六店",
        "雲林路那家": "雲林斗六店",
        "斗六店": "雲林斗六店",

        # ---------- 斗六鎮北店 ----------
        "八方雲集斗六鎮北店": "斗六鎮北店",
        "斗六鎮北店": "斗六鎮北店",
        "鎮北路那間": "斗六鎮北店",
        "鎮北路那家": "斗六鎮北店",
        "鎮北那間": "斗六鎮北店",
        "鎮北那家": "斗六鎮北店",
        "鎮北店": "斗六鎮北店",

        # ---------- 斗六石榴店 ----------
        "八方雲集斗六石榴店": "斗六石榴店",
        "斗六石榴店": "斗六石榴店",
        "石榴路那間": "斗六石榴店",
        "石榴路那家": "斗六石榴店",
        "石榴那間": "斗六石榴店",
        "石榴那家": "斗六石榴店",
        "石榴店": "斗六石榴店"
    }

    # 長名稱優先，避免：
    # 雲林斗六店 → 被「斗六店」提前匹配
    sorted_aliases = sorted(
        restaurant_aliases.keys(),
        key=len,
        reverse=True
    )

    for alias in sorted_aliases:
        if alias in message:
            return restaurant_aliases[alias]

    return None


# ==================================================
# 4. 擷取「餐點分類」
# ==================================================
def extract_category(message: str):
    """
    擷取使用者想查詢或推薦的餐點分類。

    注意：
    「麵」是虛擬分類，
    後續由 menu_service 使用關鍵字搜尋。
    """

    message = message.strip()

    if not message:
        return None

    category_aliases = {

        # ---------- 牛肉 ----------
        "牛肉產品系列": "牛肉產品系列",
        "牛肉產品": "牛肉產品系列",

        # ---------- 生鮮冷凍 ----------
        "生鮮冷凍": "生鮮冷凍",
        "冷凍食品": "生鮮冷凍",
        "冷凍": "生鮮冷凍",
        "生鮮": "生鮮冷凍",

        # ---------- 其他分類 ----------
        "鍋貼": "鍋貼",
        "水餃": "水餃",
        "湯餃": "湯餃",
        "乾麵": "乾麵",
        "湯麵": "湯麵",
        "抄手": "抄手",
        "湯品": "湯品",
        "小菜": "小菜",
        "飲品": "飲品",
        "飲料": "飲品",
        "牛肉": "牛肉產品系列"
    }

    sorted_aliases = sorted(
        category_aliases.keys(),
        key=len,
        reverse=True
    )

    for alias in sorted_aliases:
        if alias in message:
            return category_aliases[alias]

    # ==================================================
    # 「麵」不是資料庫中的單一分類
    #
    # 例如：
    # 有什麼麵
    # 想吃麵
    #
    # 回傳虛擬分類「麵」
    # chatbot_service 再使用 keyword 查詢。
    # ==================================================
    if "麵" in message:
        return "麵"

    # 單獨說「湯」時統一視為湯品
    if "湯" in message:
        return "湯品"

    return None


# ==================================================
# 5. 擷取「預算」
# ==================================================
def extract_budget(message: str):
    """
    從自然語言中擷取預算。

    支援：

    預算50元
    預算 100
    100元以內
    100元以下
    100塊以內
    只有80塊
    我有80元
    最多100元

    回傳：
    float

    例如：
    100.0
    """

    message = message.strip()

    if not message:
        return None

    patterns = [
        # 預算100元
        r"預算\s*(?:大概|約|是|有)?\s*(\d+(?:\.\d+)?)\s*(?:元|塊)?",

        # 100元以內 / 100塊以下
        r"(\d+(?:\.\d+)?)\s*(?:元|塊)\s*(?:以內|以下|內)",

        # 最多100元
        r"最多\s*(\d+(?:\.\d+)?)\s*(?:元|塊)?",

        # 只有80塊
        r"只有\s*(\d+(?:\.\d+)?)\s*(?:元|塊)",

        # 我有80元
        r"我有\s*(\d+(?:\.\d+)?)\s*(?:元|塊)"
    ]

    for pattern in patterns:
        match = re.search(pattern, message)

        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                return None

    # ==================================================
    # 常見中文數字預算
    #
    # 目前先支援專題最常見的整百說法。
    # ==================================================
    chinese_budget_map = {
        "五十": 50.0,
        "一百": 100.0,
        "兩百": 200.0,
        "二百": 200.0,
        "三百": 300.0,
        "四百": 400.0,
        "五百": 500.0
    }

    budget_context_keywords = [
        "預算",
        "以內",
        "以下",
        "最多",
        "只有"
    ]

    has_budget_context = any(
        keyword in message
        for keyword in budget_context_keywords
    )

    if has_budget_context:
        for chinese_number, value in chinese_budget_map.items():
            if chinese_number in message:
                return value

    return None


# ==================================================
# 6. 擷取「辣度偏好」
# ==================================================
def extract_spicy(message: str):
    """
    判斷使用者是否想吃辣。

    回傳：
    True  → 想吃辣
    False → 不想吃辣
    None  → 沒有提到辣度，或辣不辣都可以

    判斷順序非常重要：
    1. 中立
    2. 不辣
    3. 辣
    4. 明確指定辣味餐點

    必須先判斷否定句，
    避免「不辣」因為包含「辣」而被誤判成 True。
    """

    message = message.strip()

    if not message:
        return None

    # ==================================================
    # 1. 沒有特定辣度偏好
    # ==================================================
    neutral_keywords = [
        "辣不辣都可以",
        "辣不辣都行",
        "辣度都可以",
        "辣度都行",
        "都可以",
        "都行"
    ]

    if any(keyword in message for keyword in neutral_keywords):
        return None

    # ==================================================
    # 2. 不吃辣 / 不想要辣
    #
    # 必須優先於 spicy_keywords 判斷
    # ==================================================
    non_spicy_keywords = [
        "不太敢吃辣",
        "不敢吃辣",
        "不能吃辣",
        "不太能吃辣",
        "不吃辣",
        "不要辣",
        "不想吃辣",
        "不喜歡辣",
        "怕辣",
        "不辣",
        "不要太辣",
        "不能太辣"
    ]

    if any(keyword in message for keyword in non_spicy_keywords):
        return False

    # ==================================================
    # 3. 想吃辣
    # ==================================================
    spicy_keywords = [
        "想吃辣",
        "我要辣",
        "要辣的",
        "吃辣的",
        "喜歡辣",
        "可以辣",
        "辣一點",
        "辣的"
    ]

    if any(keyword in message for keyword in spicy_keywords):
        return True

    # ==================================================
    # 4. 使用者直接指定辣味餐點
    #
    # 例如：
    # 韓式辣味水餃
    # 麻辣牛肉麵
    # 紹辣乾麵
    # ==================================================
    spicy_food_keywords = [
        "韓式辣味",
        "麻辣",
        "紹辣"
    ]

    if any(keyword in message for keyword in spicy_food_keywords):
        return True

    return None