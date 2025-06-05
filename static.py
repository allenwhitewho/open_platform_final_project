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
url = "https://www.books.com.tw/web/sys_newtopb/books/"
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

import pandas as pd

# 步驟 1：讀取 history.csv，整理成每天的 dataframe 清單
history_file = "history.csv"
sections = []

with open(history_file, newline='', encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    current_date = None
    current_rows = []

    for row in reader:
        if not row:
            continue
        if len(row) == 1 and row[0].count("-") == 2:  # 偵測日期
            if current_date and current_rows:
                df = pd.DataFrame(current_rows[1:], columns=current_rows[0])  # 跳過欄位列
                sections.append((current_date, df))
            current_date = row[0].strip()
            current_rows = []
        else:
            current_rows.append(row)
    if current_date and current_rows:
        df = pd.DataFrame(current_rows[1:], columns=current_rows[0])
        sections.append((current_date, df))

# 保留最近 7 天
sections = sorted(sections, key=lambda x: x[0], reverse=True)[:7]
sections = list(reversed(sections))  # 由舊到新

# 步驟 2：寫入 category_log.csv（分類 Top 出現次數）
header = ["時間"] + [f"Top{i}" for i in range(1, 21)]
csv_file = "category_log.csv"
with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for date_str, df in sections:
        category_count = df["分類"].value_counts().sort_values(ascending=False)
        row = [date_str] + [f"{cat}({count})" for cat, count in category_count.items()]
        while len(row) < 21:
            row.append("")
        writer.writerow(row)

print("✅ 已從 history.csv 統計近七天分類，寫入 category_log.csv（無重複）")

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


import matplotlib.pyplot as plt
from matplotlib import font_manager

# 1. 指定字型檔相對路徑（以專案根目錄下的 fonts 資料夾為例）
font_path = "font/NotoSansCJKtc-Regular.otf"

# 2. 告訴 matplotlib 先把這支字型加進系統可用字型列表
font_manager.fontManager.addfont(font_path)

# 3. 取得字型名稱（family name），讓 Matplotlib 了解我們要使用哪個 family
prop = font_manager.FontProperties(fname=font_path)
font_name = prop.get_name()

# 4. 全域設定，將字型家族設成我們剛才註冊的那一支
plt.rcParams['font.family'] = font_name
plt.rcParams['axes.unicode_minus'] = False  # 負號正常顯示

# 統計分類數量
category_counts = df["分類"].value_counts()

# 畫出長條圖
plt.figure(figsize=(12, 6))
category_counts.plot(kind='bar')
plt.title("各類別書籍數量（市占圖）", fontsize=16)
plt.xlabel("分類", fontsize=12)
plt.ylabel("書籍數量", fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig("images/category_distribution_bar.png")  # 用不同檔名儲存
plt.show()
plt.close()


# —————— 1. 價格欄位文字轉數值 ——————
# 假設價格格式像 "250元"、"90元"、"未知價格"，先去掉「元」再轉 int，不可轉則設 NaN
def parse_price(x):
    try:
        return int(x.replace("元", ""))
    except:
        return None

df["價格_數值"] = df["價格"].apply(parse_price)
df = df.dropna(subset=["價格_數值"])  # 去掉無法轉成數字的列

# —————— 2. 箱型圖：各分類價格分布 ——————
plt.rcParams["font.family"] = font_name
plt.rcParams["axes.unicode_minus"] = False

# 使用 boxplot，各分類價格分布
df.boxplot(column="價格_數值", by="分類", rot=45, grid=False, showfliers=False)
plt.title("各分類書籍價格箱型圖", fontsize=16)
plt.suptitle("")  # 移除 pandas 自帶的副標題
plt.xlabel("分類", fontsize=12)
plt.ylabel("價格（元）", fontsize=12)
plt.tight_layout()
plt.savefig("images/category_price_boxplot.png")  # 用不同檔名儲存
plt.show()
plt.close()


import seaborn as sns

plt.figure(figsize=(14, 6))
sns.stripplot(x="分類", y="價格_數值", data=df, jitter=True)
plt.xticks(rotation=45)
plt.title("各分類書籍價格散佈圖")
plt.xlabel("分類")
plt.ylabel("價格（元）")
plt.tight_layout()
plt.savefig("images/category_price_scatter.png")  # 用不同檔名儲存
plt.show()
plt.close()


# 1. 先讀取 history.csv，用 csv.reader 處理欄位內可能有逗號的狀況
history_file = "history.csv"
records = []  # 用來收集 (日期, 分類) 資料

with open(history_file, encoding="utf-8-sig") as f:
    reader = csv.reader(f, quotechar='"')
    current_date = None

    for row in reader:
        if not row:
            continue
        # 如果這一列只有一個欄位，且符合日期格式 (YYYY-MM-DD)，就視為「新的一天開始」
        if len(row) == 1 and row[0].count("-") == 2:
            current_date = row[0].strip()
            continue

        # 跳過標題列（第一個欄位為「書名」）
        if current_date and row[0] != "書名":
            # row 大小應該恰好是 5 欄：書名, 作者, 價格, 分類, 連結
            if len(row) == 5:
                _, _, _, category, _ = row
                records.append((current_date, category))

# 2. 把 records 轉成 DataFrame
df_records = pd.DataFrame(records, columns=["日期", "分類"])

# 3. 計算每一天、每個分類的出現次數 (書量)
df_count = df_records.groupby(["日期", "分類"]).size().reset_index(name="書量")

# 4. 轉成 pivot table：index=分類，columns=日期，values=書量
df_pivot = df_count.pivot(index="分類", columns="日期", values="書量").fillna(0).astype(int)

# 5. 建立繪圖：每個分類一條線
plt.figure(figsize=(12, 6))

# a. 取出所有日期，按照「從最早到最新」排序
dates = sorted(df_pivot.columns.tolist())

# b. 取出所有分類，依 pivot table 的 index（排序後）
categories = df_pivot.index.tolist()

# c. 選擇一個足夠多色的 colormap；tab20 最多 20 種不同顏色
cmap = plt.get_cmap("tab20")
colors = [cmap(i) for i in range(len(categories))]

# d. 逐分類畫折線，並對應一個唯一的顏色
for idx, cat in enumerate(categories):
    y_values = [df_pivot.loc[cat, d] for d in dates]
    plt.plot(
        dates,
        y_values,
        marker="o",
        label=cat,
        color=colors[idx % len(colors)]  # 如果分類 > 20，則循環使用顏色
    )

# 6. 加上標題、座標標籤、圖例
plt.title("各分類市占變化折線圖（7天）", fontsize=16)
plt.xlabel("日期", fontsize=12)
plt.ylabel("書籍數量", fontsize=12)
plt.xticks(rotation=45, ha="right")
plt.legend(title="分類", bbox_to_anchor=(1.05, 1), loc="upper left")
plt.tight_layout()

# 7. 儲存成 PNG 圖檔
plt.savefig("images/category_trend_line.png")
plt.show()
plt.close()


# ————————————————
# 1. 用 csv.reader 讀取 category_log.csv，避免欄位內的逗號導致切錯
# ————————————————
category_log = "category_log.csv"
top_records = []  # 會收集 (日期, 分類, 次數)

with open(category_log, encoding="utf-8-sig") as f:
    reader = csv.reader(f, quotechar='"')
    for row in reader:
        if not row:
            continue
        # 第一個元素是「日期」，後面每個元素長得像 "分類名(次數)"
        date = row[0].strip()
        for item in row[1:]:
            item = item.strip()
            # 確定 item 形如 "某分類(3)"
            if "(" in item and ")" in item:
                cat = item.split("(")[0]
                try:
                    n = int(item.split("(")[1].replace(")", ""))
                except:
                    n = 0
                top_records.append((date, cat, n))

# 轉成 DataFrame
df_top = pd.DataFrame(top_records, columns=["日期", "分類", "次數"])

# ————————————————
# 2. pivot 出想要的 DataFrame：index=日期、columns=分類、values=次數
# ————————————————
df_top_pivot = df_top.pivot(index="日期", columns="分類", values="次數").fillna(0).astype(int)

# 按照日期排序（如果需要）
df_top_pivot = df_top_pivot.sort_index()

# ————————————————
# 3. 畫堆疊柱狀圖，指定一個大色盤 (colormap) 讓顏色不重複
# ————————————————
# 使用 tab20 colormap（最多支援 20 種不同顏色），如果分類超過 20，會自動循環配色
df_top_pivot.plot(
    kind="bar",
    stacked=True,
    colormap="tab20",
    figsize=(12, 6)
)

plt.title("Top 分類每日進榜次數堆疊圖", fontsize=16)
plt.xlabel("日期", fontsize=12)
plt.ylabel("分類進榜次數", fontsize=12)
plt.xticks(rotation=45, ha="right")
plt.legend(title="分類", bbox_to_anchor=(1.05, 1), loc="upper left")
plt.tight_layout()

# 存檔
plt.savefig("images/category_top10_stacked.png")
plt.show()
plt.close()


from collections import Counter
from matplotlib.ticker import MaxNLocator

# Step 1: 讀入 history.csv
history_file = "history.csv"
top10_books = []

with open(history_file, encoding="utf-8-sig") as f:
    current_date = None
    current_books = []
    for line in f:
        line = line.strip()
        if not line:
            continue
        if "," not in line:
            # 遇到「只有日期」的行，就把前一天的前10本加進 list
            if current_date and current_books:
                top10_books += current_books[:10]
            current_date = line.strip()
            current_books = []
        else:
            parts = line.split(",")
            title = parts[0]
            if title != "書名":  # 排除表頭
                current_books.append(title)


    # 最後一個日期的書也要加
    if current_date and current_books:
        top10_books += current_books[:10]

# Step 2: 統計書名出現次數
counter = Counter(top10_books)

# 過濾出「出現次數 ≥ 2 次」的書
filtered_common = [(t, c) for t, c in counter.most_common() if c >= 2]

# 如果沒有任何書出現次數 ≥ 2，提示使用者
if not filtered_common:
    print("❗目前沒有任何書在 7 天內出現超過一次，無法畫出常駐排行榜。")
else:
    # 取前 10 名（如果大於 10）
    top_common = filtered_common[:10]

    # Step 3: 繪圖
    titles = [item[0] for item in top_common]
    counts = [item[1] for item in top_common]

    plt.figure(figsize=(12, 6))
    plt.barh(titles[::-1], counts[::-1])
    plt.title("Top 常駐書名排行榜（出現次數大於2）")
    plt.xlabel("出現次數")
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()
    plt.savefig("images/title_top10_bar.png")
    plt.show()
    plt.close()