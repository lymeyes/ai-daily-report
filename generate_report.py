import os
import json
import feedparser
import requests
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

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

# RSS 新闻源（无需 API Key）
RSS_FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("机器之心", "https://www.jiqizhixin.com/rss"),
    ("量子位", "https://www.qbitai.com/feed"),
]

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")


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
    """通过 NewsAPI 获取新闻（如果有 API Key）"""
    if not NEWS_API_KEY:
        return []
    
    try:
        url = "https://newsapi.org/v2/everything"
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        params = {
            "q": "artificial intelligence OR AI OR NVIDIA OR OpenAI OR 人工智能",
            "from": yesterday,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 10,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            articles = resp.json().get("articles", [])
            return [
                {
                    "title": a["title"],
                    "summary": a.get("description", "") or "",
                    "url": a["url"],
                    "source": a["source"]["name"],
                    "tag": "AI新闻",
                }
                for a in articles[:6]
            ]
    except Exception as e:
        print(f"[ERROR] NewsAPI: {e}")
    return []


def get_news_from_rss():
    """通过 RSS 获取新闻"""
    news = []
    for source_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:  # 每个源取2条
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                # 清理HTML标签
                summary = summary.replace("<", "&lt;").replace(">", "&gt;")
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                
                link = entry.get("link", "")
                
                # 判断标签
                tag = "AI新闻"
                lower_title = title.lower()
                if any(k in lower_title for k in ["chip", "nvidia", "amd", "gpu", "半导体", "芯片"]):
                    tag = "芯片"
                elif any(k in lower_title for k in ["funding", "invest", "融资", "投资", "亿美元"]):
                    tag = "融资"
                elif any(k in lower_title for k in ["model", "gpt", "llm", "模型", "大模型"]):
                    tag = "模型"
                elif any(k in lower_title for k in ["china", "chinese", "中国", "国产"]):
                    tag = "中国AI"
                
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
    """获取新闻：优先API，备选RSS"""
    api_news = get_news_from_api()
    if api_news:
        return api_news
    return get_news_from_rss()


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
    now = datetime.now()
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
                            <span style="font-size:14px;font-weight:700;color:#fff">{s["ticker"]}</span>
                            <span style="font-size:11px;color:#5a6a8a">{s["name"]}</span>
                            <span style="font-size:10px;color:#7b61ff;background:rgba(123,97,255,0.1);padding:1px 6px;border-radius:4px;width:fit-content">{s["sector"]}</span>
                        </div>
                    </td>
                    <td style="font-size:15px;font-weight:700;color:#fff">{s["price"]:.2f}</td>
                    <td style="font-size:13px;font-weight:600" class="{cls}">
                        <span style="font-size:11px">{arrow}</span> {sign}{s["change_pct"]:.2f}%
                    </td>
                    <td style="font-size:12px;color:#5a6a8a">{w_sign}{s["week_change_pct"]:.1f}%</td>
                    <td style="font-size:12px;color:#5a6a8a;text-align:right">{cap}</td>
                </tr>"""
        return rows
    
    def news_items(news_list):
        items = ""
        for n in news_list:
            items += f"""
            <div style="background:#0b1120;border-radius:12px;padding:18px;border:1px solid #152030;border-left:3px solid #00d4ff;margin-bottom:14px">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap">
                    <span style="background:rgba(0,212,255,0.1);color:#00d4ff;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:600">{n["tag"]}</span>
                    <span style="font-size:11px;color:#4a5570">{n["source"]}</span>
                </div>
                <a href="{n["url"]}" target="_blank" style="font-size:15px;font-weight:600;color:#e6edf3;text-decoration:none;display:block;margin-bottom:6px;line-height:1.4">{n["title"]}</a>
                <div style="font-size:13px;color:#8b9bb4;line-height:1.6;margin-bottom:10px">{n["summary"]}</div>
                <a href="{n["url"]}" target="_blank" style="font-size:11px;color:#7b61ff;text-decoration:none;display:inline-flex;align-items:center;gap:4px">阅读原文 ↗</a>
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
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:#f7fafc;color:#2d3748;line-height:1.6}}
.container{{max-width:960px;margin:0 auto;padding:20px}}
.header{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;padding:32px;margin-bottom:24px;box-shadow:0 10px 25px rgba(102,126,234,0.15)}}
.header::before{{content:'';position:absolute;top:-50%;right:-20%;width:400px;height:400px;background:radial-gradient(circle,rgba(255,255,255,0.1) 0%,transparent 70%);border-radius:50%}}
.header-badge{{display:inline-block;background:rgba(255,255,255,0.2);color:#fff;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;backdrop-filter:blur(10px)}}
.header h1{{font-size:30px;font-weight:700;color:#fff;margin-bottom:8px;text-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.header-date{{color:rgba(255,255,255,0.8);font-size:14px}}
.header-date span{{color:#fff;font-weight:500}}
.section{{background:#fff;border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.section-title{{font-size:17px;font-weight:600;color:#2d3748;margin-bottom:18px;display:flex;align-items:center;gap:10px}}
.section-title .icon{{width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);box-shadow:0 0 8px rgba(102,126,234,0.3)}}
.section-title .market-tag{{font-size:11px;font-weight:500;padding:2px 8px;border-radius:6px;background:#f7fafc;color:#718096;margin-left:auto;border:1px solid #e2e8f0}}
.stock-table{{width:100%;border-collapse:collapse;font-size:13px}}
.stock-table th{{text-align:left;padding:10px 12px;color:#718096;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e2e8f0}}
.stock-table td{{padding:14px 12px;border-bottom:1px solid #f0f4f8;vertical-align:middle}}
.stock-table tr:hover td{{background:#f7fafc}}
.stock-table tr:last-child td{{border-bottom:none}}
.up{{color:#38a169}}
.down{{color:#e53e3e}}
.flat{{color:#718096}}
.market-bar{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.market-stat{{background:#fff;border-radius:12px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.08);flex:1;min-width:140px}}
.market-stat-label{{font-size:11px;color:#718096;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px}}
.market-stat-value{{font-size:18px;font-weight:700;color:#2d3748}}
.market-stat-change{{font-size:12px;font-weight:600;margin-top:2px}}
.summary-box{{background:linear-gradient(135deg,#f7fafc 0%,#edf2f7 100%);border-radius:12px;padding:18px;border:1px solid #e2e8f0}}
.summary-box p{{font-size:14px;color:#4a5568;line-height:1.7}}
.footer{{text-align:center;padding:24px;color:#718096;font-size:12px}}
@media(max-width:600px){{
.header h1{{font-size:22px}}
.stock-table{{font-size:12px}}
.stock-table th:nth-child(4),.stock-table td:nth-child(4){{display:none}}
.market-bar{{flex-direction:column}}
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
            <div class="market-stat-value" style="color:#00e5a0">{up_count}涨 {down_count}跌 {flat_count}平</div>
            <div class="market-stat-change up">覆盖{len(stocks)}只标的</div>
        </div>
        <div class="market-stat">
            <div class="market-stat-label">最大涨幅</div>
            <div class="market-stat-value" style="color:#00e5a0">{top_gainer["ticker"] if top_gainer else "-"}</div>
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
            <p>本报告由 GitHub Actions 自动生成，覆盖美股、港股、A股共 <strong style="color:#00e5a0">{len(stocks)}</strong> 只AI核心标的。数据来源为 Yahoo Finance，新闻来源为 RSS 聚合与 NewsAPI。</p>
            <p style="margin-top:10px">今日最强标的为 <strong style="color:#00d4ff">{top_gainer["name"] if top_gainer else "-"} ({top_gainer["ticker"] if top_gainer else "-"})</strong>，涨幅 <strong style="color:#00e5a0">{top_gainer["change_pct"]:.2f}%</strong>。</p>
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
