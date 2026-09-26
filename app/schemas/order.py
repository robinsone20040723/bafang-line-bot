from pydantic import BaseModel, Field


# 使用 option_id 計算訂單時，每一個商品的資料格式
class OrderItemRequest(BaseModel):
    option_id: int
    quantity: int = Field(gt=0)


# 使用 option_id 計算訂單的完整 Request
class CalculateOrderRequest(BaseModel):
    items: list[OrderItemRequest]


# 使用餐點名稱計算訂單時，每一個商品的資料格式
class OrderItemByName(BaseModel):
    food_name: str
    quantity: int = Field(gt=0)


# 使用餐點名稱計算訂單的完整 Request
class CalculateOrderByNameRequest(BaseModel):
    items: list[OrderItemByName]