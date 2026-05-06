import os
import re
from app.models.config_model import load_config

# 读取配置
config = load_config()

big_folder = config.get('big_path', '')
print(f"大表文件夹: {big_folder}")

# 模拟日期选择
y, m, d = '2026', '03', '21'
print(f"选择的日期: {y}.{m}.{d}")

# 构造正则表达式
pattern = re.compile(rf"农残检测记录表{re.escape(y)}\.{re.escape(m)}\.{re.escape(d)}(?:-(\d+))?\.docx$")
print(f"正则表达式: {pattern.pattern}")

# 扫描文件夹
detected = []
try:
    for filename in os.listdir(big_folder):
        print(f"检查文件: {filename}")
        if pattern.match(filename):
            match = pattern.match(filename)
            num_str = match.group(1)
            num = int(num_str) if num_str else 0
            filepath = os.path.join(big_folder, filename)
            detected.append((num, filepath))
            print(f"  匹配! 编号: {num}")
except Exception as e:
    print(f"扫描失败: {e}")

# 排序
detected.sort(key=lambda x: x[0])
detected_tables = [path for _, path in detected]

print(f"\n检测结果:")
print(f"检测到 {len(detected_tables)} 个文件")
for i, path in enumerate(detected_tables):
    print(f"  {i+1}. {os.path.basename(path)}")

if not detected_tables:
    print("未找到任何匹配文件")
    # 列出所有文件供参考
    print("\n文件夹中的所有文件:")
    try:
        for filename in os.listdir(big_folder):
            print(f"  {filename}")
    except:
        pass
