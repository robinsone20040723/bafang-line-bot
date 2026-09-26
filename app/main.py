from fastapi import FastAPI
from app.routers.menu import router as menu_router
from app.routers.inventory import router as inventory_router
from app.routers.restaurant import router as restaurant_router
from app.routers.order import router as order_router
from app.routers.line import router as line_router

app = FastAPI(
    title="八方雲集 LINE Chatbot API",
    description="斗六八方雲集 LINE 聊天機器人後端系統",
    version="1.0.0"
)
app.include_router(menu_router)
app.include_router(inventory_router)
app.include_router(restaurant_router)
app.include_router(order_router)
app.include_router(line_router)


@app.get("/")
def home():
    return {
        "message": "八方雲集 LINE Chatbot 啟動成功"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "bafang-line-bot"
    }