# 🐾 CodePet：你的编程桌宠助手

一个可以陪你写代码、监督你写代码、鼓励你写更多代码的 Python 桌面宠物程序。

---

## 🧩 项目愿景

> 「你有没有觉得，有时候一个人写代码很孤独？」

CodePet 是一个陪伴式的桌面宠物，它可以监测你每天使用编程工具的时间和活跃度，以各种方式鼓励你保持学习/创作的节奏，还能通过拟人化的动画反馈增强编程的乐趣。  
🎙️ **现在支持语音对话功能**，你可以直接和你的桌宠说话！

---

## 🔧 项目功能规划

### 🎯 第一阶段：功能 MVP

| 功能模块       | 描述 |
|----------------|------|
| 程序使用检测   | 后台检测 VS Code、PyCharm、Terminal、Jupyter 等编程工具是否正在运行 |
| 键盘敲击统计   | 实时记录你在使用编程工具时的键盘输入次数 |
| 数据记录存储   | 每日统计总编程时间、敲击次数，保存为本地 JSON 或 SQLite 文件 |
| 桌宠基础动画   | 显示一个简单的宠物动画，能根据你当天的活跃度变化表情/状态 |

---

### 🚀 第二阶段：进阶体验优化

| 模块             | 描述 |
|------------------|------|
| 活动窗口识别     | 更精确判断当前窗口是否为编程软件/网页，从而过滤无效敲击 |
| 桌宠行为系统     | 桌宠根据当前状态呈现不同动作，比如开心、困倦、催你写代码等 |
| 成就激励机制     | 根据连续打卡天数、总敲击数等展示成就，激发持续动力 |
| 多语言支持       | 支持中英宠物对话或鼓励语句 |
| 可视化统计面板   | 提供简洁的图表展示你每周的进步情况 |

---

### 🧠 实时语音对话功能（NEW!）

| 功能         | 描述 |
|--------------|------|
| 🎤 语音识别   | 使用火山引擎流式语音识别（ASR），实时识别人类语音输入 |
| 🤖 大模型对话 | 使用火山大语言模型（LLM）理解语义并生成个性化回复 |
| 🔊 语音合成   | 通过火山 TTS 将回复转成音频，宠物“说”出回应 |
| 💬 即时反馈   | 桌宠播放语音并展示动画或气泡，与用户互动 |

---

## 📦 安装依赖

```bash
pip install websocket-client sounddevice simpleaudio requests pyaudio ffmpeg-python

项目结构

codepet/
├── main.py                  # 启动入口
├── config/
│   ├── settings.yaml        # 全局配置（宠物设置、用户配置）
│   └── model_config.json    # 模型和语音引擎配置
├── core/                    # 核心功能模块
│   ├── activity/            # 编程活跃度检测
│   │   ├── tracker.py           # 活动监控（窗口/应用）
│   │   └── keylogger.py         # 键盘敲击记录
│   ├── stats/
│   │   ├── logger.py            # 每日数据写入
│   │   └── db_manager.py        # SQLite 管理器
│   ├── pet/                 # 宠物行为/状态管理
│   │   ├── controller.py        # 动作控制、情绪切换
│   │   └── model.py             # 宠物数据类（状态/心情/行为）
│   ├── voice/               # 语音交互模块
│   │   ├── asr_client.py        # 火山 ASR 接入
│   │   ├── llm_client.py        # 火山 LLM 对话逻辑
│   │   ├── tts_client.py        # 火山 TTS 合成
│   │   └── dialog_manager.py    # 语音整体流程控制器
│   ├── scheduler/           # 定时器、每日任务调度
│   │   └── jobs.py              # 提醒打卡、保存日报等
│   └── events.py            # 全局事件分发中心（用于插件通信）
├── plugins/                 # 插件模块（独立解耦）
│   ├── base.py              # 插件基类定义
│   ├── achievement.py       # 成就系统插件
│   ├── pomodoro.py          # 番茄钟插件
│   └── github_stats.py      # GitHub 贡献图插件（可选联网）
├── ui/                      # 桌面 UI 组件（主界面、动画、托盘）
│   ├── window.py            # 主窗口（Tkinter / PyQt）
│   ├── animator.py          # 播放宠物动画
│   └── tray.py              # 系统托盘菜单
├── assets/                  # 图片、动画帧、音效资源
│   ├── pets/                # 多个宠物模型
│   └── sounds/              # 播报音效等
├── data/                    # 本地数据存储
│   ├── stats.db             # SQLite 数据库
│   ├── logs/                # 日志文件夹
│   └── temp/                # 缓存语音或帧图
├── web/                     # Web 控制台（可选）
│   ├── api.py               # FastAPI 提供设置控制接口
│   └── dashboard.html       # 可视化数据页面（或前端打包）
├── utils/                   # 公共辅助工具
│   ├── time_utils.py
│   ├── audio_utils.py
│   └── system_utils.py
├── requirements.txt
└── README.md

