#!/usr/bin/env python3
"""测试 needs_reasoner 逻辑"""

import re

_TOOL_RE = re.compile(r"(搜索|查一下|查一查|帮我查|查询|发邮件|提交|运行|计算|算一下|算一算|"
                      r"规划|安排|日程|提醒|翻译|天气|几点了|几点|今天几|星期几|日期|"
                      r"读一下|读取|打开文件|写一下|写入|保存|记下来|做个笔记|记个笔记|笔记|"
                      r"列出|列一下|看看我的|我的.*有哪些|"
                      r"说过|记得|之前|以前|原来|告诉过|访问|打开|获取|"
                      r"search|run|commit|schedule|plan|calculate|book|weather|translate|"
                      r"list|show|fetch|note|reminder)")
_RISK_RE = re.compile(r"(删除|删掉|支付|付款|转账|权限|delete|drop|pay|purchase|rm -rf)")
_STEP_RE = re.compile(r"(然后|接着|之后|first|then|after that|step \d|步骤|再|最后|顺便|同时)")

test_messages = [
    "你好",
    "今天天气真不错",
    "帮我写一个Python函数",
    "你是谁",
    "讲个笑话",
]

for msg in test_messages:
    tool_intent = bool(_TOOL_RE.search(msg))
    steps = 1 + len(_STEP_RE.findall(msg))
    risk = 3 if _RISK_RE.search(msg) else (2 if tool_intent else 1)

    needs_reasoner = tool_intent or steps > 1 or risk >= 2

    print(f"\n消息: {msg}")
    print(f"  工具意图: {tool_intent}")
    print(f"  步骤数: {steps}")
    print(f"  风险级别: {risk}")
    print(f"  需要Reasoner: {needs_reasoner}")
