# 🎲 AI_TRPG

> 一个可扩展、模块化的 AI 主持人跑团系统
> Modular AI-Driven Tabletop RPG Engine

---

## 📌 项目简介

**AI_TRPG** 是一个基于大语言模型（LLM）的智能跑团系统。
它将传统桌面角色扮演游戏（TRPG）的主持人（GM）逻辑抽象为可扩展模块，实现：

* 🧠 AI 主持人自动生成剧情
* 🎙️ 语音合成与角色配音
* 🗂️ 可插拔规则系统（如 COC / DND 等）
* 🧩 模块化包结构，支持工程化部署
* 📦 可打包为独立可执行程序（PyInstaller）

本项目已迁移为标准 Python 包结构：

```
ai_trpg/
│
├── core/          # 核心逻辑（剧情调度、工具函数等）
├── audio/         # 语音模块（TTS 管理等）
├── rules/         # 规则系统（可扩展）
├── state/         # 玩家状态管理
├── ui/            # 前端交互层
└── ...
```

---

## 🏗️ 项目架构

### 1️⃣ 核心层（Core）

* AI 主持人逻辑
* Prompt 构建与上下文管理
* 游戏流程控制
* 工具模块（general_tools）

---

### 2️⃣ 音频系统（Audio）

* 语音合成（TTS）
* 角色音色管理
* 流式播放支持
* 可替换语音引擎

---

### 3️⃣ 规则系统（Rules）

支持为不同跑团规则创建独立目录，例如：

```
rules/
├── coc/
├── dnd/
└── custom/
```

规则可定义：

* 玩家状态栏结构
* 技能系统
* 判定逻辑
* 专属 Prompt 模板

---

### 4️⃣ 状态系统（State）

支持根据不同规则加载不同的状态模板：

```
state/
├── coc/
│   └── status.txt
├── dnd/
│   └── status.txt
```

实现规则与 UI 解耦。

---

## 🚀 快速开始

### 1️⃣ 克隆仓库

```bash
git clone https://github.com/yourname/AI_TRPG.git
cd AI_TRPG
```

---

### 2️⃣ 创建环境（推荐 Conda）

```bash
conda create -n ai_trpg python=3.10
conda activate ai_trpg
pip install -r requirements.txt
```

---

### 3️⃣ 运行

```bash
python main.py
```

或模块方式运行：

```bash
python -m ai_trpg
```

---

## 📦 打包为可执行程序

使用 PyInstaller：

```bash
pyinstaller main.py --onefile --noconsole
```

生成的可执行文件位于：

```
dist/
```

可直接分发给其他玩家运行。

> ⚠️ 若使用包结构，建议在打包前确认 `ai_trpg` 目录已正确识别为包（含 `__init__.py`）。

---

## 🎮 功能特性

* ✅ AI 主持人自动叙事
* ✅ 多玩家支持（可扩展 P2P）
* ✅ 流式文本输出
* ✅ 语音播报
* ✅ 规则插件化
* ✅ 工程化包结构
* ✅ 可独立打包分发

---

## 🧩 插件化设计理念

本项目采用“核心引擎 + 规则插件”的架构：

```
Engine
   │
   ├── Prompt Builder
   ├── State Manager
   ├── Audio Manager
   │
Rules (COC / DND / Custom)
```

优势：

* 不同规则互不干扰
* 便于新增跑团系统
* 支持社区贡献规则包

---

## 📌 未来规划

* [ ] P2P 联机系统
* [ ] 多房间支持
* [ ] Web 前端版本
* [ ] 插件市场
* [ ] 存档系统
* [ ] 可视化角色卡编辑器

---

## 🤝 贡献

欢迎提交：

* 新规则系统
* UI 优化
* 音频扩展
* Prompt 优化方案

---

## 📜 License

MIT License

---

## ✨ 项目愿景

> 让 AI 成为一个真正“可扩展、可部署、可协作”的数字主持人，而不是一次性的对话脚本。

---
