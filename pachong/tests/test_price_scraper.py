"""价格爬虫测试"""

import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.price_scraper import PriceScraper
from scrapers.config import DEFAULT_VARIETIES


def test_fetch_all():
    """测试获取所有价格"""
    scraper = PriceScraper()
    all_prices = scraper.scrape_all_prices()

    print(f"共获取 {len(all_prices)} 个品种的价格")
    if all_prices:
        print("\n前10个品种:")
        for item in all_prices[:10]:
            print(f"  {item['品种']}: {item['均价']}元/斤 {item['涨跌']}")

    return all_prices


def test_filter_varieties():
    """测试品种筛选"""
    scraper = PriceScraper()
    data = scraper.scrape_varieties(["白菜", "西红柿", "黄瓜", "土豆", "青椒"])

    print(f"\n筛选后: {len(data)} 个品种")
    for item in data:
        print(f"  {item['品种']}: {item['均价']}元/斤 {item['涨跌']}")

    return data


def test_save_files():
    """测试保存功能"""
    scraper = PriceScraper()
    data = scraper.scrape_varieties(["白菜", "西红柿", "黄瓜"])

    json_path = scraper.save_to_json(data, "price_data")
    csv_path = scraper.save_to_csv(data, "price_data")

    print(f"\nJSON文件: {json_path} (存在: {os.path.exists(json_path)})")
    print(f"CSV文件: {csv_path} (存在: {os.path.exists(csv_path)})")


if __name__ == "__main__":
    print("=" * 50)
    print("价格爬虫测试")
    print("=" * 50)

    print("\n[测试1] 获取所有价格")
    print("-" * 30)
    test_fetch_all()

    print("\n[测试2] 品种筛选")
    print("-" * 30)
    test_filter_varieties()

    print("\n[测试3] 文件保存")
    print("-" * 30)
    test_save_files()

    print("\n测试完成!")
