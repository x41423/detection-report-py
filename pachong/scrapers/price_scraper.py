"""蔬菜价格爬虫 - CN蔬菜网"""

import json
import os
import re
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .config import MOBILE_URL, HEADERS, REQUEST_DELAY, DEFAULT_VARIETIES


class PriceScraper:
    """蔬菜价格爬虫"""

    def __init__(self, varieties: Optional[list[str]] = None):
        self.varieties = varieties or DEFAULT_VARIETIES
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_price_page(self) -> BeautifulSoup:
        """获取价格页面"""
        r = self.session.get(MOBILE_URL, timeout=15)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'lxml')

    def parse_price_text(self, text: str) -> Optional[dict]:
        """解析价格文本，格式: 西红柿价格2.43元↓"""
        pattern = r'(.+?)价格([\d.]+)元([↑↓\-])'
        match = re.match(pattern, text.strip())
        if match:
            variety = match.group(1)
            price = float(match.group(2))
            trend = match.group(3)
            return {
                "品种": variety,
                "均价": price,
                "涨跌": trend,
            }
        return None

    def scrape_all_prices(self) -> list[dict]:
        """从主页抓取所有价格数据"""
        soup = self.fetch_price_page()
        results = []

        # 查找包含"价格"和"元"的文本
        for element in soup.find_all(['td', 'div', 'span', 'a', 'li']):
            text = element.get_text(strip=True)
            if '价格' in text and '元' in text and len(text) < 30:
                item = self.parse_price_text(text)
                if item and item not in results:
                    results.append(item)

        return results

    def filter_varieties(self, all_prices: list[dict], varieties: list[str]) -> list[dict]:
        """根据品种列表筛选价格"""
        filtered = []
        for item in all_prices:
            for variety in varieties:
                if variety in item["品种"]:
                    filtered.append(item)
                    break
        return filtered

    def scrape_varieties(self, varieties: Optional[list[str]] = None) -> list[dict]:
        """抓取指定品种的价格"""
        target_varieties = varieties or self.varieties

        print("正在获取价格数据...")
        all_prices = self.scrape_all_prices()
        print(f"共获取 {len(all_prices)} 个品种的价格")

        filtered = self.filter_varieties(all_prices, target_varieties)
        print(f"匹配到 {len(filtered)} 个目标品种")

        # 添加采集时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in filtered:
            item["采集时间"] = timestamp

        return filtered

    def save_to_json(self, data: list[dict], output_dir: str = "price_data") -> str:
        """保存数据到JSON文件"""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vegetable_prices_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"数据已保存到: {filepath}")
        return filepath

    def save_to_csv(self, data: list[dict], output_dir: str = "price_data") -> str:
        """保存数据到CSV文件"""
        import csv

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vegetable_prices_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["品种", "均价", "涨跌", "采集时间"])

            for item in data:
                writer.writerow([
                    item.get("品种", ""),
                    item.get("均价", ""),
                    item.get("涨跌", ""),
                    item.get("采集时间", ""),
                ])

        print(f"数据已保存到: {filepath}")
        return filepath


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="蔬菜价格爬虫")
    parser.add_argument("-v", "--varieties", nargs="+", help="指定品种列表")
    parser.add_argument("-o", "--output", default="price_data", help="输出目录")
    parser.add_argument("-f", "--format", choices=["json", "csv", "both"], default="both", help="输出格式")

    args = parser.parse_args()

    scraper = PriceScraper()

    print("=" * 50)
    print("蔬菜价格爬虫 - CN蔬菜网")
    print("=" * 50)

    data = scraper.scrape_varieties(args.varieties)

    print(f"\n采集完成! 共获取 {len(data)} 条价格数据")

    if args.format in ("json", "both"):
        scraper.save_to_json(data, args.output)

    if args.format in ("csv", "both"):
        scraper.save_to_csv(data, args.output)

    # 打印结果预览
    print("\n=== 数据预览 ===")
    for item in data[:10]:
        print(f"  {item['品种']}: {item['均价']}元/斤 {item['涨跌']}")


if __name__ == "__main__":
    main()
