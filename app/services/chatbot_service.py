import math
import re
import time

from app.database.database import get_db_connection
from app.ai.intent import detect_intent
from app.ai.entity import (
    extract_order_items,
    extract_food_name,
    extract_restaurant_name,
    extract_category,
    extract_budget,
    extract_spicy,
)
from app.services.menu_service import (
    get_food_price,
    get_foods_by_category,
    get_foods_by_keyword,
    get_recommended_foods,
    search_food_names,
)
from app.services.inventory_service import get_inventory
from app.services.restaurant_service import (
    get_restaurant_info,
    get_all_restaurants,
)
from app.services.conversation_service import (
    get_conversation_state,
    set_conversation_state,
    update_conversation_state,
    clear_conversation_state,
)
from app.services.nlp_service import analyze_message_with_ai


def format_time(time_value):
    if time_value is None:
        return ""
    total_seconds = int(time_value.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def format_price(price):
    price = float(price)
    if price.is_integer():
        return str(int(price))
    return str(price)


def empty_ai_entities():
    return {
        "food_name": None,
        "category": None,
        "restaurant_name": None,
        "quantity": None,
        "budget": None,
        "spicy": None,
    }


def safe_ai_analysis(message):
    try:
        result = analyze_message_with_ai(message)
        if not isinstance(result, dict):
            return {
                "intent": "unknown",
                "entities": empty_ai_entities(),
            }

        intent = result.get("intent", "unknown")
        entities = result.get("entities")
        if not isinstance(entities, dict):
            entities = empty_ai_entities()

        normalized = empty_ai_entities()
        for key in normalized:
            normalized[key] = entities.get(key)

        return {
            "intent": intent,
            "entities": normalized,
        }
    except Exception as error:
        print(f"Gemini 分析失敗：{error}")
        return {
            "intent": "unknown",
            "entities": empty_ai_entities(),
        }


def filter_recommendations(category, spicy=None, budget=None, limit=3):
    if category in ("麵", "全部"):
        foods = get_foods_by_keyword("麵" if category == "麵" else "")
        filtered_foods = []
        for food in foods:
            price = float(food["price"])
            if budget is not None and price > float(budget):
                continue
            if spicy is not None:
                food_is_spicy = bool(food["is_spicy"])
                if food_is_spicy != spicy:
                    continue
            filtered_foods.append(food)
        return filtered_foods[:limit]

    return get_recommended_foods(
        category_name=category,
        spicy=spicy,
        budget=budget,
        limit=limit,
    )


def build_recommendation_response(recommended_foods, category, spicy=None, budget=None):
    if not recommended_foods:
        return {
            "success": False,
            "intent": "recommendation",
            "message": "目前找不到符合你條件的餐點，可以調整分類、辣度或預算再試試看。",
        }

    food_messages = [
        f'{food["food_name"]} {format_price(food["price"])}元'
        for food in recommended_foods
    ]

    return {
        "success": True,
        "intent": "recommendation",
        "category": category,
        "spicy": spicy,
        "budget": budget,
        "recommendations": recommended_foods,
        "message": "依照你的需求，我推薦：\n" + "\n".join(food_messages),
    }


def handle_recommendation_conversation(message, user_id, conversation):
    state = conversation["state"]

    if state == "waiting_category":
        category = extract_category(message)
        if any(kw in message for kw in ("都可以", "都行", "隨便")):
            category = "全部"

        if category is None:
            return {
                "success": False,
                "intent": "recommendation",
                "message": "我目前還不知道你想吃哪一類，可以告訴我鍋貼、水餃、麵類，或直接說「都可以」。",
            }

        update_conversation_state(user_id=user_id, category=category, state="waiting_spicy")
        return {
            "success": True,
            "intent": "recommendation",
            "message": "好的，那你想吃辣的，還是不辣的呢？",
        }

    if state == "waiting_spicy":
        if any(kw in message for kw in ("不要辣", "不辣", "不能吃辣", "不吃辣", "不敢吃辣")):
            spicy = False
        elif any(kw in message for kw in ("要辣", "吃辣", "辣的")) or message == "辣":
            spicy = True
        elif any(kw in message for kw in ("都可以", "都行", "沒差", "隨便")):
            spicy = None
        else:
            return {
                "success": False,
                "intent": "recommendation",
                "message": "請告訴我你想吃辣的、不辣的，或都可以。",
            }

        update_conversation_state(user_id=user_id, spicy=spicy, state="waiting_budget")
        return {
            "success": True,
            "intent": "recommendation",
            "message": "了解，那你的預算大約多少元呢？",
        }

    if state == "waiting_budget":
        budget_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if any(kw in message for kw in ("都可以", "不限", "沒差", "隨便")):
            budget = None
        elif budget_match:
            budget = float(budget_match.group(1))
        else:
            return {
                "success": False,
                "intent": "recommendation",
                "message": "請告訴我大約多少元，例如「100元」。",
            }

        update_conversation_state(user_id=user_id, budget=budget, state="ready_to_recommend")
        conversation = get_conversation_state(user_id)
        recommended_foods = filter_recommendations(
            category=conversation["category"],
            spicy=conversation["spicy"],
            budget=conversation["budget"],
            limit=3,
        )
        clear_conversation_state(user_id)

        return build_recommendation_response(
            recommended_foods,
            conversation["category"],
            conversation["spicy"],
            conversation["budget"],
        )

    return None


def analyze_user_message(message):
    intent = detect_intent(message)
    entities = empty_ai_entities()

    entities["food_name"] = extract_food_name(message)
    entities["restaurant_name"] = extract_restaurant_name(message)
    entities["category"] = extract_category(message)
    entities["budget"] = extract_budget(message)
    entities["spicy"] = extract_spicy(message)

    if intent == "unknown":
        ai_result = safe_ai_analysis(message)
        if ai_result["intent"] != "unknown":
            intent = ai_result["intent"]
        for key, value in ai_result["entities"].items():
            if entities.get(key) is None and value is not None:
                entities[key] = value
        return intent, entities

    need_ai = False
    if intent == "price_query" and entities["food_name"] is None:
        need_ai = True
    elif intent == "category_query" and entities["category"] is None:
        need_ai = True

    if need_ai:
        ai_result = safe_ai_analysis(message)
        for key, value in ai_result["entities"].items():
            if entities.get(key) is None and value is not None:
                entities[key] = value

    return intent, entities


def handle_message(message: str, user_id: str = "TEST_USER"):
    start_time = time.perf_counter()
    message = message.strip()

    if not message:
        return {
            "success": False,
            "intent": "unknown",
            "message": "請輸入您想詢問的內容。",
        }

    conversation = get_conversation_state(user_id)

    if conversation is not None:
        current_state = conversation.get("state")

        interrupt_intent = detect_intent(message)

        strong_interrupt = False

        if interrupt_intent == "price_calculation":
            strong_interrupt = bool(extract_order_items(message))

        elif interrupt_intent == "price_query":
            strong_interrupt = (
                extract_food_name(message) is not None
                and any(kw in message for kw in ("多少錢", "價格", "價錢", "多少"))
            )

        elif interrupt_intent == "inventory_query":
            strong_interrupt = any(
                kw in message
                for kw in (
                    "庫存",
                    "有貨",
                    "缺貨",
                    "還有嗎",
                    "還有沒有",
                    "買得到嗎",
                    "買得到",
                    "賣完",
                    "剩多少",
                )
            )

        elif interrupt_intent == "restaurant_info":
            strong_interrupt = any(
                kw in message
                for kw in (
                    "有哪些分店",
                    "有那些分店",
                    "有哪些店",
                    "有那些店",
                    "有哪些門市",
                    "地址",
                    "電話",
                    "營業時間",
                    "幾點開",
                    "幾點關",
                    "開到幾點",
                    "在哪裡",
                    "位置",
                )
            )

        elif interrupt_intent == "category_query":
            strong_interrupt = any(
                kw in message
                for kw in (
                    "有哪些",
                    "有那些",
                    "種類",
                    "有什麼",
                )
            )

        elif interrupt_intent == "recommendation":
            strong_interrupt = any(
                kw in message
                for kw in (
                    "推薦",
                    "不知道吃什麼",
                    "吃什麼好",
                    "幫我選",
                    "幫我推薦",
                )
            )

        elif interrupt_intent == "menu_query":
            strong_interrupt = any(
                kw in message
                for kw in (
                    "菜單",
                    "menu",
                )
            )

        elif interrupt_intent == "general_chat":
            strong_interrupt = any(
                kw in message
                for kw in (
                    "你好",
                    "哈囉",
                    "嗨",
                    "hello",
                    "hi",
                    "謝謝",
                    "感謝",
                    "掰掰",
                    "再見",
                    "拜拜",
                    "bye",
                )
            )

        if strong_interrupt:
            clear_conversation_state(user_id)
            conversation = None

    if conversation is not None:
        if conversation is not None:
            if conversation["state"] == "waiting_food_selection":
                food_candidates = conversation.get("food_candidates", [])
                pending_intent = conversation.get("pending_intent")
                selected_food = None

                for food_name in food_candidates:
                    if food_name in message:
                        selected_food = food_name
                        break

                if selected_food is None:
                    number_match = re.fullmatch(r"\s*(\d+)\s*", message)
                    if number_match:
                        selected_index = int(number_match.group(1)) - 1
                        if 0 <= selected_index < len(food_candidates):
                            selected_food = food_candidates[selected_index]

                if selected_food is not None:
                    if pending_intent == "inventory_query":
                        conversation["selected_food"] = selected_food
                        update_conversation_state(user_id, state="waiting_restaurant_selection")
                        return {
                            "success": True,
                            "intent": "inventory_query",
                            "selected_food": selected_food,
                            "state": "waiting_restaurant_selection",
                            "message": f"好的，你選擇的是「{selected_food}」。請告訴我你想查詢哪一間分店的庫存。",
                        }

                candidate_text = "\n".join(
                    f"{index}. {food_name}"
                    for index, food_name in enumerate(food_candidates, start=1)
                )
                return {
                    "success": False,
                    "intent": pending_intent,
                    "state": "waiting_food_selection",
                    "message": f"我還無法確認你選的是哪一個餐點。\n請從以下餐點中選擇：\n{candidate_text}",
                }

            if conversation["state"] == "waiting_restaurant_selection":
                selected_food = conversation.get("selected_food")
                if selected_food is None:
                    clear_conversation_state(user_id)
                    return {
                        "success": False,
                        "intent": "inventory_query",
                        "message": "剛才的餐點資料沒有保存成功，請再告訴我你想查哪一個餐點的庫存。",
                    }

                restaurant_name = extract_restaurant_name(message)
                if restaurant_name is None:
                    restaurants = get_all_restaurants()
                    if restaurants:
                        restaurant_names = [r["restaurant_name"] for r in restaurants]
                        restaurant_text = "\n".join(
                            f"{idx}. {name}" for idx, name in enumerate(restaurant_names, start=1)
                        )
                        return {
                            "success": False,
                            "intent": "inventory_query",
                            "state": "waiting_restaurant_selection",
                            "message": f"你目前要查的是「{selected_food}」。\n請告訴我你想查哪一間分店：\n{restaurant_text}",
                        }
                    return {
                        "success": False,
                        "intent": "inventory_query",
                        "state": "waiting_restaurant_selection",
                        "message": f"你目前要查的是「{selected_food}」。請告訴我你想查詢哪一間分店。",
                    }

                inventory = get_inventory(restaurant_name, selected_food)
                if inventory is None:
                    return {
                        "success": False,
                        "intent": "inventory_query",
                        "state": "waiting_restaurant_selection",
                        "message": f"目前查不到{restaurant_name}的{selected_food}庫存資料。你可以再告訴我其他分店。",
                    }

                stock_quantity = inventory["stock_quantity"]
                stock_status = inventory["stock_status"]
                full_restaurant_name = inventory["restaurant_name"]
                unit = inventory["unit"]

                clear_conversation_state(user_id)

                if stock_status == "available" and stock_quantity is not None and stock_quantity > 0:
                    reply_message = f"{full_restaurant_name}的{selected_food}目前有貨，庫存約{stock_quantity}{unit}。"
                else:
                    reply_message = f"{full_restaurant_name}的{selected_food}目前缺貨。"

                return {
                    "success": True,
                    "intent": "inventory_query",
                    "restaurant_name": full_restaurant_name,
                    "food_name": selected_food,
                    "stock_quantity": stock_quantity,
                    "stock_status": stock_status,
                    "message": reply_message,
                }

            conversation_result = handle_recommendation_conversation(message, user_id, conversation)
            if conversation_result is not None:
                return conversation_result

    nlp_start = time.perf_counter()
    intent, entities = analyze_user_message(message)
    nlp_end = time.perf_counter()
    print(f"[效能] NLP 分析：{nlp_end - nlp_start:.4f} 秒")

    if intent == "price_calculation":
        items = extract_order_items(message)
        if not items:
            return {
                "success": False,
                "intent": intent,
                "message": "我知道你想計算餐點金額，但目前無法辨識餐點名稱或數量。",
            }

        connection = get_db_connection()
        if connection is None or not connection.is_connected():
            return {
                "success": False,
                "intent": intent,
                "message": "資料庫連線失敗。",
            }

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            result_items = []
            total_amount = 0.0

            sql = """
                SELECT m.food_id, m.food_name, mo.option_id, mo.option_name, mo.unit, mo.price
                FROM menu AS m
                JOIN menu_option AS mo ON m.food_id = mo.food_id
                WHERE m.food_name = %s AND m.is_available = TRUE AND mo.is_active = TRUE
                ORDER BY mo.option_id
                LIMIT 1
            """

            for item in items:
                cursor.execute(sql, (item["food_name"],))
                product = cursor.fetchone()
                if product is None:
                    return {
                        "success": False,
                        "intent": intent,
                        "message": f"找不到「{item['food_name']}」這個餐點。",
                    }

                unit_price = float(product["price"])
                subtotal = unit_price * item["quantity"]
                total_amount += subtotal

                result_items.append({
                    "food_name": product["food_name"],
                    "quantity": item["quantity"],
                    "unit": product["unit"],
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                })

            rounded_total = math.ceil(total_amount)
            detail_messages = [
                f"{item['food_name']}{item['quantity']}{item['unit']}{item['subtotal']:g}元"
                for item in result_items
            ]

            return {
                "success": True,
                "intent": intent,
                "items": result_items,
                "original_total": total_amount,
                "total_amount": rounded_total,
                "message": "，".join(detail_messages) + f"，總金額為{rounded_total}元。",
            }
        except Exception as error:
            return {
                "success": False,
                "intent": intent,
                "message": f"計算餐點金額時發生錯誤：{error}",
            }
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    if intent == "price_query":
        food_name = entities["food_name"]
        if food_name is None:
            return {
                "success": False,
                "intent": intent,
                "message": "請告訴我您想查詢哪一個餐點的價格。",
            }

        product = get_food_price(food_name)
        if product is None:
            return {
                "success": False,
                "intent": intent,
                "message": f"目前查不到「{food_name}」的價格資料。",
            }

        price = float(product["price"])
        unit = product["unit"]
        return {
            "success": True,
            "intent": intent,
            "food_name": product["food_name"],
            "price": price,
            "unit": unit,
            "message": f"{product['food_name']}每{unit}{format_price(price)}元。",
        }

    if intent == "inventory_query":
        food_name = entities["food_name"]
        restaurant_name = entities["restaurant_name"]

        if food_name is None:
            return {
                "success": False,
                "intent": intent,
                "message": "請告訴我您想查詢哪一個餐點的庫存。",
            }

        matched_foods = search_food_names(food_name)
        if not matched_foods:
            return {
                "success": False,
                "intent": intent,
                "message": f"目前找不到與「{food_name}」相關的餐點。",
            }

        if len(matched_foods) > 1:
            food_candidates = [food["food_name"] for food in matched_foods]
            set_conversation_state(
                user_id=user_id,
                state="waiting_food_selection",
                pending_intent="inventory_query",
                food_candidates=food_candidates,
            )
            candidate_text = "\n".join(
                f"{idx}. {name}" for idx, name in enumerate(food_candidates, start=1)
            )
            return {
                "success": True,
                "intent": intent,
                "state": "waiting_food_selection",
                "food_candidates": food_candidates,
                "message": f"我找到幾個與「{food_name}」相關的餐點：\n{candidate_text}\n請告訴我你想查哪一個餐點。",
            }

        food_name = matched_foods[0]["food_name"]

        if restaurant_name is None:
            set_conversation_state(
                user_id=user_id,
                state="waiting_restaurant_selection",
                pending_intent="inventory_query",
                food_candidates=[],
            )
            conversation = get_conversation_state(user_id)
            if conversation is not None:
                conversation["selected_food"] = food_name
            return {
                "success": True,
                "intent": intent,
                "food_name": food_name,
                "state": "waiting_restaurant_selection",
                "message": f"好的，你想查「{food_name}」。請告訴我您想查詢哪一間分店的庫存。",
            }

        inventory = get_inventory(restaurant_name, food_name)
        if inventory is None:
            return {
                "success": False,
                "intent": intent,
                "message": f"目前查不到{restaurant_name}的{food_name}庫存資料。",
            }

        stock_quantity = inventory["stock_quantity"]
        stock_status = inventory["stock_status"]
        full_restaurant_name = inventory["restaurant_name"]
        unit = inventory["unit"]

        if stock_status == "available" and stock_quantity is not None and stock_quantity > 0:
            reply_message = f"{full_restaurant_name}的{food_name}目前有貨，庫存約{stock_quantity}{unit}。"
        else:
            reply_message = f"{full_restaurant_name}的{food_name}目前缺貨。"

        return {
            "success": True,
            "intent": intent,
            "restaurant_name": full_restaurant_name,
            "food_name": food_name,
            "stock_quantity": stock_quantity,
            "stock_status": stock_status,
            "message": reply_message,
        }

    if intent == "restaurant_info":
        restaurant_name = entities["restaurant_name"]
        restaurant_list_keywords = [
            "有哪些分店", "有那些分店", "有哪些店", "有那些店",
            "分店有哪些", "分店有什麼", "有哪些門市", "有那些門市", "門市有哪些"
        ]

        if any(keyword in message for keyword in restaurant_list_keywords):
            restaurants = get_all_restaurants()
            if not restaurants:
                return {
                    "success": False,
                    "intent": intent,
                    "message": "目前查不到分店資料。",
                }
            restaurant_names = [r["restaurant_name"] for r in restaurants]
            reply_message = (
                "目前斗六共有以下分店：\n"
                + "\n".join(f"{idx}. {name}" for idx, name in enumerate(restaurant_names, start=1))
                + "\n\n您可以直接告訴我想查哪一間分店。"
            )
            return {
                "success": True,
                "intent": intent,
                "restaurants": restaurants,
                "message": reply_message,
            }

        if restaurant_name is None:
            return {
                "success": False,
                "intent": intent,
                "message": "請告訴我您想查詢哪一間分店。\n例如：中山店地址、文化店電話、石榴店營業時間。",
            }

        restaurant = get_restaurant_info(restaurant_name)
        if restaurant is None:
            return {
                "success": False,
                "intent": intent,
                "message": f"目前查不到{restaurant_name}的分店資料。",
            }

        full_restaurant_name = restaurant["restaurant_name"]
        address = restaurant["address"]
        phone = restaurant["phone"]
        hours_text = "、".join(
            f"{format_time(p['open_time'])}～{format_time(p['close_time'])}"
            for p in restaurant["business_hours"]
        )

        if any(kw in message for kw in ("地址", "在哪裡", "位置")):
            reply_message = f"{full_restaurant_name}的地址是{address}。"
        elif any(kw in message for kw in ("電話", "電話多少", "電話是幾號")):
            reply_message = f"{full_restaurant_name}的電話是{phone}。"
        elif any(kw in message for kw in ("營業時間", "幾點開", "幾點關", "開到幾點", "營業到幾點", "幾點打烊")):
            reply_message = f"{full_restaurant_name}的營業時間為{hours_text}。"
        else:
            reply_message = f"{full_restaurant_name}\n地址：{address}\n電話：{phone}\n營業時間：{hours_text}。"

        return {
            "success": True,
            "intent": intent,
            "restaurant_name": full_restaurant_name,
            "address": address,
            "phone": phone,
            "business_hours": hours_text,
            "message": reply_message,
        }

    if intent == "recommendation":
        category = entities["category"]
        budget = entities["budget"]
        spicy = entities["spicy"]

        if category is not None and (budget is not None or spicy is not None):
            recommended_foods = filter_recommendations(
                category=category,
                spicy=spicy,
                budget=budget,
                limit=3,
            )
            return build_recommendation_response(recommended_foods, category, spicy, budget)

        if category is not None:
            foods = get_foods_by_keyword("麵") if category == "麵" else get_foods_by_category(category)
            if not foods:
                return {
                    "success": False,
                    "intent": intent,
                    "message": f"目前找不到適合推薦的「{category}」餐點。",
                }

            recommended_foods = foods[:3]
            food_messages = [f'{food["food_name"]} {format_price(food["price"])}元' for food in recommended_foods]
            return {
                "success": True,
                "intent": intent,
                "category": category,
                "recommendations": recommended_foods,
                "message": f"如果你想吃「{category}」，我可以推薦：\n" + "\n".join(food_messages),
            }

        set_conversation_state(user_id=user_id, state="waiting_category")
        return {
            "success": True,
            "intent": intent,
            "message": "可以，我可以幫你推薦！你比較想吃鍋貼、水餃、麵類，還是都可以呢？",
        }

    if intent == "category_query":
        category = entities["category"]
        if category is None:
            return {
                "success": False,
                "intent": intent,
                "message": "請告訴我您想查詢哪一類餐點。",
            }

        foods = get_foods_by_keyword("麵") if category == "麵" else get_foods_by_category(category)
        if not foods:
            return {
                "success": False,
                "intent": intent,
                "category": category,
                "message": f"目前查不到「{category}」的餐點資料。",
            }

        food_messages = [f'{food["food_name"]} {format_price(food["price"])}元' for food in foods]
        return {
            "success": True,
            "intent": intent,
            "category": category,
            "count": len(foods),
            "foods": foods,
            "message": f"目前「{category}」的餐點有：\n" + "\n".join(food_messages),
        }

    if intent == "menu_query":
        foods = get_foods_by_keyword("")
        if not foods:
            return {
                "success": False,
                "intent": intent,
                "message": "目前查不到菜單資料。",
            }

        food_messages = [f'{food["food_name"]} {format_price(food["price"])}元' for food in foods]
        return {
            "success": True,
            "intent": intent,
            "count": len(foods),
            "foods": foods,
            "message": "目前菜單餐點有：\n" + "\n".join(food_messages),
        }

    if intent == "general_chat":
        lower_message = message.lower()
        if any(kw in message for kw in ("你好", "哈囉", "嗨")) or any(kw in lower_message for kw in ("hello", "hi")):
            return {
                "success": True,
                "intent": intent,
                "message": "哈囉！歡迎使用八方雲集斗六地區點餐助手。\n你可以問我餐點、價格、庫存、分店資訊，或是不知道吃什麼時請我幫你推薦！",
            }

        if any(kw in message for kw in ("謝謝", "感謝")) or "thank" in lower_message:
            return {
                "success": True,
                "intent": intent,
                "message": "不客氣！如果還想查餐點、價格、庫存，或需要我幫你推薦，都可以繼續問我。",
            }

        if any(kw in message for kw in ("掰掰", "再見", "拜拜")) or "bye" in lower_message:
            return {
                "success": True,
                "intent": intent,
                "message": "掰掰！下次想吃八方雲集再來找我。",
            }

        return {
            "success": True,
            "intent": intent,
            "message": "我可以協助你查詢八方雲集斗六地區的餐點、價格、庫存、分店資訊，也可以依照你的喜好和預算推薦餐點喔！",
        }

    return {
        "success": False,
        "intent": "unknown",
        "message": "我目前還不太確定你的意思。你可以問我餐點價格、庫存、菜單、分店資訊，或請我推薦餐點。",
    }