主題：書籍熱度即時追蹤與 LINE 智慧推薦系統
一、專題背景
    1.	動機
        o	網路書店排行榜瞬息萬變，讀者難即時掌握熱門書籍動態。
        o	LINE 使用者習慣對話介面，若能結合自然語言查詢，將大幅提升使用者體驗。
    2.	目標
        o	自動爬取「博客來」每日書籍排行榜與分類統計，儲存並可視化。
        o	提供 Web 介面與 LINE Bot，讓使用者既能查表格，也能對話查詢與收藏。
二、功能
    1.	爬蟲與自動排程
        o	GitHub Actions每天自動執行 static.py。
    2.	資料生成
        o	產生 static.csv（當日 50 本書）、history.csv（保留七天）、category_log.csv（分類 Top 統計）。
    3.	圖表可視化
        o	六張圖：分類市占長條、價格箱型、價格散佈、分類變化折線、分類堆疊、書名常駐排行榜。
    4.	Flask 網站
        o	首頁（/）：導向並顯示上述六張圖表。
        o	當日排行榜（/static）：提供分類下拉篩選功能，隱藏重複分類欄。
        o	歷史排行榜（/history）：分頁顯示過去七天每日排行榜，每頁 50 本書。
    5.	LINE Bot
        o	「聊天」→ AI 回應（Gemini）。
        o	「書籍」→ 顯示指令列表。
        o	「新書排行」「分類排行榜」「分類 XXX」→ 對應查詢。
        o	「收藏 書名」「刪除收藏 書名」「我的收藏」→ 管理使用者收藏。
三、技術
    •	Python 生態：Requests、Pandas、Matplotlib、Flask、line-bot-sdk
    •	字型處理：Matplotlib 載入 fonts/NotoSansCJKtc-Regular.otf 以支援繁體中文
    •	自動化：GitHub Actions
    •	部署：Render（需 gunicorn、Procfile）自動部署＋休眠喚醒機制
    •	資料格式：CSV 儲存輕量資料流，SQLite/JSON 可擴展收藏管理
四、程式流程圖
  A[GitHub Actions 定時觸發] --> B[執行 static.py]
  B --> C[爬取博客來排行榜]
  C --> D[生成 static.csv / history.csv / category_log.csv]
  D --> E[Matplotlib 產生六張圖]
  E --> F[推送 CSV 圖檔至 GitHub]
  F --> G[Render 自動部署 Flask 應用]
  G --> H[使用者訪問網站 & LINE Bot 查詢]
五、成果
    •	數據＋圖表：每日自動更新資料、生成六張高品質繁中圖表
    •	Web 介面：可即時瀏覽當日排行榜與過去七日排行榜
    •	互動體驗：分類篩選、分頁切換、收藏功能
    •	LINE Bot：整合 AI 聊天、書籍查詢與收藏管理
六、參與哪些事務及貢獻
    •	撰寫 static.py（爬蟲、CSV 生成、圖表產生、字型註冊）
    •	設定 GitHub Actions workflow
    •	部署至 Render 並解決 Linux 中文字型問題
    •	開發 app.py 路由邏輯（分類篩選、歷史分頁）
    •	設計 templates/*.html 排版與分頁按鈕樣式
七、遇到哪些問題及如何解決
    1.	Matplotlib 找不到中文字型
        o	解決：將 Noto Sans CJK TC 字型檔放入專案，並用 font_manager.addfont() 註冊。
    2.	CSV 欄位有逗號導致解析錯誤
        o	解決：改用 csv.reader(..., quotechar='"') 或 pandas read_csv(..., quotechar='"')。`
    3.	分頁跳轉排版跑版
        o	解決：在 CSS 加 table-layout: fixed; word-break: break-all;，並包裹 .table-wrapper { overflow-x: auto; }。
八、心得感想
    •	整合能力提升：從爬蟲→資料處理→視覺化→Web 開發→LINE Bot→自動化部署，完整體驗「端到端」專案開發。
    •	跨領域學習：解決繁中字型、雲端部署串接各種技術難題。
    •	團隊協作：明確分工且互相 review，確保每個模組穩定運作。
    •	未來展望：期待加入互動式圖表、AI 推薦演算法，並優化使用者個性化體驗。