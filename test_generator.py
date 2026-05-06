#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试新的抑制率生成逻辑"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.data_generator import (
    set_risk_lists,
    set_rate_ranges,
    gen_inhibition_rates,
    load_history
)
from app.models.config_model import load_config

# 加载配置
config = load_config()

# 初始化数据生成器
set_risk_lists(config.get("high_risk", []), config.get("low_risk", []))
set_rate_ranges(config.get("rate_ranges", {}))

print("=" * 60)
print("测试抑制率生成逻辑")
print("=" * 60)

# 测试1：首次生成
print("\n【测试1】首次生成（菜名无历史记录）")
vegs1 = ["花菜", "白菜", "黄瓜"]
result1 = gen_inhibition_rates(vegs1)
for item in result1:
    print(f"  {item['variety']}: {item['rate']}")

# 测试2：相同菜名再次生成（应基于上次值波动±5%）
print("\n【测试2】相同菜名再次生成（应基于上次值波动±5%）")
vegs2 = ["花菜", "白菜", "黄瓜"]
result2 = gen_inhibition_rates(vegs2)
for item in result2:
    print(f"  {item['variety']}: {item['rate']}")

# 测试3：验证变动幅度
print("\n[测试3] 验证变动幅度（应≤5%）")
for i, item1 in enumerate(result1):
    item2 = result2[i]
    rate1 = float(item1['rate'].replace('%', ''))
    rate2 = float(item2['rate'].replace('%', ''))
    change = abs(rate2 - rate1) / rate1 * 100
    status = "OK" if change <= 5.5 else "FAIL"  # 允许0.5%误差
    print(f"  {item1['variety']}: {rate1:.3f}% -> {rate2:.3f}% (变动 {change:.2f}%) {status}")

# 测试4：验证不是整数
print("\n[测试4] 验证抑制率不是精确整数")
for item in result2:
    rate = float(item['rate'].replace('%', ''))
    is_integer = abs(rate - round(rate)) < 0.01
    status = "FAIL 是整数" if is_integer else "OK 非整数"
    print(f"  {item['variety']}: {item['rate']} {status}")

# 测试5：多次生成验证稳定性
print("\n【测试5】同一菜名连续生成5次，验证波动范围")
vegs3 = ["花菜"]
rates = []
for i in range(5):
    result = gen_inhibition_rates(vegs3)
    rate = float(result[0]['rate'].replace('%', ''))
    rates.append(rate)
    print(f"  第{i+1}次: {result[0]['rate']}")

min_rate = min(rates)
max_rate = max(rates)
total_change = (max_rate - min_rate) / min_rate * 100
print(f"  波动范围: {min_rate:.3f}% ~ {max_rate:.3f}% (总变动 {total_change:.2f}%)")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)