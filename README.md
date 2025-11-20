# 今日头条自动化内容发布系统

一个基于 AI 的自动化内容创作和发布系统，能够自动爬取热点话题、生成高质量文章、创建配图，并自动发布到今日头条平台。

## ✨ 功能特性

- 🔥 **热点爬取**：自动从 46LA 等平台爬取实时热点话题
- 🤖 **AI 文章生成**：使用 DeepSeek AI 生成高质量、符合平台调性的文章内容
- 🎨 **智能配图生成**：基于腾讯混元 API 自动生成文章封面图
- 🛡️ **内容过滤**：自动过滤政治敏感内容，确保内容安全
- 📝 **自动发布**：使用 Selenium 自动化发布文章到今日头条
- ⏰ **智能调度**：支持自定义发布间隔，避免频繁操作
- 📊 **发布记录**：自动记录已发布文章，支持断点续传

## 📋 系统要求

- Python 3.7+
- Chrome 浏览器（用于 Selenium 自动化）
- 以下 API 密钥：
  - DeepSeek API Key（用于文章生成和内容过滤）
  - 腾讯云混元 API（SecretId 和 SecretKey，用于图片生成）
- 今日头条账号 Cookie（用于自动登录）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd <project-name>
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `config.py` 文件（可复制 `config.example.py`）：

```bash
cp config.example.py config.py
```

编辑 `config.py` 或设置环境变量：

```bash
# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="your_deepseek_api_key"
$env:IMAGE_API_SECRET_ID="your_tencent_secret_id"
$env:IMAGE_API_SECRET_KEY="your_tencent_secret_key"

# Linux/Mac
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export IMAGE_API_SECRET_ID="your_tencent_secret_id"
export IMAGE_API_SECRET_KEY="your_tencent_secret_key"
```

### 4. 配置 Cookie

1. 登录今日头条创作者平台（https://mp.toutiao.com/）
2. 使用浏览器开发者工具导出 Cookie（JSON 格式）
3. 将 Cookie 保存到 `cookies/toutiao.json`

Cookie 文件格式示例（参考 `cookies/toutiao.json.example`）：

```json
[
    {
        "name": "sessionid",
        "value": "your_cookie_value",
        "domain": ".toutiao.com",
        "path": "/",
        "secure": false,
        "httpOnly": false
    }
]
```

### 5. 运行程序

#### 模式 1：只爬取和过滤热点

```bash
python main.py --mode crawl --crawl-limit 100
```

#### 模式 2：只生成并发布文章（从已有热搜数据）

```bash
python main.py --mode publish --hot-searches-file filtered_hot_searches.json
```

#### 模式 3：完整流程（推荐）

```bash
python main.py --mode full --crawl-limit 100 --publish-delay 900
```

## 📖 详细使用说明

### 命令行参数

#### 通用参数

- `--mode`: 运行模式
  - `crawl`: 只爬取和过滤热点
  - `publish`: 只生成并发布文章
  - `full`: 完整流程（默认）

#### 爬取参数

- `--crawl-limit`: 爬取热点的最大数量（默认：100）
- `--hot-searches-file`: 热搜数据 JSON 文件路径（默认：`filtered_hot_searches.json`）

#### 生成和发布参数

- `--generate-limit`: 限制生成的文章数量（默认：不限制）
- `--generate-delay`: 生成文章时的 API 调用间隔秒数（默认：1.5）
- `--publish-delay`: 发布文章后的等待间隔秒数（默认：900，即 15 分钟）
- `--cookies`: Cookie 文件路径（默认：`cookies/toutiao.json`）
- `--headless`: 使用无头浏览器模式
- `--article-dir`: 文章保存目录（默认：`generated_articles`）

#### 封面配置参数

- `--cover-mode`: 封面处理方式
  - `none`: 不上传封面
  - `generate`: 自动生成上传（默认）
- `--cover-style`: 封面风格编号（参考混元文生图 Style 参数）
- `--cover-resolution`: 封面分辨率，如 `1024:1024`
- `--cover-negative`: 封面反向提示词
- `--cover-logo`: 封面是否加水印（1=加，0=不加，默认：0）

### 使用示例

#### 示例 1：完整流程，发布间隔 30 分钟

```bash
python main.py --mode full --crawl-limit 50 --publish-delay 1800
```

#### 示例 2：无头模式，不生成封面

```bash
python main.py --mode publish --headless --cover-mode none
```

#### 示例 3：自定义封面风格和分辨率

```bash
python main.py --mode publish --cover-style 201 --cover-resolution 1024:1024
```

#### 示例 4：限制生成 5 篇文章

```bash
python main.py --mode publish --generate-limit 5
```

## 📁 项目结构

```
.
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── config.example.py      # 配置文件示例
├── requirements.txt       # Python 依赖
├── README.md             # 本文件
│
├── ai_analyzer.py         # AI 文章生成模块
├── hot_topic_finder.py   # 热点爬取模块
├── image_generator.py    # 图片生成模块
├── publisher.py          # 发布模块
├── utils.py              # 工具函数
│
├── cookies/              # Cookie 目录
│   ├── toutiao.json.example  # Cookie 文件示例
│   └── toutiao.json      # 真实 Cookie
│
├── generated_articles/   # 生成的文章
├── generated_images/     # 生成的图片
└── logs/                 # 日志文件
```

## ⚙️ 配置说明

### API 配置

在 `config.py` 中配置以下内容：

- **DeepSeek API**：用于文章生成和内容过滤
- **腾讯混元 API**：用于图片生成
- **文章生成提示词**：可自定义文章生成风格和要求
- **图片生成提示词**：可自定义图片生成风格

### 发布配置

- **发布间隔**：建议设置为 15-30 分钟，避免被平台判定为异常行为
- **封面模式**：可选择不生成封面或自动生成封面

## 🔒 安全注意事项

1. **不要提交敏感信息**：
   - `config.py` 包含 API 密钥，已添加到 `.gitignore`
   - `cookies/toutiao.json` 包含登录凭证，已添加到 `.gitignore`
   - 日志文件可能包含敏感信息，已添加到 `.gitignore`

2. **定期更新 Cookie**：
   - Cookie 可能会过期，需要定期更新
   - 如果登录失败，请重新导出 Cookie

3. **API 密钥安全**：
   - 建议使用环境变量而非直接写在配置文件中
   - 不要在公开场合分享 API 密钥

## 🐛 常见问题

### Q1: Cookie 已失效怎么办？

A: 重新登录今日头条创作者平台，使用浏览器开发者工具导出新的 Cookie，替换 `cookies/toutiao.json` 文件。

### Q2: 封面生成失败怎么办？

A: 检查腾讯混元 API 配置是否正确，确保 SecretId 和 SecretKey 有效。系统会自动重试 3 次，如果仍然失败会跳过该文章。

### Q3: 发布失败怎么办？

A: 检查以下几点：
- Cookie 是否有效
- 网络连接是否正常
- 浏览器驱动是否正确安装
- 查看日志文件了解详细错误信息

### Q4: 如何跳过已发布的文章？

A: 使用 `--mode publish` 模式时，系统会自动跳过 `published_articles.json` 中记录的已发布文章。

### Q5: 如何修改文章生成风格？

A: 编辑 `config.py` 中的 `ARTICLE_GENERATION_PROMPT_TEMPLATE` 变量，修改提示词模板。

## 📝 日志说明

日志文件保存在 `logs/` 目录下，按日期命名（如 `app_20251120.log`）。日志级别可在 `config.py` 中配置：

- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## ⚠️ 免责声明

本工具仅供学习和研究使用。使用本工具时，请遵守：

1. 今日头条平台的服务条款
2. 相关法律法规
3. AI 生成内容的版权和使用规范

使用者需自行承担使用本工具产生的所有责任和风险。

---

**祝您使用愉快！** 🎉

