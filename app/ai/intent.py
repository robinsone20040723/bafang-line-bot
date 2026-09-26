import re


def detect_intent(message: str) -> str:
    """
    根據使用者輸入文字判斷意圖。
    """

    message = message.strip()

    if not message:
        return "unknown"

    # ==================================================
    # 1. 庫存查詢
    # ==================================================
    inventory_keywords = [
        # 明確庫存用語
        "庫存",
        "有貨",
        "缺貨",
        "賣完",
        "售完",
        "剩多少",

        # 詢問是否還有
        "還有嗎",
        "還有沒有",
        "還有",
        "有沒有",

        # 自然語言購買可用性
        "買得到嗎",
        "買得到",
        "買的到嗎",
        "買的到",
        "還買得到嗎",
        "還買得到",
        "還買的到嗎",
        "還買的到",

        # 是否仍有販售
        "還有賣嗎",
        "還有賣",
        "有在賣嗎",
        "有在賣",
    ]

    if any(keyword in message for keyword in inventory_keywords):
        return "inventory_query"

    # ==================================================
    # 2. 餐點推薦
    # ==================================================
    recommendation_keywords = [
        "推薦",
        "推薦一下",
        "有什麼推薦",
        "幫我推薦",
        "幫我選",
        "吃什麼好",
        "不知道吃什麼",
        "不知道要吃什麼",
        "不知道怎麼選",
        "不知道要怎麼選",
        "不知道選什麼",
        "想吃點東西",
        "有什麼適合",
        "適合我的",
        "肚子餓",
    ]

    if any(keyword in message for keyword in recommendation_keywords):
        return "recommendation"

    # ==================================================
    # 3. 總金額計算
    # ==================================================
    has_quantity = re.search(
        r"(?:\d+|[零一二兩三四五六七八九十百]+)\s*(顆|份|杯|碗|盒|袋)",
        message
    )

    calculation_keywords = [
        "多少錢",
        "多少元",
        "總共",
        "總價",
        "合計",
        "多少",
        "幫我算",
        "算一下"
    ]

    if has_quantity and any(
        keyword in message
        for keyword in calculation_keywords
    ):
        return "price_calculation"

    # ==================================================
    # 4. 單品價格查詢
    # ==================================================
    price_keywords = [
        "多少錢",
        "價格",
        "多少元",
        "幾塊",
        "價錢"
    ]

    if any(keyword in message for keyword in price_keywords):
        return "price_query"

# ==================================================
# 5. 分店資訊
# ==================================================
    restaurant_keywords = [
        # 分店列表
        "有哪些店",
        "有哪些分店",
        "有什麼店",
        "有什麼分店",
        "哪幾間店",
        "哪幾間分店",
        "分店有哪些",

        # 地址 / 位置
        "地址",
        "在哪裡",
        "位置",
        "怎麼去",

        # 電話
        "電話",
        "電話多少",
        "電話是幾號",

        # 營業時間
        "營業時間",
        "幾點開",
        "幾點關",
        "開到幾點",
        "營業到幾點",
        "幾點打烊",

        # 一般分店詢問
        "分店"
    ]

    if any(
        keyword in message
        for keyword in restaurant_keywords
    ):
        return "restaurant_info"

    # ==================================================
    # 6. 分類查詢
    # ==================================================
    category_names = [
        "牛肉產品系列",
        "牛肉產品",
        "鍋貼",
        "水餃",
        "湯餃",
        "乾麵",
        "湯麵",
        "抄手",
        "湯品",
        "小菜",
        "飲品",
        "飲料",
        "生鮮冷凍",
        "冷凍食品",
        "麵"
    ]

    category_query_keywords = [
        "有什麼",
        "有哪些",
        "有那些",
        "有哪一些",
        "有哪幾種",
        "賣什麼",
        "可以吃什麼"
    ]

    has_category = any(
        category in message
        for category in category_names
    )

    has_category_question = any(
        keyword in message
        for keyword in category_query_keywords
    )

    if has_category and has_category_question:
        return "category_query"

    # 支援「鍋貼有哪些」、「水餃有什麼」這類句型
    if has_category and (
        "有哪些" in message
        or "有什麼" in message
        or "有那些" in message
    ):
        return "category_query"

    # ==================================================
    # 7. 菜單查詢
    # ==================================================
    menu_keywords = [
        "菜單",
        "有什麼可以吃",
        "有什麼餐點",
        "全部餐點",
        "完整菜單"
    ]

    if any(keyword in message for keyword in menu_keywords):
        return "menu_query"

    # ==================================================
    # 8. 一般聊天
    # ==================================================
    chat_keywords = [
        # 問候
        "你好",
        "哈囉",
        "嗨",
        "hello",
        "hi",

        # 感謝
        "謝謝",
        "感謝",

        # 告別
        "掰掰",
        "拜拜",
        "再見",
        "bye",

        # 詢問 Chatbot 功能
        "你可以幫我做什麼",
        "可以幫我做什麼",
        "你能幫我做什麼",
        "能幫我做什麼",
        "你會什麼",
        "你能做什麼",
        "可以做什麼",
        "有什麼功能"
    ]

    if any(
        keyword in message.lower()
        for keyword in chat_keywords
    ):
        return "general_chat"

    # ==================================================
    # 9. 無法辨識
    # ==================================================
    return "unknown"