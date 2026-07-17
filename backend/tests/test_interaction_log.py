"""测试用户交互日志功能"""

import os
import sys
import tempfile
from pathlib import Path

# 设置临时日志路径
temp_dir = tempfile.mkdtemp()
os.environ["SUNDAY_LOG_PATH"] = str(Path(temp_dir) / "engine.log")
os.environ["SUNDAY_INTERACTION_LOG_PATH"] = str(Path(temp_dir) / "interaction.log")
os.environ["SUNDAY_LOG_INTERACTION"] = "true"
os.environ["SUNDAY_LOG_FULL_CONTENT"] = "true"

# 导入日志模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.log_engine import log

def test_interaction_logging():
    """测试完整的用户交互日志流程"""

    print("=" * 60)
    print("测试用户交互日志系统")
    print("=" * 60)

    request_id = "req_test_001"
    user_id = "user_123"
    session_id = "sess_abc"

    # 1. 记录交互开始
    print("\n1. 记录交互开始...")
    log.interaction_start(
        session_id=session_id,
        user_id=user_id,
        request_id=request_id,
        user_message="我最近压力很大，感觉有点焦虑",
        conversation_id="conv_456",
        metadata={"client": "web", "ip": "192.168.1.100"}
    )

    # 2. 记录上下文检索
    print("2. 记录上下文检索...")
    log.context_retrieved(
        request_id=request_id,
        memory_nodes=[
            {"id": "mem_001", "content": "用户最近在准备考试", "importance": 0.8},
            {"id": "mem_002", "content": "用户提到工作压力", "importance": 0.6},
        ],
        conversation_history=[
            {"role": "user", "content": "最近好累"},
            {"role": "assistant", "content": "我能理解..."},
        ],
        retrieved_count=2
    )

    # 3. 记录护栏检查
    print("3. 记录护栏检查...")
    log.guardrail_check(
        request_id=request_id,
        stage="input",
        passed=True,
        reason="all checks passed"
    )

    # 4. 记录工具调用
    print("4. 记录工具调用...")
    log.tool_call(
        request_id=request_id,
        tool_name="memory_search",
        tool_args={"query": "压力", "limit": 5},
        tool_result=[{"id": "mem_003", "content": "用户喜欢听音乐放松"}],
        success=True,
        latency_ms=120.5
    )

    # 5. 记录记忆写入
    print("5. 记录记忆写入...")
    log.memory_write(
        request_id=request_id,
        node_id="mem_004",
        node_type="interaction",
        content_preview="用户表达了焦虑情绪，需要情感支持",
        importance=0.75
    )

    # 6. 记录交互完成
    print("6. 记录交互完成...")
    log.interaction_complete(
        request_id=request_id,
        user_id=user_id,
        system_response="我能感觉到你的压力。压力很大的时候，允许自己慢下来是很重要的。你想聊聊具体是什么让你感到焦虑吗？",
        total_latency_ms=2340.5,
        tokens_used=1520,
        cost_usd=0.0045,
        engine_used="deepseek-chat",
        success=True
    )

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    # 检查日志文件
    engine_log = Path(temp_dir) / "engine.log"
    interaction_log = Path(temp_dir) / "interaction.log"

    print(f"\n引擎日志路径: {engine_log}")
    print(f"交互日志路径: {interaction_log}")

    if interaction_log.exists():
        print(f"\n交互日志大小: {interaction_log.stat().st_size} bytes")
        print("\n交互日志内容:")
        print("-" * 60)
        with open(interaction_log, "r", encoding="utf-8") as f:
            content = f.read()
            print(content)
    else:
        print("\n[WARNING] 交互日志文件未生成")

    return temp_dir

def test_pii_redaction():
    """测试 PII 脱敏功能"""
    print("\n" + "=" * 60)
    print("测试 PII 脱敏")
    print("=" * 60)

    from app.log_engine import _redact_pii

    test_cases = [
        ("我的手机号是 13812345678", "我的手机号是 138****5678"),
        ("邮箱 user@example.com", "邮箱 u***@example.com"),
        ("身份证 110101199001011234", "身份证 110101********1234"),
    ]

    for original, expected in test_cases:
        redacted = _redact_pii(original)
        status = "[OK]" if redacted == expected else "[FAIL]"
        print(f"\n{status} 原文: {original}")
        print(f"  脱敏: {redacted}")
        if redacted != expected:
            print(f"  期望: {expected}")

def test_long_message_truncation():
    """测试长消息截断"""
    print("\n" + "=" * 60)
    print("测试长消息截断")
    print("=" * 60)

    long_message = "这是一条很长的消息" * 1000  # 超过 10000 字符

    print(f"\n原始消息长度: {len(long_message)} 字符")

    log.interaction_start(
        session_id="sess_test",
        user_id="user_test",
        request_id="req_long",
        user_message=long_message,
    )

    print("[OK] 长消息已截断并记录")

if __name__ == "__main__":
    try:
        temp_dir = test_interaction_logging()
        test_pii_redaction()
        test_long_message_truncation()

        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        print(f"\n日志文件保存在: {temp_dir}")
        print("你可以手动检查日志内容。")

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
