import os
import json
import feedparser
import requests
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# ============ 配置 ============
STOCKS = {
    # 美股
    "NVDA": {"name": "NVIDIA", "market": "US", "sector": "芯片"},
    "AMD": {"name": "AMD", "market": "US", "sector": "芯片"},
    "MSFT": {"name": "Microsoft", "market": "US", "sector": "软件"},
    "GOOGL": {"name": "Alphabet", "market": "US", "sector": "互联网"},
    "AMZN": {"name": "Amazon", "market": "US", "sector": "互联网"},
    "META": {"name": "Meta", "market": "US", "sector": "互联网"},
    "TSLA": {"name": "Tesla", "market": "US", "sector": "AI/汽车"},
    "PLTR": {"name": "Palantir", "market": "US", "sector": "AI/数据"},
    "BABA": {"name": "阿里巴巴", "market": "US", "sector": "互联网"},
    # 港股
    "0700.HK": {"name": "腾讯控股", "market": "HK", "sector": "互联网"},
    "1810.HK": {"name": "小米集团", "market": "HK", "sector": "消费电子"},
    "9988.HK": {"name": "阿里巴巴-SW", "market": "HK", "sector": "互联网"},
    "0020.HK": {"name": "商汤-W", "market": "HK", "sector": "AI"},
    "2018.HK": {"name": "瑞声科技", "market": "HK", "sector": "硬件"},
    # A股
    "688981.SS": {"name": "中芯国际", "market": "CN", "sector": "芯片"},
    "688256.SS": {"name": "寒武纪", "market": "CN", "sector": "AI芯片"},
    "002230.SZ": {"name": "科大讯飞", "market": "CN", "sector": "AI语音"},
    "688041.SS": {"name": "海光信息", "market": "CN", "sector": "芯片"},
    "603019.SS": {"name": "中科曙光", "market": "CN", "sector": "算力"},
}

# 新闻过滤：黑名单关键词（标题或摘要出现这些词则过滤）
NEWS_BLACKLIST = [
    # 体育/足球
    "football", "soccer", "match", "game", "team", "player", "league", "fifa",
    "足球", "赛事", "比赛", "球队", "球员",
    # 娱乐/漫画
    "comic", "manga", "anime", "movie review", "film review",
    "漫画", "动画", "影视", "电影评论",
    # 政治（非科技类）
    "election", "vote", "campaign", "president",
    # 其他不相关
    "recipe", "cooking", "travel guide",
]

def is_relevant_news(title, summary=""):
    """检查新闻是否与 AI/科技相关（过滤黑名单）"""
    text = (title + " " + summary).lower()
    for kw in NEWS_BLACKLIST:
        if kw in text:
            return False
    return True


# RSS 新闻源（无需 API Key）
RSS_FEEDS = [
    # 中文媒体
    ("机器之心", "https://www.jiqizhixin.com/rss"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("36氪", "https://36kr.com/feed"),
    ("虎嗅", "https://www.huxiu.com/rss/0.xml"),
    ("很客公园", "https://www.geekpark.net/rss"),
    ("爱范儿", "https://www.ifanr.com/feed"),
    ("雷科技", "https://www.leiPhone.com/feed"),
    ("钛媒体", "http://www.tmtpost.com/rss.xml"),
    # 英文媒体
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
]

# 优先读环境变量， fallback 到本地配置文件
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
if not NEWS_API_KEY:
    _config_paths = [
        Path.home() / ".workbuddy" / "secrets" / "apis.json",
        Path.home() / ".workbuddy" / "secrets" / "notion.json",
    ]
    for _p in _config_paths:
        if _p.exists():
            try:
                _data = json.loads(_p.read_text(encoding="utf-8"))
                if "newsapi_key" in _data:
                    NEWS_API_KEY = _data["newsapi_key"]
                    break
            except Exception:
                pass


def get_stock_data():
    """获取股票数据"""
    data = []
    for ticker, info in STOCKS.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d", interval="1d")
            
            if hist.empty or len(hist) < 1:
                continue
                
            current_price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else current_price
            day_change = current_price - prev_close
            day_change_pct = (day_change / prev_close * 100) if prev_close else 0
            
            week_ago = hist["Close"].iloc[0] if len(hist) >= 1 else current_price
            week_change_pct = ((current_price - week_ago) / week_ago * 100) if week_ago else 0
            
            # 市值
            try:
                info_obj = stock.info
                market_cap = info_obj.get("marketCap", 0)
            except Exception:
                market_cap = 0
            
            data.append({
                "ticker": ticker,
                "name": info["name"],
                "market": info["market"],
                "sector": info["sector"],
                "price": round(current_price, 2),
                "prev_close": round(prev_close, 2),
                "change": round(day_change, 2),
                "change_pct": round(day_change_pct, 2),
                "week_change_pct": round(week_change_pct, 2),
                "market_cap": market_cap,
            })
        except Exception as e:
            print(f"[ERROR] {ticker}: {e}")
    
    # 按涨幅排序
    data.sort(key=lambda x: x["change_pct"], reverse=True)
    return data


def get_news_from_api():
    """通过 NewsAPI 获取新闻（中英文均抓取）"""
    if not NEWS_API_KEY:
        return []
    
    all_articles = []
    try:
        url = "https://newsapi.org/v2/everything"
        # 使用北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now_beijing = datetime.now(beijing_tz)
        yesterday = (now_beijing - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 英文新闻 - 优化搜索关键词，只在标题中搜索
        params_en = {
            "q": "AI OR artificial intelligence OR OpenAI OR ChatGPT OR LLM OR GPT OR Claude OR Gemini",
            "searchIn": "title,description",
            "from": yesterday,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 8,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(url, params=params_en, timeout=30)
        if resp.status_code == 200:
            articles = resp.json().get("articles", [])
            for a in articles:
                title = a["title"]
                summary = a.get("description", "") or ""
                # 过滤不相关新闻
                if not is_relevant_news(title, summary):
                    continue
                all_articles.append({
                    "title": title,
                    "summary": summary,
                    "url": a["url"],
                    "source": a["source"]["name"],
                    "tag": "AI新闻",
                })
        
        # 中文新闻（NewsAPI 支持 zh 语言参数）
        params_zh = {
            "q": "人工智能 OR AI OR 大模型 OR 深度学习 OR 机器学习",
            "searchIn": "title,description",
            "from": yesterday,
            "sortBy": "publishedAt",
            "language": "zh",
            "pageSize": 8,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(url, params=params_zh, timeout=30)
        if resp.status_code == 200:
            articles = resp.json().get("articles", [])
            for a in articles:
                title = a["title"]
                summary = a.get("description", "") or ""
                if not is_relevant_news(title, summary):
                    continue
                all_articles.append({
                    "title": title,
                    "summary": summary,
                    "url": a["url"],
                    "source": a["source"]["name"],
                    "tag": "AI新闻",
                })
    except Exception as e:
        print(f"[ERROR] NewsAPI: {e}")
    
    return all_articles[:10]  # 最多返回10条


def get_news_from_rss():
    """通过 RSS 获取新闻"""
    news = []
    for source_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:  # 每个源取3条候选，过滤后取2条
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                # 过滤不相关新闻
                if not is_relevant_news(title, summary):
                    continue
                # 清理HTML标签
                summary = summary.replace("<", "&lt;").replace(">", "&gt;")
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                
                link = entry.get("link", "")
                
                # 判断标签
                tag = "AI新闻"
                lower_title = title.lower()
                # 中文 + 英文关键词
                if any(k in title or k in lower_title for k in ["芯片", "半导体", "chip", "nvidia", "amd", "gpu", "英伟达", "英特尔", "高通"]):
                    tag = "芯片"
                elif any(k in title or k in lower_title for k in ["融资", "投资", "亿美元", "funding", "invest", "IPO", "上市", "估值"]):
                    tag = "融资"
                elif any(k in title or k in lower_title for k in ["模型", "大模型", "model", "gpt", "llm", "GPT", "Claude", "Gemini", "DeepSeek"]):
                    tag = "模型"
                elif any(k in title or k in lower_title for k in ["中国", "国产", "华为", "腾讯", "阿里", "百度", "字节", "china", "chinese", "domestic"]):
                    tag = "中国AI"
                elif any(k in title or k in lower_title for k in ["机器人", "具身", "robot", "人形"]):
                    tag = "机器人"
                
                news.append({
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "source": source_name,
                    "tag": tag,
                })
        except Exception as e:
            print(f"[ERROR] RSS {source_name}: {e}")
    
    # 去重并限制数量
    seen = set()
    unique_news = []
    for n in news:
        if n["title"] not in seen and n["title"]:
            seen.add(n["title"])
            unique_news.append(n)
    
    return unique_news[:8]


def get_news():
    """获取新闻：合并 API + RSS 结果"""
    api_news = get_news_from_api()
    rss_news = get_news_from_rss()
    # 合并去重
    seen = set()
    all_news = []
    for n in api_news + rss_news:
        if n["title"] not in seen and n["title"]:
            seen.add(n["title"])
            all_news.append(n)
    return all_news[:12]  # 最多12条


def format_market_cap(cap):
    if cap >= 1e12:
        return f"${cap/1e12:.1f}T"
    elif cap >= 1e9:
        return f"${cap/1e9:.0f}B"
    elif cap >= 1e6:
        return f"${cap/1e6:.0f}M"
    return "-"


def generate_html(stocks, news):
    """生成HTML早报"""
    # 使用北京时间 (UTC+8)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    date_str = now.strftime("%Y年%m月%d日")
    weekday_str = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    
    us_stocks = [s for s in stocks if s["market"] == "US"]
    hk_stocks = [s for s in stocks if s["market"] == "HK"]
    cn_stocks = [s for s in stocks if s["market"] == "CN"]
    
    # 市场统计
    all_changes = [s["change_pct"] for s in stocks]
    up_count = sum(1 for c in all_changes if c > 0)
    down_count = sum(1 for c in all_changes if c < 0)
    flat_count = sum(1 for c in all_changes if c == 0)
    top_gainer = max(stocks, key=lambda x: x["change_pct"]) if stocks else None
    
    def stock_rows(stock_list):
        rows = ""
        for s in stock_list:
            cls = "up" if s["change_pct"] > 0 else ("down" if s["change_pct"] < 0 else "flat")
            arrow = "▲" if s["change_pct"] > 0 else ("▼" if s["change_pct"] < 0 else "—")
            sign = "+" if s["change_pct"] > 0 else ""
            w_sign = "+" if s["week_change_pct"] > 0 else ""
            cap = format_market_cap(s["market_cap"])
            rows += f"""
                <tr>
                    <td>
                        <div style="display:flex;flex-direction:column;gap:2px">
                            <span style="font-size:15px;font-weight:700;color:#e2e8f0">{s["ticker"]}</span>
                            <span style="font-size:12px;color:#a8b4ff">{s["name"]}</span>
                            <span style="font-size:11px;color:#667eea;background:rgba(102,126,234,0.15);padding:2px 8px;border-radius:6px;width:fit-content">{s["sector"]}</span>
                        </div>
                    </td>
                    <td style="font-size:16px;font-weight:700;color:#e2e8f0">{s["price"]:.2f}</td>
                    <td style="font-size:13px;font-weight:600" class="{cls}">
                        <span style="font-size:11px">{arrow}</span> {sign}{s["change_pct"]:.2f}%
                    </td>
                    <td style="font-size:12px;color:#4a5568">{w_sign}{s["week_change_pct"]:.1f}%</td>
                    <td style="font-size:12px;color:#4a5568;text-align:right">{cap}</td>
                </tr>"""
        return rows
    
    def news_items(news_list):
        items = ""
        for n in news_list:
            items += f"""
            <div class="news-card">
                <div class="news-tag">{n["tag"]}</div>
                <div class="news-source">{n["source"]}</div>
                <a href="{n["url"]}" target="_blank" class="news-title">{n["title"]}</a>
                <div class="news-summary">{n["summary"]}</div>
                <a href="{n["url"]}" target="_blank" class="news-link">阅读原文 ↗</a>
            </div>"""
        return items
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI全球早报 - {date_str}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
  font-family:'SF Pro Display','PingFang SC','Hiragino Sans GB','Microsoft YaHei',-apple-system,sans-serif;
  background: linear-gradient(135deg,#0f0f23 0%,#1a1a2e 50%,#16213e 100%);
  color:#e2e8f0;
  line-height:1.6;
  min-height:100vh;
  font-size:15px;
}}
.container{{max-width:960px;margin:0 auto;padding:24px}}
.header{{
  background: linear-gradient(135deg,#667eea 0%,#764ba2 50%,#f093fb 100%);
  border-radius:20px;
  padding:40px 36px;
  margin-bottom:28px;
  box-shadow:0 20px 60px rgba(102,126,234,0.3);
  position:relative;
  overflow:hidden;
}}
.header::before{{
  content:'';
  position:absolute;
  top:-60%;
  right:-10%;
  width:500px;
  height:500px;
  background:radial-gradient(circle,rgba(255,255,255,0.12) 0%,transparent 70%);
  border-radius:50%;
  animation: float 8s ease-in-out infinite;
}}
@keyframes float{{
  0%,100%{{transform:translateY(0px)}}
  50%{{transform:translateY(-20px)}}
}}
.header-badge{{
  display:inline-block;
  background:rgba(255,255,255,0.18);
  color:#fff;
  padding:6px 16px;
  border-radius:20px;
  font-size:12px;
  font-weight:600;
  letter-spacing:1.5px;
  text-transform:uppercase;
  margin-bottom:14px;
  backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,0.15);
}}
.header h1{{
  font-size:38px;
  font-weight:800;
  color:#fff;
  margin-bottom:10px;
  text-shadow:0 4px 12px rgba(0,0,0,0.2);
  letter-spacing:-0.5px;
}}
.header-date{{color:rgba(255,255,255,0.85);font-size:15px;font-weight:500}}
.header-date span{{color:#fff;font-weight:700}}
.section{{
  background:rgba(26,32,53,0.7);
  backdrop-filter:blur(20px);
  border-radius:18px;
  padding:28px;
  margin-bottom:22px;
  box-shadow:0 8px 32px rgba(0,0,0,0.3);
  border:1px solid rgba(102,126,234,0.15);
}}
.section-title{{
  font-size:18px;
  font-weight:700;
  color:#e2e8f0;
  margin-bottom:20px;
  display:flex;
  align-items:center;
  gap:12px;
}}
.section-title .icon{{
  width:10px;
  height:10px;
  border-radius:50%;
  background:linear-gradient(135deg,#667eea,#f093fb);
  box-shadow:0 0 12px rgba(102,126,234,0.5);
  animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse{{
  0%,100%{{box-shadow:0 0 12px rgba(102,126,234,0.5)}}
  50%{{box-shadow:0 0 20px rgba(240,147,251,0.7)}}
}}
.section-title .market-tag{{
  font-size:11px;
  font-weight:600;
  padding:4px 10px;
  border-radius:8px;
  background:rgba(102,126,234,0.15);
  color:#a8b4ff;
  margin-left:auto;
  border:1px solid rgba(102,126,234,0.25);
}}
.stock-table{{width:100%;border-collapse:collapse;font-size:14px}}
.stock-table th{{
  text-align:left;
  padding:12px 14px;
  color:#a8b4ff;
  font-weight:700;
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:1px;
  border-bottom:2px solid rgba(102,126,234,0.3);
}}
.stock-table td{{
  padding:16px 14px;
  border-bottom:1px solid rgba(102,126,234,0.1);
  vertical-align:middle;
  font-size:14px;
}}
.stock-table tr:hover td{{background:rgba(102,126,234,0.08)}}
.stock-table tr:last-child td{{border-bottom:none}}
.up{{color:#00ff88;font-weight:700;text-shadow:0 0 8px rgba(0,255,136,0.3)}}
.down{{color:#ff4757;font-weight:700;text-shadow:0 0 8px rgba(255,71,87,0.3)}}
.flat{{color:#a8b4ff}}
.market-bar{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px}}
.market-stat{{
  background:rgba(26,32,53,0.8);
  backdrop-filter:blur(20px);
  border-radius:14px;
  padding:18px 22px;
  box-shadow:0 8px 32px rgba(0,0,0,0.3);
  flex:1;
  min-width:150px;
  border:1px solid rgba(102,126,234,0.15);
}}
.market-stat-label{{
  font-size:11px;
  color:#a8b4ff;
  margin-bottom:6px;
  text-transform:uppercase;
  letter-spacing:1px;
  font-weight:600;
}}
.market-stat-value{{font-size:22px;font-weight:800;color:#e2e8f0}}
.market-stat-change{{font-size:13px;font-weight:700;margin-top:4px}}
.news-card{{
  background:rgba(26,32,53,0.6);
  backdrop-filter:blur(20px);
  border-radius:14px;
  padding:20px;
  margin-bottom:16px;
  border:1px solid rgba(102,126,234,0.15);
  border-left:4px solid #667eea;
  transition: all 0.3s ease;
}}
.news-card:hover{{
  border-left-color:#f093fb;
  background:rgba(102,126,234,0.1);
  transform:translateX(4px);
  box-shadow:0 8px 32px rgba(102,126,234,0.2);
}}
.news-tag{{
  display:inline-block;
  background:rgba(102,126,234,0.2);
  color:#a8b4ff;
  padding:3px 12px;
  border-radius:8px;
  font-size:11px;
  font-weight:700;
  letter-spacing:0.5px;
  margin-bottom:10px;
}}
.news-source{{font-size:11px;color:#6b7bff;margin-bottom:8px;font-weight:600}}
.news-title{{
  font-size:16px;
  font-weight:700;
  color:#e2e8f0;
  text-decoration:none;
  display:block;
  margin-bottom:8px;
  line-height:1.5;
}}
.news-title:hover{{color:#a8b4ff}}
.news-summary{{font-size:14px;color:#8892b0;line-height:1.7;margin-bottom:12px}}
.news-link{{
  font-size:12px;
  color:#667eea;
  text-decoration:none;
  display:inline-flex;
  align-items:center;
  gap:6px;
  font-weight:600;
  transition: all 0.2s;
}}
.news-link:hover{{color:#f093fb;gap:10px}}
.summary-box{{
  background:linear-gradient(135deg,rgba(102,126,234,0.1) 0%,rgba(240,147,251,0.1) 100%);
  border-radius:14px;
  padding:22px;
  border:1px solid rgba(102,126,234,0.2);
}}
.summary-box p{{font-size:15px;color:#b8c1ec;line-height:1.8}}
.footer{{
  text-align:center;
  padding:28px;
  color:#6b7bff;
  font-size:12px;
  letter-spacing:1px;
}}
@media(max-width:600px){{
  .header h1{{font-size:26px}}
  .stock-table{{font-size:13px}}
  .stock-table th:nth-child(4),.stock-table td:nth-child(4){{display:none}}
  .market-bar{{flex-direction:column}}
  .news-title{{font-size:15px}}
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-badge">AI 全球早报 · GitHub自动版</div>
        <h1>AI 全球早报</h1>
        <div class="header-date">{date_str} <span>{weekday_str}</span> | 美股 · 港股 · A股 · 全球AI动态</div>
    </div>

    <div class="market-bar">
        <div class="market-stat">
            <div class="market-stat-label">AI核心标的涨跌</div>
            <div class="market-stat-value" style="color:#16a34a">{up_count}涨 {down_count}跌 {flat_count}平</div>
            <div class="market-stat-change up">覆盖{len(stocks)}只标的</div>
        </div>
        <div class="market-stat">
            <div class="market-stat-label">最大涨幅</div>
            <div class="market-stat-value" style="color:#16a34a">{top_gainer["ticker"] if top_gainer else "-"}</div>
            <div class="market-stat-change up">+{top_gainer["change_pct"]:.2f}%</div>
        </div>
        <div class="market-stat">
            <div class="market-stat-label">生成时间</div>
            <div class="market-stat-value">{now.strftime("%H:%M")}</div>
            <div class="market-stat-change flat">北京时间</div>
        </div>
    </div>
"""
    
    # 股票区块
    if us_stocks:
        html += f"""
    <div class="section">
        <div class="section-title"><div class="icon"></div>美股 AI 核心标的<span class="market-tag">NASDAQ/NYSE</span></div>
        <table class="stock-table"><thead><tr><th>股票</th><th>现价</th><th>日涨跌</th><th>5日涨跌</th><th style="text-align:right">市值</th></tr></thead><tbody>{stock_rows(us_stocks)}</tbody></table>
    </div>"""
    
    if hk_stocks:
        html += f"""
    <div class="section">
        <div class="section-title"><div class="icon"></div>港股 AI 核心标的<span class="market-tag">HKEX</span></div>
        <table class="stock-table"><thead><tr><th>股票</th><th>现价</th><th>日涨跌</th><th>5日涨跌</th><th style="text-align:right">市值</th></tr></thead><tbody>{stock_rows(hk_stocks)}</tbody></table>
    </div>"""
    
    if cn_stocks:
        html += f"""
    <div class="section">
        <div class="section-title"><div class="icon"></div>A股 AI 核心标的<span class="market-tag">SSE/SZSE</span></div>
        <table class="stock-table"><thead><tr><th>股票</th><th>现价</th><th>日涨跌</th><th>5日涨跌</th><th style="text-align:right">市值</th></tr></thead><tbody>{stock_rows(cn_stocks)}</tbody></table>
    </div>"""
    
    # 新闻区块
    html += f"""
    <div class="section">
        <div class="section-title"><div class="icon"></div>今日AI要闻 · 可溯源</div>
        {news_items(news)}
    </div>

    <div class="section">
        <div class="section-title"><div class="icon"></div>市场总结</div>
        <div class="summary-box">
            <p>本报告由 GitHub Actions 自动生成，覆盖美股、港股、A股共 <strong style="color:#16a34a">{len(stocks)}</strong> 只AI核心标的。数据来源为 Yahoo Finance，新闻来源为 RSS 聚合与 NewsAPI。</p>
            <p style="margin-top:10px">今日最强标的为 <strong style="color:#1a202c">{top_gainer["name"] if top_gainer else "-"} ({top_gainer["ticker"] if top_gainer else "-"})</strong>，涨幅 <strong style="color:#16a34a">{top_gainer["change_pct"]:.2f}%</strong>。</p>
        </div>
    </div>

    <div class="footer">
        AI全球早报 · GitHub Actions 自动版 | 每天早上 06:00 (北京时间) 自动生成
    </div>
</div>
</body>
</html>"""
    
    return html


def main():
    print("[1/3] 获取股票数据...")
    stocks = get_stock_data()
    print(f"    成功获取 {len(stocks)} 只股票")
    
    print("[2/3] 获取新闻数据...")
    news = get_news()
    print(f"    成功获取 {len(news)} 条新闻")
    
    print("[3/3] 生成HTML报告...")
    html = generate_html(stocks, news)
    
    # 确保输出目录存在
    Path("dist").mkdir(exist_ok=True)
    with open("dist/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("    已保存到 dist/index.html")
    print("[DONE] 早报生成完成!")


if __name__ == "__main__":
    main()
