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
import re
# 建立一個清單來存每本書的資料
book_data = []

# 23 - 73
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

    if author == "未知作者":
        # 從詳細頁抓出版社替代作者
        safe_sleep()
        try:
            detail_res = session.get(link, timeout=15)
            detail_res.raise_for_status()
            detail_soup = BeautifulSoup(detail_res.text, "html.parser")

            publisher = "未知出版社"
            meta_tag = detail_soup.select_one("meta[name=description]")
            if meta_tag and "出版社：" in meta_tag["content"]:
                desc = meta_tag["content"]
                match = re.search(r"出版社：(.+?)，", desc)
                if match:
                    publisher = match.group(1).strip()

            author = f"（出版社：{publisher}）"
        except Exception as e:
            print(f"⚠️ 詳細頁抓出版社失敗：{e}")
            author = "未知作者"

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

from datetime import datetime, timedelta
import pytz

# 設定時區為台灣
tz = pytz.timezone("Asia/Taipei")
now = datetime.now(tz).date()
'''+ timedelta(days=1)'''
now_str = now.strftime("%Y-%m-%d")

# 寫入 CSV 檔案（接續寫入）
with open("static.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    
    # 每次都寫入時間列，標示資料批次開始
    writer.writerow([now_str])

    # 寫入欄位標題
    writer.writerow(["書名", "作者", "價格", "分類", "連結"])
    
    # 寫入資料
    writer.writerows(book_data)


print("\n📊 分類統計結果（依出現次數排序）：")
for cat, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
    print(f"分類「{cat}」出現次數：{count}")

# 讀取 history.csv 舊資料
import pandas as pd
import os

history_file = "history.csv"
sections = []  # 每天一區塊：[date_string, [rows...]]
if os.path.exists(history_file):
    with open(history_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        section = []
        section_date = None
        for row in reader:
            if not row:
                continue
            if len(row) == 1:
                try:
                    # 嘗試解析成日期（確保真的是日期格式）
                    parsed_date = datetime.strptime(row[0], "%Y-%m-%d").date()
                    if section_date and section:
                        sections.append((section_date, section))
                    section_date = str(parsed_date)
                    section = []
                    continue
                except:
                    pass  # 如果不是日期就跳過，繼續累加資料
            section.append(row)
        if section_date and section:
            sections.append((section_date, section))

# 3. 新增今天的新資料（格式同上）
new_section_rows = [["書名", "作者", "價格", "分類", "連結"]] + book_data
sections.append((str(now), new_section_rows))

# 4. 保留最新 7 天
# 排序並去重（後面的會蓋掉前面的）
latest = {}
for date_str, rows in sections:
    latest[date_str] = rows
# 保留最近 7 天
sorted_dates = sorted(latest.keys(), reverse=True)[:7]
sections = [(d, latest[d]) for d in sorted_dates]

# 5. 寫入 history.csv
with open(history_file, "w", newline='', encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    for date_str, rows in reversed(sections):  # 由舊到新
        writer.writerow([date_str])
        writer.writerows(rows)

rows = []
with open("static.csv", "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split(",")
        if len(parts) == 5:  # 只保留正確的資料列
            rows.append(parts)

# 直接從本次爬下來的資料建立 DataFrame
df = pd.DataFrame(book_data, columns=["書名", "作者", "價格", "分類", "連結"])

# 統計分類
category_count = df["分類"].value_counts().sort_values(ascending=False)

# 組合一列：時間 + Top 分類(次數)
row = [now] + [f"{cat}({count})" for cat, count in category_count.items()]

# 補齊最多 20 欄（如果不足 20 種分類）
while len(row) < 21:
    row.append("")

# 設定欄位名稱
header = ["時間"] + [f"Top{i}" for i in range(1, 21)]

# 寫入 category_log.csv（附加）
with open("category_log.csv", "a", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    # 如果是空檔案就補寫欄位
    if f.tell() == 0:
        writer.writerow(header)
    writer.writerow(row)

print("✅ 已從 static.csv 統計分類並寫入 category_log.csv")

# print category_log.csv
try:
    with open("category_log.csv", newline='', encoding='utf-8-sig') as f:
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