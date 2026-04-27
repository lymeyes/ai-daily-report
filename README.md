# AI 全球早报 🤖📰

每天早上 **06:00（北京时间）** 自动生成并部署 AI 领域早报，覆盖 **美股 · 港股 · A股** 核心标的 + 全球AI新闻聚合。

> 🌐 在线演示：https://ehvkmoedbxbtu.ok.kimi.link

---

## 📊 覆盖内容

| 类别 | 数量 | 示例 |
|------|------|------|
| **美股** | 9只 | NVIDIA、AMD、Microsoft、Alphabet、Amazon、Meta、Tesla、Palantir、阿里巴巴 |
| **港股** | 5只 | 腾讯、小米、阿里巴巴-SW、商汤、瑞声科技 |
| **A股** | 5只 | 中芯国际、寒武纪、科大讯飞、海光信息、中科曙光 |
| **新闻** | 8条+ | TechCrunch、MIT Technology Review、机器之心、量子位等 |

---

## 🚀 快速开始（2步搞定）

### 第1步：创建 GitHub 仓库

1. 登录 [GitHub](https://github.com)
2. 点击右上角 **+** → **New repository**
3. 仓库名填 `ai-daily-report`（或其他名字）
4. 选择 **Public**（GitHub Pages 需要 Public 或 Pro 账号）
5. 点击 **Create repository**

### 第2步：上传代码

**方式A：直接上传（最简单）**

1. 下载本项目的所有文件
2. 在 GitHub 仓库页面点击 **Upload files**
3. 拖拽所有文件到上传区
4. 点击 **Commit changes**

**方式B：命令行**

```bash
git clone https://github.com/你的用户名/ai-daily-report.git
cd ai-daily-report
# 复制所有文件到此目录
git add .
git commit -m "init: AI daily report"
git push origin main
```

---

## ⚙️ 启用 GitHub Actions

### 1. 开启 GitHub Pages

进入仓库 → **Settings** → **Pages** → **Source** 选择 **GitHub Actions**

### 2. 配置定时任务（可选）

工作流文件已包含定时触发器，默认每天 UTC 22:00（北京时间次日 06:00）自动运行。

如需手动测试，进入仓库 → **Actions** → **AI Daily Morning Report** → **Run workflow**

### 3. 添加 NewsAPI Key（可选，提升新闻质量）

> 如果不配置，将使用免费 RSS 源获取新闻，效果同样可用。

1. 到 [NewsAPI](https://newsapi.org) 注册获取免费 API Key
2. 进入仓库 → **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. Name 填 `NEWS_API_KEY`，Value 填你的 API Key
5. 点击 **Add secret**

---

## 📁 项目结构

```
ai-daily-report/
├── .github/
│   └── workflows/
│       └── daily-report.yml    # GitHub Actions 定时工作流
├── generate_report.py          # 核心脚本：采集数据 + 生成HTML
├── requirements.txt            # Python 依赖
├── README.md                   # 本文件
└── dist/                       # 生成的 HTML 输出目录（自动创建）
```

---

## 🛠️ 本地测试

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行脚本（可选：设置 NewsAPI Key）
export NEWS_API_KEY="你的key"  # Linux/Mac
# set NEWS_API_KEY=你的key     # Windows

python generate_report.py

# 3. 查看输出
dist/index.html
```

---

## ⏰ 定时说明

`.github/workflows/daily-report.yml` 中的 Cron 表达式：

```yaml
- cron: '0 22 * * *'
```

- **UTC 22:00** = **北京时间次日 06:00**（UTC+8）
- 全年固定，无需调整夏令时

---

## 📝 自定义配置

### 添加/删除股票

编辑 `generate_report.py` 顶部的 `STOCKS` 字典：

```python
STOCKS = {
    "NVDA": {"name": "NVIDIA", "market": "US", "sector": "芯片"},
    "0700.HK": {"name": "腾讯控股", "market": "HK", "sector": "互联网"},
    "688981.SS": {"name": "中芯国际", "market": "CN", "sector": "芯片"},
    # 添加你自己的...
}
```

### 添加新闻源

编辑 `generate_report.py` 顶部的 `RSS_FEEDS`：

```python
RSS_FEEDS = [
    ("源名称", "RSS地址"),
    # 添加你自己的...
]
```

---

## 💡 常见问题

**Q：为什么新闻全是英文？**  
A：默认 RSS 源以英文为主。如需中文新闻为主，可删除英文 RSS 源，只保留 `机器之心`、`量子位` 等中文源。

**Q：A股数据准确吗？**  
A：A股数据通过 Yahoo Finance 获取，可能存在15分钟延迟。如需实时数据，建议使用 A 股专用数据接口。

**Q：可以推送到微信/钉钉吗？**  
A：可以。在 `generate_report.py` 的 `main()` 函数末尾，添加 Webhook 推送代码即可。

---

## 📄 License

MIT License — 可自由修改和分发。
