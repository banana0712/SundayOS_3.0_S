#!/usr/bin/env python3
"""
删除 main.py 中的 conversations 端点（行 1088-1172）
"""
import sys

MAIN_PY = "app/main.py"  # 从 backend/ 目录运行

# 读取文件
with open(MAIN_PY, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"原始行数: {len(lines)}")

# 找到 conversations 部分的开始和结束
start_marker = "# --- conversation endpoints"
end_marker = "class MemoryStoreRequest(BaseModel):"

start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if start_marker in line:
        start_idx = i
    if end_marker in line and start_idx is not None:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    print(f"找到 conversations 部分: 行 {start_idx+1} 到 {end_idx}")
    print(f"删除 {end_idx - start_idx} 行")

    # 删除这些行
    new_lines = lines[:start_idx] + lines[end_idx:]

    # 写回文件
    with open(MAIN_PY, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"新行数: {len(new_lines)}")
    print(f"减少了: {len(lines) - len(new_lines)} 行")
    print("✓ 完成")
else:
    print("✗ 未找到标记")
    sys.exit(1)
