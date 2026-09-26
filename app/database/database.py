import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error


# 讀取專案根目錄的 .env
load_dotenv()


def get_db_connection():
    """
    建立並回傳 MySQL 資料庫連線。
    """

    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )

        return connection

    except Error as error:
        print(f"MySQL 連線失敗：{error}")
        return None