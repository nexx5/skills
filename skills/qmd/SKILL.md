---
name: qmd
description: QMD 本地文档搜索引擎技能。适用于需要索引、搜索和检索 Markdown 文档、知识库、会议记录等文件的场景。当用户需要搜索文档内容、管理文档集合、生成向量嵌入、或使用混合搜索（BM25+向量+重排序）时触发。
---

# QMD - Query Markup Documents

QMD 是一个本地文档搜索引擎，结合 BM25 全文搜索、向量语义搜索和 LLM 重排序，所有模型本地运行。

## 安装检查与安装

### 1. 检查是否已安装

```bash
# 检查 qmd 命令是否可用
qmd --help

# 检查 npm 全局包
npm list -g @tobilu/qmd

# 检查 Node.js 版本（需要 >= 22）
node --version
```

### 2. 安装 QMD

```bash
# 使用 npm 安装
npm install -g @tobilu/qmd

# 或使用 bun 安装
bun install -g @tobilu/qmd
```

### 3. Windows 特殊处理

Windows 上安装后如果 `qmd` 命令无法运行，需同时修复 `qmd.cmd` 和 `qmd.ps1` 两个文件。

**问题现象**：
- 安装成功，`npm list -g @tobilu/qmd` 显示已安装
- 运行 `qmd` 命令报错或无响应

**原因**：npm 生成的 `qmd.cmd` 和 `qmd.ps1` 都依赖 `/bin/sh` 执行 shell 脚本，但 Windows 上 Git Bash 的 shell 路径可能未正确配置。

**修复步骤**：

```powershell
# 1. 找到 npm 全局安装目录
npm config get prefix
# 输出示例：<NPM_PREFIX_DIR>（npm 全局安装目录，各系统不同）

# 2. 确认 qmd.js 存在
Test-Path "$env:APPDATA\npm\node_modules\@tobilu\qmd\dist\cli\qmd.js"
```

修复 `qmd.cmd` 文件，替换为以下内容：

```batch
@ECHO off
SETLOCAL
node "%~dp0\node_modules\@tobilu\qmd\dist\cli\qmd.js" %*
```

修复 `qmd.ps1` 文件，替换为以下内容：

```powershell
#!/usr/bin/env pwsh
$basedir=Split-Path $MyInvocation.MyCommand.Definition -Parent
if ($MyInvocation.ExpectingInput) {
  $input | & node "$basedir/node_modules/@tobilu/qmd/dist/cli/qmd.js" $args
} else {
  & node "$basedir/node_modules/@tobilu/qmd/dist/cli/qmd.js" $args
}
```

**验证修复**：

```powershell
# 刷新 PATH 缓存
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 测试运行
qmd --help
```

### 4. 模型说明

QMD 使用三个本地 GGUF 模型（首次使用时自动下载）：

| 模型 | 用途 | 大小 |
|------|------|------|
| `embeddinggemma-300M-Q8_0` | 向量嵌入（默认） | ~300MB |
| `qwen3-reranker-0.6b-q8_0` | 重排序 | ~640MB |
| `qmd-query-expansion-1.7B-q4_k_m` | 查询扩展（微调） | ~1.1GB |

模型缓存位置：`~/.cache/qmd/models/`

**注意**：BM25 是 SQLite FTS5 全文搜索算法，不是模型，无需额外下载。

#### 使用 HF 镜像下载模型

如果 HuggingFace 访问缓慢，设置 `HF_ENDPOINT` 环境变量使用国内镜像：

```powershell
# PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"
qmd embed
```

#### 中文多语言模型（推荐）

默认 embeddinggemma 模型对中文支持有限，建议替换为 Qwen3-Embedding：

```powershell
# 设置多语言模型
$env:QMD_EMBED_MODEL="hf:Qwen/Qwen3-Embedding-0.6B-GGUF/Qwen3-Embedding-0.6B-Q8_0.gguf"

# 强制重新生成嵌入（切换模型后必须执行）
qmd embed -f
```

切换模型后需重新生成所有向量嵌入，因为不同模型的向量维度不兼容。

### 基础使用流程

```bash
# 1. 添加文档集合
qmd collection add <路径> --name <集合名>

# 2. 添加上下文描述（重要！提升搜索质量）
qmd context add qmd://<集合名> "描述信息"

# 3. 生成向量嵌入
qmd embed

# 4. 搜索文档
qmd search "关键词"           # BM25 快速搜索
qmd vsearch "语义查询"        # 向量语义搜索
qmd query "混合查询"          # 混合搜索+重排序（最佳质量）
```

## 核心工作流

### 1. 集合管理

```bash
# 创建集合
qmd collection add . --name myproject
qmd collection add ~/Documents/notes --name notes --mask "**/*.md"

# 查看集合列表
qmd collection list

# 移除/重命名集合
qmd collection remove <集合名>
qmd collection rename <旧名> <新名>

# 列出集合中的文件
qmd ls <集合名>
qmd ls <集合名>/子目录
```

### 2. 上下文管理

上下文是 QMD 的核心功能，为文档添加描述性元数据以改善搜索结果。

```bash
# 为集合添加上下文
qmd context add qmd://notes "个人笔记和想法"
qmd context add qmd://docs/api "API 文档"

# 添加全局上下文（适用于所有集合）
qmd context add / "项目知识库"

# 查看/移除上下文
qmd context list
qmd context rm qmd://notes/旧路径
```

**最佳实践**：为每个集合和重要子路径添加上下文描述，这能显著提升 LLM 选择文档的准确性。

### 3. 搜索命令

| 命令 | 类型 | 适用场景 |
|------|------|----------|
| `search` | BM25 全文搜索 | 快速关键词匹配 |
| `vsearch` | 向量语义搜索 | 自然语言语义匹配 |
| `query` | 混合+重排序 | 最佳搜索结果质量 |

```bash
# 基础搜索
qmd search "关键词"
qmd query "复杂查询"

# 限制集合
qmd search "API" -c notes

# 控制结果数量和质量
qmd query -n 10 --min-score 0.3 "查询内容"

# 获取所有匹配（需配合 --min-score 使用）
qmd search "关键词" --all --min-score 0.4
```

### 4. 文档检索

```bash
# 按路径获取文档
qmd get "docs/file.md"
qmd get "docs/file.md:50" -l 100  # 从第50行开始，最多100行

# 按 docid 获取（搜索结果中显示）
qmd get "#abc123"

# 批量获取
qmd multi-get "journals/2025-05*.md"
qmd multi-get "doc1.md, doc2.md, #abc123"
qmd multi-get "docs/*.md" --max-bytes 20480
```

### 5. 输出格式

为 AI Agent 工作流设计的输出格式：

```bash
# JSON 输出（结构化结果）
qmd search "关键词" --json -n 10

# 文件列表输出
qmd query "错误处理" --all --files --min-score 0.4

# Markdown 输出
qmd search --md --full "错误处理"

# 查看评分细节
qmd query --json --explain "查询内容"
```

## 高级配置

### 向量嵌入

```bash
# 基础嵌入
qmd embed

# 强制重新嵌入
qmd embed -f

# AST 感知分块（代码文件）
qmd embed --chunk-strategy auto
```

### 多语言支持

对于中文等 CJK 语言，使用 Qwen3-Embedding 模型：

```bash
# Linux/macOS
export QMD_EMBED_MODEL="hf:Qwen/Qwen3-Embedding-0.6B-GGUF/Qwen3-Embedding-0.6B-Q8_0.gguf"

# Windows PowerShell
$env:QMD_EMBED_MODEL="hf:Qwen/Qwen3-Embedding-0.6B-GGUF/Qwen3-Embedding-0.6B-Q8_0.gguf"

# 重新嵌入
qmd embed -f
```

### GPU 加速

```bash
# 指定 GPU 后端
export QMD_LLAMA_GPU="metal"  # 或 vulkan, cuda
export QMD_LLAMA_GPU="false"   # 禁用 GPU

# 强制 CPU 模式
export QMD_FORCE_CPU=1
```

### MCP 服务器

```bash
# 启动 MCP 服务器
qmd mcp

# HTTP 模式
qmd mcp --http                    # <LOCAL_HOST>:8181
qmd mcp --http --daemon           # 后台运行
qmd mcp stop                      # 停止服务
```

## 索引维护

```bash
# 查看状态
qmd status

# 重新索引
qmd update
qmd update --pull  # 先 git pull 再索引

# 清理缓存
qmd cleanup
```

## 性能提示

- **首次运行较慢**：模型首次加载需下载并初始化（约 2.7GB 总量）
- **重排序耗时**：`qmd query` 的重排序模型加载较慢，后续会使用缓存
- **跳过重排序**：使用 `--no-rerank` 参数可加速搜索（牺牲部分质量）
- **GPU 加速**：确保 `QMD_LLAMA_GPU` 设置正确以使用 GPU 加速

## 评分解读

| 分数 | 相关性 |
|------|--------|
| 0.8 - 1.0 | 高度相关 |
| 0.5 - 0.8 | 中等相关 |
| 0.2 - 0.5 | 部分相关 |
| 0.0 - 0.2 | 低相关性 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QMD_LLAMA_GPU` | auto | GPU 后端配置 |
| `QMD_FORCE_CPU` | unset | 强制 CPU 模式 |
| `QMD_EMBED_MODEL` | embeddinggemma | 自定义嵌入模型 |
| `QMD_EMBED_PARALLELISM` | auto | 并行度设置 |
| `QMD_EDITOR_URI` | vscode | 编辑器链接模板 |

## 数据存储

索引存储在 `~/.cache/qmd/index.sqlite`，使用 SQLite 数据库包含：
- 集合配置
- 文档内容
- FTS5 全文索引
- 向量嵌入
- LLM 缓存
