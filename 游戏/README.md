# 游戏自动化脚本

单机地下城游戏关卡自动选择与战斗脚本。

## 功能

- 屏幕截图与模板匹配（OpenCV）
- 自动点击关卡、开始战斗、结算界面
- 战斗中自动按键释放技能
- F1 启动/暂停，F12 退出

## 安装依赖

```bash
cd /Users/isaac/工作/游戏
pip install -r requirements.txt
```

## 使用方法

### 1. 截取游戏界面模板

打开游戏，进入以下界面，用截图工具截取对应元素，保存到 `assets/templates/`：

| 文件名 | 含义 | 用途 |
|---|---|---|
| `level_icon.png` | 关卡图标 | 选择关卡 |
| `start_button.png` | 开始战斗按钮 | 进入战斗 |
| `skill_button.png` | 技能按钮/战斗识别 | 判断进入战斗 |
| `again_button.png` | 再次挑战按钮 | 结算后重开 |
| `confirm_button.png` | 确认按钮 | 通用确认 |

截图建议：
- 只截取目标元素本身，周围留少量像素
- 背景尽量稳定（不要截到会动的特效）
- 保存为 PNG 格式

### 2. 修改配置

编辑 `config/config.json`，调整：

- `confidence`：模板匹配阈值（0~1，默认 0.8）
- `click_delay`：点击后等待时间
- `loop_delay`：每轮循环间隔
- `screen_region`：只识别屏幕某区域，格式 `[x, y, width, height]`，设为 `null` 表示全屏
- `states`：状态机流程

### 3. 运行脚本

```bash
python main.py
```

按 **F1** 开始，**F12** 退出。

## 目录结构

```
游戏/
├── main.py              # 主脚本
├── requirements.txt     # Python 依赖
├── config/
│   └── config.json      # 运行配置（首次运行自动生成）
├── assets/
│   ├── templates/       # 模板图片
│   └── samples/         # 可存放参考截图
├── utils/               # 后续可扩展工具模块
└── logs/
    └── game_bot.log     # 运行日志
```

## 继续开发

可以扩展的方向：

1. **多分辨率适配**：缩放模板图片匹配不同分辨率
2. **OCR 识别**：用 easyocr 读取关卡文字、体力数值
3. **血量/能量检测**：识别血条颜色判断是否放技能
4. **异常处理**：体力不足、背包已满、网络断线等弹窗检测
5. **日志统计**：记录刷了多少次、掉了什么材料

## 注意事项

- 仅用于单机游戏个人使用
- 在云游戏平台运行前请确认平台规则
- 运行前把鼠标放到安全位置，按 F12 可随时停止
