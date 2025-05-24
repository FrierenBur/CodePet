# 🐾 CodePet：你的编程桌宠助手 (Spine 动画版)

一个可以陪你写代码、监督你写代码、鼓励你写更多代码的 Python 桌面宠物程序，采用 Spine 2D 骨骼动画技术，带来更流畅、更生动的宠物表现！

---

## 🌟 项目特色 (Spine 版)

* **流畅的骨骼动画**：利用 Spine 的强大功能，宠物拥有更自然的动作、平滑的过渡和丰富的表现力。
* **高效的资源管理**：相比序列帧，Spine 通过骨骼和图集复用，能以更小的资源体积实现更复杂的动画效果。
* **灵活的动画控制**：支持动画混合、动态换肤（未来规划）、程序化控制骨骼（例如头部跟随鼠标，未来规划）等高级特性。
* **核心功能继承**：保留了原版 CodePet 的核心陪伴功能，如编程活跃度监测、状态反馈、语音互动（规划中）等。

---

## 🚀 快速开始 (Spine 版)

### 依赖项

确保你已经安装了 Python 和 PyQt5。

1.  **PyQt5**:
    ```bash
    pip install PyQt5
    ```
2.  **Spine Runtime**:
    本项目使用官方的 `spine-python` 运行时库。你需要：
    * 从 Esoteric Software 的 [Spine Runtimes GitHub 仓库](https://github.com/EsotericSoftware/spine-runtimes) 下载最新的 `spine-python` 运行时。
    * 将下载的 `spine-runtimes-x.x.x/spine-python/spine` 文件夹（通常里面包含 `__init__.py`, `animation.py`, `atlas.py` 等文件）复制到本项目的 `libs/` 目录下 (如果 `libs` 目录不存在，请创建它)，最终路径应为 `CodePet/libs/spine/`。
3.  **其他依赖**：
    请查看 `requirements.txt` 文件，并通过以下命令安装：
    ```bash
    pip install -r requirements.txt
    ```
    *(注意: `requirements.txt` 可能需要更新以包含Spine集成可能引入的新依赖，或者移除不再需要的旧依赖。目前 `spine-python` 本身是纯Python，不直接通过pip安装。)*

### 配置文件

1.  **全局设置 (`config/settings.yaml`)**:
    * 确保 `pet.type` 指向你在 `assets/pets/` 目录下存放了Spine动画资源的角色名 (例如，如果角色是 `cat_spine`，则设置为 `cat_spine`)。
    * 根据需要调整其他用户、宠物、界面和行为参数。
2.  **模型和语音配置 (`config/model_config.json`)**:
    * 如果计划使用语音功能，请配置相关的API密钥等信息。

### 宠物动画资源

1.  使用 Spine 编辑器创建你的宠物角色和动画。
2.  **导出 Spine 资源**：
    * 为每个角色导出一套文件：
        * 骨骼和动画数据：通常是 `.json` 文件 (推荐，便于调试) 或 `.skel` (二进制) 文件。
        * 纹理图集描述：`.atlas` 文件。
        * 纹理图集图片：一张或多张 `.png` 图片。
3.  **存放资源**：
    * 在 `assets/pets/` 目录下，为每个Spine角色创建一个独立的文件夹，例如 `assets/pets/cat_spine/`。
    * 将导出的 `.json` (或 `.skel`)、`.atlas` 和 `.png` 文件放入对应的角色文件夹中。
    * **命名约定 (建议)**：例如，`assets/pets/cat_spine/cat_spine.json`, `assets/pets/cat_spine/cat_spine.atlas`, `assets/pets/cat_spine/cat_spine.png`。
    * 新的动画管理器 (`SpineAnimator` 或修改后的 `Animator`) 会根据角色名加载这些文件。

### 运行程序

从项目的根目录 (`CodePet/`) 运行：
```bash
python main.py

或者，如果遇到导入问题，推荐使用：

Bash

python -m main
🔧 项目结构 (Spine 版适配说明)
CodePet/
├── main.py                  # 应用程序主入口
├── config/                  # 配置文件目录
│   ├── settings.yaml        # 全局配置
│   └── model_config.json    # 模型和语音引擎配置
│   └── config_manager.py    # 配置加载和管理模块
├── core/                    # 核心功能模块
│   ├── pet/                 # 宠物行为和状态管理
│   │   ├── model.py         # 宠物数据模型 (状态、动作、心情枚举等)
│   │   └── controller.py    # 宠物控制器，实现状态机逻辑
│   ├── events.py            # 全局事件分发系统
│   ├── activity/            # (功能保留) 编程活跃度检测
│   ├── stats/               # (功能保留) 数据统计
│   └── voice/               # (功能保留) 语音交互模块
├── ui/                      # 用户界面和动画显示模块
│   ├── window.py            # PetWindow 主窗口类
│   ├── animator_spine.py    # (或修改后的 animator.py) Spine动画逻辑处理
│   ├── render_widget_spine.py # (新增) 用于渲染Spine动画的自定义Qt控件 (例如 QOpenGLWidget)
│   └── tray.py              # (功能保留) 系统托盘菜单
├── assets/                  # 静态资源
│   ├── pets/                # 宠物角色资源根目录
│   │   ├── cat_spine/       # 示例Spine角色 "cat_spine"
│   │   │   ├── cat_spine.json
│   │   │   ├── cat_spine.atlas
│   │   │   └── cat_spine.png
│   │   └── test_spine/      # 另一个示例Spine角色 "test_spine"
│   │       └── ...
│   └── sounds/              # (功能保留) 音效资源
├── libs/                    # 存放第三方库或运行时
│   └── spine/               # 从官方 Spine Runtimes 复制的 spine-python 运行时库
├── data/                    # (功能保留) 本地数据存储
├── plugins/                 # (功能保留) 插件模块
├── utils/                   # (功能保留) 公共辅助工具
├── web/                     # (功能保留) Web控制台
├── requirements.txt         # Python 依赖列表 (可能需要更新)
└── README.md                # 本文件
```

## 🛠️ 开发与集成 Spine 的核心步骤

1. **获取并集成 spine-python 运行时**：将其源代码放入 `libs/spine/`。

2. 创建 `SpineAnimator` 类

    (例如，在 

   ```
   ui/animator_spine.py
   ```

   ，或者大幅修改 

   ```
   ui/animator.py
   ```

   )： 

   - 负责加载指定角色的 Spine 数据 (`.json`/`.skel`, `.atlas`)。
   - 管理 `spine.AnimationState`，处理动画播放、循环、速度等逻辑。
   - 提供 `update(delta_time)` 方法来推进动画。
   - 提供 `get_render_data()` 方法，输出当前帧需要渲染的部件、顶点、纹理坐标等信息。

3. 创建 `SpineRenderWidget` 类

    (例如，在 

   ```
   ui/render_widget_spine.py
   ```

   )： 

   - 继承 `QOpenGLWidget` (推荐以获得硬件加速) 或 `QWidget`。
   - 在初始化时加载 Spine 纹理图集图片到 OpenGL 纹理或 `QPixmap`。
   - 在其 `paintGL()` (或 `paintEvent()`) 方法中，根据 `SpineAnimator` 提供的 `get_render_data()`，使用 OpenGL 指令或 `QPainter` 将当前帧的骨骼动画绘制出来。**这是集成中最具挑战性的部分。**

4. 修改 `PetWindow` 类 ： 

   - 将原有的 `QLabel` 替换为 `SpineRenderWidget` 实例。
   - 实例化并使用新的 `SpineAnimator`。
   - `update_animation` 方法现在会调用 `SpineAnimator.update()` 并触发 `SpineRenderWidget.update()` (请求重绘)。
   - `play_animation` 方法现在会调用 `SpineAnimator.set_action()`。

5. 调整 `core/pet/model.py` 中的 `ActionType`： 

   - 确保 `ActionType` 枚举的值与你在 Spine 编辑器中为各动画命名的名称完全一致。

6. **资源准备**：为你的宠物角色创建 Spine 项目，导出所需的动画和资源文件，并按照新的结构存放到 `assets/pets/角色名/` 目录下。

------

## 💡 未来展望

- 实现更复杂的动画混合（例如，宠物走路时可以同时做其他表情）。
- 支持 Spine 的皮肤 (Skins) 系统，轻松为宠物换装或改变外观。
- 利用 Spine 的事件 (Events) 在动画特定时间点触发程序逻辑。
- 使用 Spine 的IK约束 (IK Constraints) 实现更自然的肢体联动，例如头部/眼睛跟随鼠标。

------

欢迎贡献和提出建议！