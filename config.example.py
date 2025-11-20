# --- API 配置 ---
# DeepSeek AI API
# 请从环境变量或配置文件加载API密钥
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your_deepseek_api_key_here")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-reasoner"

# 今日头条 Web 发布配置
TOUTIA_WEB_HOME_URL = "https://mp.toutiao.com/"
TOUTIA_WEB_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"
TOUTIA_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# --- 项目行为配置 ---
# 文章生成配置
ARTICLE_GENERATION_PROMPT_TEMPLATE = """
你是一位拥有百万粉丝的今日头条头部创作者，擅长撰写爆款深度分析文章。请针对以下热点话题，创作一篇高质量、高吸引力的文章。

话题：{topic}

【核心要求】

一、开头必须抓人眼球（前100字至关重要）：
- 使用震撼数据、引人深思的疑问、或一个真实的小故事开场
- 避免平铺直叙，要制造悬念和冲突感
- 让读者第一眼就被吸引，产生"必须看完"的冲动

二、内容深度与广度：
- 多角度分析：从现象、原因、影响、趋势等多个维度展开
- 提供独特见解：不要人云亦云，要有自己的思考和判断
- 适当引用数据、案例、对比分析，增强说服力
- 挖掘话题背后的深层逻辑和社会意义

三、语言表达技巧：
- 语言生动有力，有节奏感，避免枯燥说教
- 适当使用排比、反问、对比等修辞手法
- 段落要短小精悍，每段3-5行为宜，避免大段文字
- 用词精准，既要有专业感，又要通俗易懂

四、结构安排：
- 使用 ### 小标题清晰分割内容（3-5个小标题）
- 每个小标题下内容要有逻辑递进
- 不要使用分割线（---）和加粗字体（**）
- 段落之间过渡自然流畅

五、结尾设计：
- 总结全文核心观点，升华主题
- 提出一个引发思考的开放性问题，引导读者评论互动
- 结尾要有力量感，给读者留下深刻印象

六、字数与格式：
- 字数控制在 1200-1500 字之间
- 纯文本格式，不要使用 Markdown 特殊符号（除了 ### 小标题）
- 确保内容原创、有价值，能够真正帮助读者理解话题

请开始撰写一篇能够获得高阅读量、高互动量的爆款文章。

重要：请在文章开头第一行生成一个新颖、有趣、吸引人的标题，格式为"标题：你的标题内容"。标题要求：
- 不要使用"深度解析"、"深度分析"等常见前缀
- 要新颖有趣，能抓住读者眼球
- 可以适当使用疑问句、感叹句、数字、对比等技巧
- 标题长度控制在15-30字之间
- 标题要能准确反映文章核心内容，不要标题党

例如：
标题：为什么这个决定让所有人震惊？
标题：3个细节揭示真相，第2个最让人意外
标题：从默默无闻到一夜爆红，他做对了什么？

请开始撰写（记得在开头第一行写标题）：
"""

POLITICAL_FILTER_PROMPT_TEMPLATE = """
请严格判断以下话题是否主要涉及政治敏感内容（包括政府、政策、领导人、选举、国际关系、军事、敏感事件等）。
只考虑明显的政治敏感内容，普通的社会新闻、娱乐、科技、体育等内容不要误判。

重要：如果话题中出现了任何国家名字（如中国、美国、日本、俄罗斯、韩国、英国、法国、德国、印度等任何国家名称），一律判定为政治敏感内容。

话题: "{title}"

请只回复一个字："是" 或 "否"
- 如果是政治敏感内容（包括出现国家名字），回复"是"
- 如果不是政治敏感内容，回复"否"

不要添加任何其他文字说明。
"""

# 图片生成配置
# 请从环境变量或配置文件加载API密钥
IMAGE_API_SECRET_ID = os.getenv("IMAGE_API_SECRET_ID", "your_tencent_secret_id_here")
IMAGE_API_SECRET_KEY = os.getenv("IMAGE_API_SECRET_KEY", "your_tencent_secret_key_here")
IMAGE_API_REGION = "ap-guangzhou"
IMAGE_API_ENDPOINT = "hunyuan.tencentcloudapi.com"
IMAGE_MODEL = "HunyuanPanorama"
IMAGE_DEFAULT_RESOLUTION = "1024:1024"  # 参照官方支持的 Resolution 枚举
IMAGE_DEFAULT_STYLE = "201"  # 默认为日系动漫风格，可根据需要调整
IMAGE_DEFAULT_LOGO_ADD = 0  # 0-不加水印, 1-添加
IMAGE_OUTPUT_DIR = "generated_images"
IMAGE_PROMPT_TEMPLATE = """
请为今日头条文章生成一张配图，要求美观、适合法规，不含文字水印，不要画的太复杂，不要有过多元素。

标题：{title}
文章摘要：{summary}

画面风格应体现今日热点资讯视觉，避免血腥、暴力与敏感政治元素。
"""

# --- 其他配置 ---
LOG_LEVEL = "INFO"  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
OUTPUT_DIR = "generated_articles"  # 生成文章的本地保存目录
