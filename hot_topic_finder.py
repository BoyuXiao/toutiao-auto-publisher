import json
import os
import time

import requests
from bs4 import BeautifulSoup

from config import POLITICAL_FILTER_PROMPT_TEMPLATE, DEEPSEEK_API_KEY


class HotSearchCrawler:
    def __init__(self, deepseek_api_key):
        self.session = requests.Session()
        self.deepseek_api_key = deepseek_api_key
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_hot_searches(self, max_tokens=100):
        """获取46LA热搜页面并解析内容"""
        url = "https://www.46.la/hot"
        try:
            print("正在获取热搜页面...")
            response = self.session.get(url, headers=self.headers)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            hot_searches = []

            # 找到所有的热搜卡片
            cards = soup.find_all("div", class_="hotapi-tab-card")
            print(f"找到 {len(cards)} 个热搜卡片")

            for i, card in enumerate(cards):
                # 检查是否为中关村内容（需要排除的）
                header = card.find("div", class_="hotapi-header")
                if header:
                    # 检查标题和描述
                    title_elem = header.find("span", class_="title-name")
                    desc_elem = header.find("span", class_="text-muted")

                    title_text = title_elem.text if title_elem else ""
                    desc_text = desc_elem.text if desc_elem else ""

                    # 跳过中关村的CPU和手机排行榜
                    if "中关村" in title_text and any(
                        x in desc_text for x in ["CPU", "手机"]
                    ):
                        print(f"跳过中关村内容: {desc_text}")
                        continue

                # 提取热搜列表
                hot_list = card.find("ul", class_="hotapi-list")
                if hot_list:
                    items = hot_list.find_all("li")
                    print(f"卡片 {i+1} 中找到 {len(items)} 个热搜项")

                    for item in items:
                        link_elem = item.find("a")
                        if link_elem and link_elem.get("href"):
                            title = link_elem.text.strip()
                            url = link_elem.get("href")

                            # 提取热度（如果有）
                            heat_elem = item.find("div", class_="hot-heat")
                            heat = heat_elem.text.strip() if heat_elem else "未知"

                            # 提取排名
                            rank_elem = item.find("badge", class_="hotapi-rank")
                            rank = (
                                rank_elem.text.strip()
                                if rank_elem
                                else str(len(hot_searches) + 1)
                            )

                            hot_searches.append(
                                {"title": title, "url": url, "heat": heat, "rank": rank}
                            )

            print(f"总共提取到 {len(hot_searches)} 个热搜话题")
            print(f"保留{min(max_tokens,len(hot_searches))}个")
            return hot_searches[: min(max_tokens, len(hot_searches))]

        except Exception as e:
            print(f"获取热搜数据失败: {e}")
            return []

    def deepseek_political_filter(self, title):
        """使用DeepSeek API判断是否为政治内容"""
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json",
            }

            prompt = POLITICAL_FILTER_PROMPT_TEMPLATE.format(title=title)
            data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 5,
                "temperature": 0.1,
            }

            # 调用DeepSeek API
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"].strip()
                print(f"话题: {title} -> DeepSeek判断: {answer}")

                # 如果返回"是"，说明是政治内容，应该过滤掉（返回False）
                return answer.lower() != "是"
            else:
                print(f"DeepSeek API调用失败: {response.status_code}")
                # API调用失败时，暂时保留内容
                return True

        except Exception as e:
            print(f"DeepSeek API过滤异常: {e}")
            # 异常时暂时保留内容
            return True

    def filter_with_deepseek(self, hot_searches):
        """使用DeepSeek API过滤政治内容"""
        print("开始使用DeepSeek API过滤政治内容...")
        filtered_searches = []

        for i, item in enumerate(hot_searches):
            title = item["title"]
            print(f"正在处理第 {i+1}/{len(hot_searches)} 个话题: {title}")

            # 使用DeepSeek判断是否为政治内容
            if self.deepseek_political_filter(title):
                filtered_searches.append(item)
                print(f"保留话题: {title}")
            else:
                print(f"过滤掉政治话题: {title}")

        print(f"过滤后剩余 {len(filtered_searches)} 个话题")
        return filtered_searches

    def save_results(
        self, hot_searches, max_count=100, json_filename="filtered_hot_searches.json"
    ):
        """保存结果到文件"""
        # 限制数量
        if len(hot_searches) > max_count:
            hot_searches = hot_searches[:max_count]
            print(f"限制为前 {max_count} 个话题")

        # 保存为JSON
        try:
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(hot_searches, f, ensure_ascii=False, indent=2)
            print(f"已保存 {len(hot_searches)} 个热搜话题到 {json_filename}")
        except Exception as e:
            print(f"保存JSON文件失败: {e}")

        return json_filename


def main():
    import os

    is_filter_political = True
    max_count = 100
    # 从环境变量或config.py加载API密钥
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or DEEPSEEK_API_KEY
    crawler = HotSearchCrawler(deepseek_api_key)

    # 获取所有热搜（自动跳过中关村内容）
    all_hot_searches = crawler.fetch_hot_searches(max_tokens=max_count)

    if not all_hot_searches:
        print("没有获取到热搜数据，程序结束")
        return

    # 使用DeepSeek API过滤政治内容
    if is_filter_political:
        filtered_searches = crawler.filter_with_deepseek(all_hot_searches)
    else:
        filtered_searches = all_hot_searches

    if not filtered_searches:
        print("所有话题都被过滤掉了，没有可保存的内容")
        return

    # 保存结果
    json_file = crawler.save_results(filtered_searches, max_count=max_count)

    # 打印部分结果预览
    print("\n" + "=" * 50)
    print("前10个过滤后的热搜话题预览:")
    print("=" * 50)
    for i, item in enumerate(filtered_searches[:10], 1):
        print(f"{i}. [{item['rank']}] {item['title']}")
        print(f"   热度: {item['heat']}")


if __name__ == "__main__":
    main()
