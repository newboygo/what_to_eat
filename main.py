# what_to_eat/main.py
import random
import time
import json
import os
import aiohttp
from astrbot.core import PluginBase

class WhatToEatPlugin(PluginBase):
    def __init__(self, context):
        super().__init__(context)
        self.context = context
        self.data_file = os.path.join(context.plugin_data_path, "data.json")
        self.foods = []
        self.load_data()
        self.context.loop.create_task(self.fetch_foods())

    def register(self):
        self.base_info = {
            "name": "今天吃什么",
            "version": "1.0.1",
            "description": "随机推荐今天吃什么，有小概率吃屎。美食数据来自网络。",
            "author": "YourName",
            "repository": "https://github.com/yourname/what_to_eat"
        }

        self.register_message_handler(self.handle_message)
        self.register_command("set_shit_prob", self.set_shit_prob, "设置吃屎概率（管理员）")
        self.register_command("set_cooldown", self.set_cooldown, "设置冷却时间（管理员）")
        self.register_command("refresh_foods", self.refresh_foods, "刷新美食列表（管理员）")

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "last_used": {},
                "shit_prob": 0.1,
                "cooldown": 3600
            }

    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    async def fetch_foods(self):
        url = "https://api.npoint.io/8164f16271253edb851a"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'foods' in data and isinstance(data['foods'], list):
                            self.foods = [food.strip() for food in data['foods'] if food.strip()]
                            return True
        except Exception as e:
            self.context.logger.error(f"获取美食列表失败: {e}")
        return False

    async def refresh_foods(self, params, context):
        if context.user_id not in self.context.admin_ids:
            return "权限不足。"
        if await self.fetch_foods():
            return "美食列表刷新成功！"
        else:
            return "美食列表刷新失败，请查看日志。"

    async def handle_message(self, context):
        message = context.message.strip()
        if message != "今天吃什么":
            return

        user_id = context.user_id
        user_name = context.user_name
        current_time = time.time()

        if user_id in self.data["last_used"]:
            elapsed = current_time - self.data["last_used"][user_id]
            if elapsed < self.data["cooldown"]:
                remain = int(self.data["cooldown"] - elapsed)
                return f"今天你已经吃过了，在等{remain}秒后再吃。"

        foods_to_use = self.foods or ["火锅", "烧烤", "寿司", "披萨", "汉堡", "拉面", "炸鸡", "沙拉", "牛排", "饺子"]

        if random.random() < self.data["shit_prob"]:
            food = "屎"
            reply = f"{user_name}，你今天吃{food}！今天吃屎去吧。"
        else:
            food = random.choice(foods_to_use)
            reply = f"{user_name}，你今天吃{food}。"

        self.data["last_used"][user_id] = current_time
        self.save_data()

        return reply

    async def set_shit_prob(self, params, context):
        if context.user_id not in self.context.admin_ids:
            return "权限不足。"
        try:
            prob = float(params.get("message"))
            if not (0 <= prob <= 1):
                return "概率必须在0到1之间。"
            self.data["shit_prob"] = prob
            self.save_data()
            return f"吃屎概率已设置为{prob:.2f}。"
        except (ValueError, TypeError):
            return "请输入有效的数字。"

    async def set_cooldown(self, params, context):
        if context.user_id not in self.context.admin_ids:
            return "权限不足。"
        try:
            cooldown = int(params.get("message"))
            if cooldown < 0:
                return "冷却时间不能为负数。"
            self.data["cooldown"] = cooldown
            self.save_data()
            return f"冷却时间已设置为{cooldown}秒。"
        except (ValueError, TypeError):
            return "请输入有效的整数。"

def register_plugin(context):
    return WhatToEatPlugin(context)
