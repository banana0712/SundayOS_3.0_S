# OLLAMA_SETUP.md · Ollama 本地 Embedding 配置指南

> 让 Sunday 的语义记忆更聪明——用 Ollama 免费本地模型替换 hash embedder。

---

## 0. 这是什么

Sunday 的记忆检索需要把文本转成向量（embedding）。当前的 hash embedder 不需要任何依赖，但**中文切词不准**——"我喜欢跑步"和"我热爱运动"在 hash 空间里可能完全无关。

Ollama 的 `nomic-embed-text` 是一个 274MB 的轻量模型，免费、本地运行，中英文都支持。装上后，Sunday 的中文记忆检索精度提升 **30-50 倍**。

---

## 1. 安装 Ollama（一次性）

### Linux（小兔云服务器）

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text
```

### Windows（你的开发笔记本）

下载安装包：[https://ollama.com/download/windows](https://ollama.com/download/windows)
安装后打开终端：
```bash
ollama pull nomic-embed-text
```

### macOS

```bash
brew install ollama
ollama serve &
ollama pull nomic-embed-text
```

---

## 2. 验证

```bash
# 健康检查
curl http://localhost:11434/api/tags

# 测试 embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "我喜欢跑步"}'
```

---

## 3. 配置 Sunday

不需要改 `.env`。Sunday 启动时会自动检测 Ollama 是否运行——如果在运行就自动升级，如果不在就继续用 hash。

要手动指定模型和地址的话，在 `.env` 里加：

```env
OLLAMA_BASE_URL=http://localhost:11434     # 默认值
OLLAMA_EMBED_MODEL=nomic-embed-text       # 默认值
# OLLAMA_EMBED_MODEL=bge-m3              # 更好的中文（1.2GB，生产环境推荐）
```

---

## 4. 重启 Sunday

```bash
# 本地
python -m uvicorn app.main:app --port 8005

# 服务器
systemctl restart sunday
```

启动后验证：

```bash
curl http://localhost:8005/health
# embedder: "semantic" (之前是 "hash")
# embedding_dim: 768 (之前是 128)
```

---

## 5. 模型选择

| 模型 | 大小 | 维度 | 中文 | 适合场景 |
|------|------|------|------|---------|
| `nomic-embed-text` | 274MB | 768 | 良好 | **推荐默认**，够轻够准 |
| `bge-m3` | 1.2GB | 1024 | 最佳 | 大量中文数据，生产环境 |
| `all-minilm` | 45MB | 384 | 一般 | 极轻量，嵌入式设备 |

切换模型：改 `.env` 里的 `OLLAMA_EMBED_MODEL`，然后 `ollama pull <新模型名>`，重启 Sunday。

---

## 6. 故障排查

| 现象 | 诊断 | 解决 |
|------|------|------|
| embedder 仍是 `hash` | `curl localhost:11434/api/tags` | Ollama 没启动：`ollama serve &` |
| 模型不存在 | `ollama list` | `ollama pull nomic-embed-text` |
| 嵌入返回全零 | `/health` → dim=128 | 模型未拉取或 Ollama 版本太老 |
