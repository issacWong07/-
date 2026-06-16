#!/usr/bin/env python3
"""
单机游戏自动化脚本 - 地下城关卡选择

功能：
    - 基于 OpenCV 模板匹配识别游戏界面元素
    - 自动点击关卡、开始战斗、处理结算
    - 支持热键启动/暂停/退出

用法：
    python main.py

热键：
    F1  - 开始/暂停
    F12 - 完全退出
"""

import json
import logging
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from pynput import keyboard

# 禁用 PyAutoGUI 的安全功能（鼠标移动到角落不会触发 FailSafeException）
pyautogui.FAILSAFE = True

PROJECT_ROOT = Path(__file__).parent.resolve()
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
TEMPLATES_DIR = PROJECT_ROOT / "assets" / "templates"
LOGS_DIR = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "game_bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("game_bot")


class GameBot:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = self.load_config(config_path)
        self.running = False
        self.stopped = False
        self.templates = {}
        self.load_templates()

    def load_config(self, path: Path) -> dict:
        """加载配置文件，不存在则创建默认配置"""
        if not path.exists():
            default_config = {
                "confidence": 0.8,
                "click_delay": 0.5,
                "loop_delay": 1.0,
                "screen_region": None,
                "states": {
                    "select_level": {
                        "templates": ["level_icon.png"],
                        "action": "click_center",
                        "next_state": "start_battle",
                    },
                    "start_battle": {
                        "templates": ["start_button.png"],
                        "action": "click_center",
                        "next_state": "in_battle",
                    },
                    "in_battle": {
                        "templates": ["skill_button.png"],
                        "action": "press_keys",
                        "keys": ["q", "w", "e", "r"],
                        "next_state": "settlement",
                        "timeout": 60,
                    },
                    "settlement": {
                        "templates": ["again_button.png", "confirm_button.png"],
                        "action": "click_center",
                        "next_state": "select_level",
                    },
                },
                "initial_state": "select_level",
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(default_config, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"已创建默认配置: {path}")
            return default_config

        return json.loads(path.read_text(encoding="utf-8"))

    def load_templates(self):
        """预加载所有模板图片"""
        if not TEMPLATES_DIR.exists():
            TEMPLATES_DIR.mkdir(parents=True)
            logger.warning(f"模板目录不存在，已创建: {TEMPLATES_DIR}")
            return

        for template_path in TEMPLATES_DIR.glob("*.png"):
            image = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if image is not None:
                self.templates[template_path.name] = image
                logger.info(f"已加载模板: {template_path.name} ({image.shape[1]}x{image.shape[0]})")
            else:
                logger.warning(f"无法加载模板: {template_path.name}")

    def capture_screen(self) -> np.ndarray:
        """截取屏幕，可指定区域"""
        region = self.config.get("screen_region")
        screenshot = pyautogui.screenshot(region=region)
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return screenshot

    def find_template(self, screen: np.ndarray, template_name: str, confidence: float = None) -> tuple | None:
        """在屏幕中查找模板，返回中心点坐标 (x, y)"""
        if template_name not in self.templates:
            logger.warning(f"模板未加载: {template_name}")
            return None

        if confidence is None:
            confidence = self.config.get("confidence", 0.8)

        template = self.templates[template_name]
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2

            # 如果指定了屏幕区域，需要加上区域偏移
            region = self.config.get("screen_region")
            if region:
                center_x += region[0]
                center_y += region[1]

            logger.debug(f"匹配成功: {template_name} ({max_val:.2f}) at ({center_x}, {center_y})")
            return (center_x, center_y)

        return None

    def find_any_template(self, screen: np.ndarray, template_names: list[str]) -> tuple | None:
        """查找任意一个模板，返回第一个匹配到的 (template_name, x, y)"""
        for name in template_names:
            pos = self.find_template(screen, name)
            if pos:
                return (name, pos[0], pos[1])
        return None

    def click(self, x: int, y: int):
        """安全点击指定坐标"""
        logger.info(f"点击: ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(self.config.get("click_delay", 0.5))

    def press_keys(self, keys: list[str]):
        """依次按下按键"""
        for key in keys:
            pyautogui.press(key)
            logger.info(f"按键: {key}")
            time.sleep(0.1)
        time.sleep(self.config.get("click_delay", 0.5))

    def run_state(self, state_name: str) -> str:
        """执行单个状态，返回下一个状态名"""
        states = self.config.get("states", {})
        state = states.get(state_name)
        if not state:
            logger.error(f"未知状态: {state_name}")
            return state_name

        templates = state.get("templates", [])
        action = state.get("action", "click_center")
        next_state = state.get("next_state", state_name)

        logger.info(f"当前状态: {state_name}")
        screen = self.capture_screen()
        match = self.find_any_template(screen, templates)

        if not match:
            logger.info(f"未识别到目标，保持当前状态: {state_name}")
            return state_name

        _, x, y = match

        if action == "click_center":
            self.click(x, y)
        elif action == "press_keys":
            self.press_keys(state.get("keys", []))
        else:
            logger.warning(f"未知动作: {action}")

        return next_state

    def run(self):
        """主循环"""
        current_state = self.config.get("initial_state", "select_level")
        logger.info("脚本已启动，按 F1 暂停/继续，F12 退出")

        while not self.stopped:
            if not self.running:
                time.sleep(0.2)
                continue

            try:
                current_state = self.run_state(current_state)
            except Exception as e:
                logger.exception(f"运行出错: {e}")
                time.sleep(1)

            time.sleep(self.config.get("loop_delay", 1.0))

        logger.info("脚本已退出")

    def toggle(self):
        """启动/暂停切换"""
        self.running = not self.running
        logger.info(f"{'继续' if self.running else '暂停'}")

    def stop(self):
        """完全停止"""
        self.stopped = True
        self.running = False
        logger.info("收到退出信号")


def main():
    bot = GameBot()

    if not bot.templates:
        logger.error("没有加载到任何模板图片。请将游戏界面截图放入 assets/templates/ 目录")
        logger.error("需要至少一张模板图片才能运行")
        sys.exit(1)

    bot_thread = threading.Thread(target=bot.run, daemon=True)
    bot_thread.start()

    def on_press(key):
        try:
            if key == keyboard.Key.f1:
                bot.toggle()
            elif key == keyboard.Key.f12:
                bot.stop()
                return False
        except Exception as e:
            logger.exception(f"热键处理错误: {e}")

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

    bot_thread.join(timeout=2)


if __name__ == "__main__":
    main()
