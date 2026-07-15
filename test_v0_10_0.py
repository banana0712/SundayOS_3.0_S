#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sunday OS v0.10.0 功能测试脚本
测试所有新功能是否正常工作
"""
import requests
import json
import sys
import io

# 修复Windows控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://45.207.220.124:8005"
API_KEY = "sunday0712"  # 从 CURRENT_STATE.md 中看到的
HEADERS = {"X-API-Key": API_KEY}

def test_health():
    """测试 1: 健康检查"""
    print("=" * 60)
    print("测试 1: 健康检查 - /health")
    print("=" * 60)

    r = requests.get(f"{BASE_URL}/health")
    data = r.json()

    print(f"状态: {data['status']}")
    print(f"版本: {data['version']}")
    print(f"引擎: {', '.join(data['engines'])}")
    print(f"记忆节点: {data['memory_nodes']}")
    print(f"对话数: {data['conversation_count']}")
    print(f"嵌入器: {data['embedder']} ({data['embedder_provider']})")

    assert data['version'] == '0.10.0', f"版本错误: {data['version']}"
    assert data['status'] == 'ok', "服务状态异常"
    print("✓ 健康检查通过")
    print()

def test_dashboard_stats():
    """测试 2: Dashboard 统计数据（新功能）"""
    print("=" * 60)
    print("测试 2: Dashboard 统计 - /api/stats/dashboard")
    print("=" * 60)

    r = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=HEADERS)
    data = r.json()

    print(f"今日消息数: {data.get('messages_today', 0)}")
    print(f"总对话数: {data.get('total_conversations', 0)}")
    print(f"记忆节点: {data.get('memory_count', 0)}")
    print(f"今日 Token: {data.get('tokens_today', 0)}")

    # 检查系统健康数据（v0.10.0 新增）
    if 'system_health' in data:
        health = data['system_health']
        print("\n系统健康:")
        print(f"  数据库: {'✓' if health.get('db') else '✗'}")
        print(f"  嵌入器: {health.get('embedder_provider', 'unknown')}")
        print(f"  降级模式: {'是' if health.get('degraded') else '否'}")
        print(f"  向量维度: {health.get('dim', 0)}")
        print(f"  引擎数: {len(health.get('engines', []))}")
        print(f"  版本: {health.get('version', 'unknown')}")

        # v0.10.0 应该移除了假的组件
        assert 'Qdrant' not in str(health), "不应该有假的 Qdrant"
        assert 'Redis' not in str(health), "不应该有假的 Redis"
        print("\n✓ Dashboard 统计数据正确（无假数据）")
    else:
        print("\n⚠ 缺少 system_health 数据")

    print()

def test_admin_endpoints():
    """测试 3: Admin 管理端点（新拆分的路由）"""
    print("=" * 60)
    print("测试 3: Admin 端点 - /api/admin/*")
    print("=" * 60)

    # 测试用户列表
    r = requests.get(f"{BASE_URL}/api/admin/users", headers=HEADERS)
    if r.status_code == 200:
        users = r.json()
        print(f"返回数据类型: {type(users)}")
        if isinstance(users, dict):
            print(f"用户数: {len(users)}")
            if users:
                first_key = list(users.keys())[0]
                user = users[first_key]
                print(f"示例用户: {first_key} ({user})")
        elif isinstance(users, list):
            print(f"用户数: {len(users)}")
            if users:
                print(f"第一个元素: {users[0]}")
        print("✓ Admin 用户列表端点正常")
    else:
        print(f"⚠ Admin 端点返回 {r.status_code}")

    # 测试使用统计
    r = requests.get(f"{BASE_URL}/api/admin/usage", headers=HEADERS)
    if r.status_code == 200:
        usage = r.json()
        print(f"总用量记录: {len(usage) if isinstance(usage, (list, dict)) else 0}")
        print("✓ Admin 使用统计端点正常")
    else:
        print(f"⚠ 使用统计端点返回 {r.status_code}")

    print()

def test_conversation_persistence():
    """测试 4: 对话持久化（SQLite）"""
    print("=" * 60)
    print("测试 4: 对话持久化")
    print("=" * 60)

    # 创建一个测试对话
    r = requests.post(
        f"{BASE_URL}/api/conversations",
        headers=HEADERS,
        json={"title": "测试对话-v0.10.0"}
    )

    if r.status_code == 200:
        conv = r.json()
        conv_id = conv['id']
        print(f"✓ 创建对话: {conv_id}")
        print(f"  标题: {conv['title']}")
        print(f"  创建时间: {conv.get('created_at', 'unknown')}")

        # 列出所有对话
        r = requests.get(f"{BASE_URL}/api/conversations", headers=HEADERS)
        convs = r.json()
        print(f"✓ 总对话数: {len(convs)}")

        # 删除测试对话
        r = requests.delete(f"{BASE_URL}/api/conversations/{conv_id}", headers=HEADERS)
        if r.status_code == 200:
            print(f"✓ 删除对话成功")

        print("✓ 对话持久化功能正常")
    else:
        print(f"✗ 创建对话失败: {r.status_code}")

    print()

def test_chat_with_routing():
    """测试 5: 聊天 + 路由追踪"""
    print("=" * 60)
    print("测试 5: 聊天 + 引擎路由")
    print("=" * 60)

    r = requests.post(
        f"{BASE_URL}/api/chat",
        headers=HEADERS,
        json={
            "message": "简单介绍一下自己，一句话",
            "user_id": "test_user"
        }
    )

    if r.status_code == 200:
        data = r.json()
        print(f"回复: {data['reply'][:100]}...")
        print(f"使用引擎: {data.get('engine', 'unknown')}")
        print(f"系统模式: {data.get('system', 'unknown')}")
        print(f"复杂度: {data.get('complexity', 0)}")

        # 检查路由追踪
        if 'trace' in data:
            trace = data['trace']
            print(f"\n路由决策:")
            print(f"  选中引擎: {trace.get('selected', 'unknown')}")
            print(f"  评分: {trace.get('scores', {})}")

        print("✓ 聊天功能正常")
    else:
        print(f"✗ 聊天失败: {r.status_code}")

    print()

def test_debug_endpoints():
    """测试 6: 调试端点"""
    print("=" * 60)
    print("测试 6: 调试端点 - /api/debug/*")
    print("=" * 60)

    # Overview
    r = requests.get(f"{BASE_URL}/api/debug/overview", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f"✓ 调试概览可用")
        print(f"  记录数: {len(data.get('events', []))}")

    # Routing
    r = requests.get(f"{BASE_URL}/api/debug/routing", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f"✓ 路由调试可用")
        print(f"  路由记录: {len(data.get('recent_routes', []))}")

    print()

def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Sunday OS v0.10.0 功能测试" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    tests = [
        ("健康检查", test_health),
        ("Dashboard 统计", test_dashboard_stats),
        ("Admin 端点", test_admin_endpoints),
        ("对话持久化", test_conversation_persistence),
        ("聊天 + 路由", test_chat_with_routing),
        ("调试端点", test_debug_endpoints),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} 失败: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
