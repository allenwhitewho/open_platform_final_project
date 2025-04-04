import requests
import csv
import time
import random

# 自訂搜尋關鍵字，例如可以改成 "python", "小說", "AI", "travel" 等等
query = "python"

# Google Books API 的查詢網址
url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=20"

# 模擬人類行為，避免 API 請求過快被封
def safe_sleep():
    t = random.uniform(1, 3)
    print(f"⏳ 等待 {t:.2f} 秒...")
    time.sleep(t)

# 發送 API 請求
safe_sleep()
res = requests.get(url)

# 檢查回應是否正常
if res.status_code != 200:
    print("❌ 無法取得資料，HTTP 錯誤碼：", res.status_code)
    exit()

# 將 API 回應轉為 JSON 格式
data = res.json()

# 建立清單存放書籍資料
book_data = []

# 逐筆取出書籍資訊
for item in data.get("items", []):
    info = item.get("volumeInfo", {})
    title = info.get("title", "無標題")
    authors = ", ".join(info.get("authors", ["未知作者"]))
    categories = ", ".join(info.get("categories", ["未知分類"]))
    link = info.get("infoLink", "無連結")
    
    print(f"📘 書名: {title}")
    print(f"    作者: {authors}")
    print(f"    分類: {categories}")
    print(f"    連結: {link}")
    print()

    book_data.append([title, authors, categories, link])

# 將結果寫入 CSV 檔案
with open("api.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["書名", "作者", "分類", "連結"])
    writer.writerows(book_data)

print("✅ API 書籍資料已成功寫入 api.csv")