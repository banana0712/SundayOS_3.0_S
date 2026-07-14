# ADR-012 · 反馈驱动的个人偏好学习系统

**日期**: 2026-07-15
**状态**: Accepted
**影响范围**: `backend/app/persona/preferences.py`, `backend/app/persona/feedback_parser.py`, `backend/app/persona/__init__.py`, `backend/app/main.py`, `backend/app/webchat.py`

---

## 背景

ADR-011 引入了 `EngineCapabilities.quality` 字段和 quality-first 路由权重表，但 quality 评分被明确标注为"人工设定"。ADR-011 自身在第 85 行指出：

> `quality 评分目前是人工设定，需要用户反馈驱动调优`

没有一个反馈管道来收集用户信号、自动调整评分或注入个性化偏好。

Sunday OS 的核心使用场景是**个人伴侣型 AI**——每天聊天、陪伴、记事。在这种场景下：
- "好的回复"是高度主观的（你喜欢简洁、我喜欢详细）
- DeepMind (NeurIPS 2025) 证明：没有人是"平均用户"
- PLUS (ICLR 2026) 证明：个性化偏好摘要比默认模型 win rate 高 72%
- VAC (2026) 证明：自然语言反馈比标量评分好 6-13%

---

## 决策

建一个**对齐 2026 前沿的个人偏好学习系统**，核心思路：

**"用户说的一句话 → LLM 解析为结构化偏好 → 注入 system prompt → 恢复更好的"**

而非传统的"点 👍 → +0.01 → 15 天后慢慢漂移"。

### 三层架构

```
显式反馈 (👍👎 + 文字)
  → quality 即时微调 (+0.01 / -0.02)
  → NL 文字被 LLM 解析为结构化偏好
  → 偏好写入 SQLite 档案

偏好注入 (每次聊天)
  → system_prompt += "[用户偏好]\n- 用户喜欢简洁直接的回复"
  → 不换引擎，换指令（VAC 发现 80% 的"不好"是指令不够精准）

日志追踪 (feedback_log 表)
  → 每条反馈记录 {user_id, engine, rating, text, parsed_result}
  → 未来可做 CPS 关联分析、偏好漂移检测
```

### 为什么不是传统的 RLHF/DPO

| 传统 RLHF | 本方案 |
|---|---|
| 离线训练，需要大量标注 | 在线学习，每次聊天即反馈 |
| 一个模型服务所有人 | 每个用户独立的偏好档案 |
| 标量奖励信号 | 自然语言偏好（NLF, VAC 2026） |
| 需要 GPU 资源 | 只需 ~100 tokens/次 的 LLM 解析 |

### 关键设计决策

1. **偏好是自然语言，不是数字向量** — 遵循 PLUS 模式，`UserPreferences.to_prompt_block()` 生成可读的中文偏好文本直接注入 prompt
2. **PreferenceStore 独立于 MemoryStore** — 复用一个 SQLite 连接（sunday.db），但用独立的表避免与记忆系统耦合
3. **解析失败不阻塞** — `parse_feedback()` 的 fallback 永远返回 neutral，避免"引擎挂了 → 偏好也挂了"
4. **质量调整权重小** — ±0.01/0.02 的单次调整确保不会因为一两句话就颠覆路由

---

## 数据流

```
用户点击 👍
  → POST /api/feedback {rating:1, engine_id:"sunday-chat"}
  → ENGINES 中 sunday-chat 的 quality += 0.01
  → PREF_STORE.log_feedback() 写入 feedback_log

用户点击 👎 + 输入 "太啰嗦了，我只需要结论"
  → POST /api/feedback {rating:-1, feedback_text:"太啰嗦了...", engine_id:"sunday-chat"}
  → ENGINES quality -= 0.02
  → parse_feedback("太啰嗦了，我只需要结论") 调用 LLM
  → 返回 {dimension:"style", style_value:"concise", summary:"用户喜欢简短的回复", action:"prompt_inject"}
  → PREF_STORE.save(prefs) 持久化

下一次聊天
  → build_prompt_with_prefs(user_id, PREF_STORE)
  → system_prompt += "\n\n[用户偏好]\n- 用户喜欢简短的回复"
  → 引擎不变（还是豆包），但回复变短
```

---

## 依赖关系

```
preferences.py       ← 独立（只依赖 sqlite3 stdlib）
feedback_parser.py   → 依赖 engines.router（LLM 解析）
persona/__init__.py  → 依赖 preferences.py（注入偏好）
main.py              → 依赖以上全部（API 端点 + 聊天链路注入）
webchat.py           → 依赖 main.py（POST /api/feedback）
```

---

## 测试

```bash
# 单元测试
python -m pytest tests/ -q  # 28 tests pass

# 集成测试
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $SUNDAY_API_KEY" \
  -d '{"rating":-1,"feedback_text":"太啰嗦了","engine_id":"sunday-chat"}'
# → {"rating":-1,"engine_adjusted":"sunday-chat","parsed_feedback":{...}}

# 偏好查看
curl http://localhost:8000/api/preferences -H "X-API-Key: $SUNDAY_API_KEY"
# → {"user_id":"user_abc123","style":"用户喜欢简短的回复","topics":{},...}
```

---

## 风险与边界

- **quality 浮点精度**：0.01 增量足够细，100 次全 👍 才涨到 1.0 → 不会饱和
- **偏好注入越界**：`to_prompt_block()` 限制 300 字符 → 不会撑爆 context
- **LLM 解析失败**：fallback 到 confidence=0.3 的 neutral 结果
- **向后兼容**：无偏好时 `build_prompt_with_prefs` = `build_system_prompt` 完全不变
- **打开持久化**：偏好存储在 sunday.db 中，服务器重启不丢失

---

## 长期路线图

### Phase 2：隐式行为信号（当前未实现）
| 信号 | 检测方式 | 权重 |
|---|---|---|
| 重问同样问题 | 语义相似度 > 0.8 | 👎 × 0.3 |
| 秒回下一条 | 间隔 < 3s | 👍 × 0.2 |
| 切话题 | 语义漂移检测 | 👎 × 0.15 |
| 长时间沉默 | 间隔 > 5min | 👎 × 0.1 |

### Phase 3：闭环验证（当前未实现）
- CPS 跟踪面板：反馈前后对话轮次变化
- 偏好生效验证：注入后跟踪同类消息回复是否改善
- 衰减机制：30 天未确认的偏好 → confidence 归零

### Phase 4：全栈自适应（当前未实现）
- Per-scenario 偏好矩阵（早晨聊天 vs 晚上工作）
- 隐式偏好发现：LLM 定期分析聊天记录提取未说出的偏好
- 偏好冲突检测与提醒

---

## 参考文献

1. PLUS (ICLR 2026): Personalized RLHF via User Summarization — 偏好摘要注入 prompt，72% win rate
2. VAC (2026): Verbal-Alignment for Customization — NL 反馈比标量评分好 6-13%
3. DeepMind (NeurIPS 2025): Capturing Individual Human Preferences with Reward Features — 无平均用户
4. openclaw-hybrid-memory (2026): 四层反馈架构 — 显式/隐式/轨迹/闭环
5. ADR-007: CPS Metric — 单次会话对话轮次作为北极星指标
6. ADR-011: Quality-First Routing — 本文档的直接前身

---

## 变更状态

- [x] `backend/app/persona/preferences.py` — 新建，UserPreferences + PreferenceStore
- [x] `backend/app/persona/feedback_parser.py` — 新建，LLM 驱动的 NL 反馈解析
- [x] `backend/app/persona/__init__.py` — 新增 build_prompt_with_prefs + get_user_preferences
- [x] `backend/app/main.py` — 新增 POST /api/feedback + GET /api/preferences + POS/api/preferences/update；聊天链路注入偏好
- [x] `backend/app/webchat.py` — 新增 👍👎 按钮 + NL 反馈输入框
- [x] `docs/adr/ADR-012-feedback-learning-system.md` — 本文档
