import requests
from bs4 import BeautifulSoup
import time
import random

# 使用一般 session，不用 requests_cache
session = requests.Session()

# 基本 headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.books.com.tw/",
    "Accept-Language": "zh-TW,zh;q=0.9"
}
session.headers.update(headers)

# 防止被封機制
def safe_sleep():
    t = random.uniform(3, 7)
    print(f"⏳ 等待 {t:.2f} 秒...")
    time.sleep(t)

# 分類抓取函式
def get_category(book_url, retries=3):
    for attempt in range(retries):
        try:
            safe_sleep()
            res = session.get(book_url, timeout=15)
            res.raise_for_status()
            html = res.text

            if "限制級商品" in html or "18歲以上會員" in html:
                return "限制級商品（需登入）"
            if "您的連線暫時異常" in html or "Connection is temporarily unavailable" in html:
                return "連線暫時異常"

            soup = BeautifulSoup(html, "html.parser")
            breadcrumb = soup.select("ul#breadcrumb-trail li a")
            if len(breadcrumb) >= 3:
                return breadcrumb[2].text.strip()
            else:
                return "未知分類"
        except Exception as e:
            time.sleep(60)
    return "分類讀取失敗"

# 先測試個別連結是否分類正確
print(get_category("https://www.books.com.tw/products/0011016503?loc=P_0001_015"))
print(get_category("https://www.books.com.tw/products/0011015621?loc=P_0001_016"))

category_count = {}

# 抓排行榜頁
url = "https://www.books.com.tw/web/sys_tdrntb/books/"
res = session.get(url)
soup = BeautifulSoup(res.text, "html.parser")
books = soup.select("li.item")

# 開始爬蟲
seen_links = set()
idx = 1
error_count = 0

import csv

# 建立一個清單來存每本書的資料
book_data = []

for book in books[23:73]:
    title_tag = book.select_one("h4 > a")
    if not title_tag:
        continue

    original_link = title_tag["href"]
    book_id = original_link.split("/products/")[-1].split("?")[0]
    link = f"https://www.books.com.tw/products/{book_id}/{idx}"

    if link in seen_links:
        continue
    seen_links.add(link)

    title = title_tag.text.strip()
    author_tag = book.select_one("ul.msg li:nth-of-type(1) a")
    author = author_tag.text.strip() if author_tag else "未知作者"

    price_tag = book.select_one("ul.msg li.price_a")
    price = "未知價格"
    if price_tag:
        price_text = price_tag.get_text(strip=True)
        if "元" in price_text:
            price = price_text.split("元")[0].split("折")[-1] + "元"

    category = get_category(link)

    if category not in category_count:
        category_count[category] = 1
    else:
        category_count[category] += 1

    if "異常" in category or "失敗" in category:
        error_count += 1
    else:
        error_count = 0

    if error_count >= 1:
        print("⚠️ 連續出錯超過 5 次，暫停 60 秒...")
        time.sleep(60)
        error_count = 0
        category = get_category(link)

    print(f"{idx}. 書名: {title}")
    print(f"    連結: {link}")
    print(f"    作者: {author}")
    print(f"    價格: {price}")
    print(f"    分類: {category}")
    idx += 1

    # 把這筆資料加入 list
    book_data.append([title, author, price, category, link])

# 寫入 CSV 檔案
with open("static.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["書名", "作者", "價格", "分類", "連結"])
    writer.writerows(book_data)


print("\n📊 分類統計結果（依出現次數排序）：")
for cat, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
    print(f"分類「{cat}」出現次數：{count}")

import pandas as pd
import csv
from datetime import datetime
import pytz

# 讀取 static.csv（你的爬蟲輸出）
df = pd.read_csv("static.csv")

# 統計分類出現次數
category_count = df["分類"].value_counts().sort_values(ascending=False)


# 設定時區為台灣
tz = pytz.timezone("Asia/Taipei")
# 取得當前時間
now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# 組合一列：時間 + Top 分類(次數)
row = [now] + [f"{cat}({count})" for cat, count in category_count.items()]

# 檢查欄位長度是否要更新（避免欄位不足）
csv_file = "category_log.csv"
try:
    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
except FileNotFoundError:
    header = ["時間"]
if len(row) > len(header):
    header = ["時間"] + [f"Top{i}" for i in range(1, len(row))]

# 寫入資料（附加）
with open(csv_file, "a", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    # 如果是空檔案，補寫欄位
    if f.tell() == 0:
        writer.writerow(header)
    writer.writerow(row)

print("✅ 已從 static.csv 統計分類並寫入 category_log.csv")

import csv

csv_file = "category_log.csv"

try:
    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

        if not rows:
            print("❌ 檔案是空的")
        else:
            print("📋 category_log.csv 內容如下：\n")
            for row in rows:
                print(" ｜ ".join(row))

except FileNotFoundError:
    print("❌ 找不到檔案 category_log.csv")
except Exception as e:
    print("❌ 發生錯誤：", e)