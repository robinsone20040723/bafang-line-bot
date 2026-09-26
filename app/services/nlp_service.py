import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel


# ==================================================
# 載入 .env
# ==================================================

load_dotenv()


# ==================================================
# 系統支援的 Intent
# ==================================================

SUPPORTED_INTENTS = [
    "inventory_query",
    "recommendation",
    "category_query",
    "price_query",
    "price_calculation",
    "restaurant_info",
    "menu_query",
    "general_chat",
    "unknown"
]


# ==================================================
# Structured Output 資料模型
# ==================================================

class AIEntities(BaseModel):
    food_name: str | None
    category: str | None
    restaurant_name: str | None
    quantity: int | None
    budget: float | None
    spicy: bool | None


class AINLPResult(BaseModel):

    intent: Literal[
        "inventory_query",
        "recommendation",
        "category_query",
        "price_query",
        "price_calculation",
        "restaurant_info",
        "menu_query",
        "general_chat",
        "unknown"
    ]

    entities: AIEntities


# ==================================================
# 建立空白 Entities
# ==================================================

def create_empty_entities():

    return {
        "food_name": None,
        "category": None,
        "restaurant_name": None,
        "quantity": None,
        "budget": None,
        "spicy": None
    }


# ==================================================
# 驗證 NLP 結果
# ==================================================

def validate_nlp_result(result: dict):

    if not isinstance(result, dict):

        return {
            "intent": "unknown",
            "entities": create_empty_entities()
        }

    intent = result.get(
        "intent",
        "unknown"
    )

    if intent not in SUPPORTED_INTENTS:
        intent = "unknown"

    received_entities = result.get(
        "entities",
        {}
    )

    if not isinstance(
        received_entities,
        dict
    ):
        received_entities = {}

    entities = create_empty_entities()

    for key in entities:

        if key in received_entities:
            entities[key] = received_entities[key]

    return {
        "intent": intent,
        "entities": entities
    }


# ==================================================
# Gemini System Prompt
# ==================================================

SYSTEM_PROMPT = """
你是「八方雲集斗六地區 LINE 點餐 Chatbot」的語意分析器。

你的工作只有兩件事：

1. 判斷使用者的 Intent
2. 擷取 Entities

你不是負責直接回答問題的聊天機器人。

禁止自行提供：
- 餐點價格
- 即時庫存
- 店家地址
- 電話
- 營業時間
- 不存在的餐點

真正的餐點、價格、庫存與分店資料，
之後會由 Python 查詢 MySQL。


========================
支援的 Intent
========================

inventory_query
使用者詢問餐點是否有貨、還有沒有、能不能買到。

recommendation
使用者不知道吃什麼，或希望系統推薦餐點。

category_query
使用者詢問某一類型有哪些餐點。

price_query
使用者詢問單一餐點的價格。

price_calculation
使用者要求計算多個餐點的總價格。

restaurant_info
使用者詢問分店地址、電話、營業時間。

menu_query
使用者詢問完整菜單或一般菜單內容。

general_chat
一般聊天，例如你好、謝謝、哈囉。

unknown
無法判斷使用者意圖。


========================
Entities
========================

food_name
餐點名稱，例如：
招牌鍋貼
玉米鍋貼
韓式辣味水餃

category
餐點分類。

restaurant_name
分店名稱。

quantity
數量。

budget
使用者預算。

spicy
辣度需求。


========================
辣度規則
========================

「想吃辣」
「要辣」
「辣的」
→ spicy = true

「不要辣」
「不吃辣」
「不能吃辣」
「不敢吃辣」
「不太敢吃辣」
→ spicy = false

沒有提到辣度：
→ spicy = null

「都可以」
「辣不辣都可以」
→ spicy = null


========================
分類
========================

系統可能使用的分類：

牛肉產品系列
鍋貼
水餃
湯餃
乾麵
湯麵
麵
抄手
湯品
小菜
飲品
生鮮冷凍

如果使用者泛指：

「麵」
「麵類」

請使用：

category = 麵


========================
分店名稱
========================

斗六中山店
斗六文化店
雲林斗六店
斗六鎮北店
斗六石榴店


常見說法：

「中山店」
「中山那間」
→ 斗六中山店

「文化店」
「文化那間」
→ 斗六文化店

「鎮北店」
「鎮北那間」
→ 斗六鎮北店

「石榴店」
「石榴那間」
→ 斗六石榴店

「斗六店」
→ 雲林斗六店


========================
重要判斷規則
========================

例如：

「我肚子餓了，完全不知道要吃什麼」

intent = recommendation


「我不太敢吃辣，想吃水餃，一百塊以內有什麼推薦」

intent = recommendation
category = 水餃
budget = 100
spicy = false


「中山那間今天開到幾點」

intent = restaurant_info
restaurant_name = 斗六中山店


「玉米鍋貼現在還買得到嗎」

intent = inventory_query
food_name = 玉米鍋貼


「招牌鍋貼一顆多少錢」

intent = price_query
food_name = 招牌鍋貼


「你們有什麼麵」

intent = category_query
category = 麵


「哈囉你好」

intent = general_chat


如果沒有辨識到某個 Entity，
該欄位請保持 null。

不要為了填滿欄位而猜測。
"""


# ==================================================
# Gemini Client
# ==================================================

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==================================================
# Gemini AI 語意辨識
# ==================================================

def analyze_message_with_ai(message: str):

    message = message.strip()

    # --------------------------------------------------
    # 1. 空訊息
    # --------------------------------------------------

    if not message:

        return {
            "intent": "unknown",
            "entities": create_empty_entities()
        }

    # --------------------------------------------------
    # 2. 呼叫 Gemini Interactions API
    # --------------------------------------------------

    try:

        # 把 System Prompt 和使用者訊息一起交給 Gemini
        full_prompt = f"""
{SYSTEM_PROMPT}

========================
現在要分析的使用者訊息
========================

{message}
"""

        interaction = client.interactions.create(
            model="gemini-3.6-flash",

            input=full_prompt,

            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": AINLPResult.model_json_schema()
            }
        )

        # --------------------------------------------------
        # 3. 取得 Gemini JSON 輸出
        # --------------------------------------------------

        response_text = interaction.output_text

        if not response_text:

            return {
                "intent": "unknown",
                "entities": create_empty_entities()
            }

        # --------------------------------------------------
        # 4. JSON → Pydantic
        # --------------------------------------------------

        parsed_result = AINLPResult.model_validate_json(
            response_text
        )

        # --------------------------------------------------
        # 5. Pydantic → Python Dictionary
        # --------------------------------------------------

        result = parsed_result.model_dump()

        # --------------------------------------------------
        # 6. 最後再經過自己的驗證
        # --------------------------------------------------

        return validate_nlp_result(
            result
        )

    except Exception as error:

        print(
            f"Gemini 語意辨識發生錯誤：{error}"
        )

        return {
            "intent": "unknown",
            "entities": create_empty_entities()
        }