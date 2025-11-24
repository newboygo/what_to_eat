# -*- coding: utf-8 -*-
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import random
import json
import os
import requests
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")

DEFAULT_CONFIG = {
    "shit_probability": 0.1,
    "shit_image_url": "https://img.zcool.cn/community/01d9065e9c8b17a80121651829c3a8.jpg@1280w_1l_2o_100sh.jpg",
    "cooldown_seconds": 60
}

DEFAULT_DATA = {
    "last_used": {}
}

class WhatToEat(Star):
    def __init__(self, context):
        super().__init__(context)
        self.context = context
        self.config = self.load_config()
        self.data = self.load_data()

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            logger.info("未找到配置文件，正在创建默认配置...")
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置。")
            return DEFAULT_CONFIG.copy()

    def load_data(self):
        if not os.path.exists(DATA_PATH):
            with open(DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_DATA, f, ensure_ascii=False, indent=2)
            return DEFAULT_DATA.copy()
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}，使用默认数据。")
            return DEFAULT_DATA.copy()

    def save_data(self):
        try:
            with open(DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据文件失败: {e}")

    def is_admin(self, user_id: str) -> bool:
        admin_ids = self.context.config.get("admin_ids", [])
        return user_id in admin_ids

    def get_user_cooldown_left(self, user_id: str) -> int:
        last = self.data["last_used"].get(user_id, 0)
        now = time.time()
        left = int(self.config["cooldown_seconds"] - (now - last))
        return max(0, left)

    def update_user_used(self, user_id: str):
        self.data["last_used"][user_id] = time.time()
        self.save_data()

    @filter.command("今天吃什么")
    async def what_to_eat(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        group_id = event.get_group_id()
        is_group = group_id is not None

        left_time = self.get_user_cooldown_left(user_id)
        if left_time > 0:
            m, s = divmod(left_time, 60)
            time_str = f"{m}分{s}秒" if m > 0 else f"{s}秒"
            yield event.plain_result(f"你刚吃过，{time_str}后再来问吧。")
            return

        try:
            if event.get_platform_name() == "aiocqhttp":
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                if is_group:
                    member_info = await event.bot.api.call_action('get_group_member_info',
                                                                  group_id=group_id, user_id=user_id)
                    user_name = member_info.get("card", "") or member_info.get("nickname", user_id)
                else:
                    stranger_info = await event.bot.api.call_action('get_stranger_info', user_id=user_id)
                    user_name = stranger_info.get("nick", user_id)
            else:
                user_name = user_id
        except Exception as e:
            logger.warning(f"获取用户昵称失败: {e}")
            user_name = user_id

        avatar_url = f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"

        shit_prob = self.config.get("shit_probability", 0.1)
        if random.random() < shit_prob:
            chain = [
                Comp.Image.fromURL(self.config["shit_image_url"]),
                Comp.Plain(f"\n{user_name}，你今天吃"),
                Comp.Image.fromURL(avatar_url),
                Comp.Plain("💩")
            ]
            yield event.chain_result(chain)
        else:
            try:
                response = requests.get("https://www.themealdb.com/api/json/v1/1/random.php", timeout=5)
                data = response.json()
                if data.get("meals"):
                    food_name = data["meals"][0]["strMeal"]
                else:
                    raise Exception("API 返回空")
            except Exception as e:
                logger.warning(f"获取在线美食失败: {e}，使用本地备选")
                local_foods = [
                    "宫保鸡丁", "麻婆豆腐", "红烧肉", "糖醋里脊", "鱼香肉丝",
                    "水煮牛肉", "回锅肉", "酸辣土豆丝", "番茄炒蛋", "清蒸鲈鱼",
                    "北京烤鸭", "小笼包", "火锅", "螺蛳粉", "扬州炒饭"
                ]
                food_name = random.choice(local_foods)

            chain = [
                Comp.Image.fromURL(avatar_url),
                Comp.Plain(f"\n{user_name}，你今天吃{food_name}。")
            ]
            yield event.chain_result(chain)

        self.update_user_used(user_id)

    @filter.command("设置吃屎概率")
    async def set_shit_prob(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        if not self.is_admin(user_id):
            yield event.plain_result("权限不足，只有管理员可以修改概率。")
            return

        msg = event.get_message_str().strip()
        parts = msg.split()
        if len(parts) < 2:
            yield event.plain_result("用法：设置吃屎概率 [0-1之间的数，例如 0.1]")
            return

        try:
            new_prob = float(parts[1])
            if not (0 <= new_prob <= 1):
                raise ValueError
        except ValueError:
            yield event.plain_result("请输入 0 到 1 之间的数字。")
            return

        self.config["shit_probability"] = new_prob
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            yield event.plain_result(f"已将吃屎概率设置为 {new_prob:.2%}。")
        except Exception as e:
            yield event.plain_result(f"保存配置失败: {e}")

    @filter.command("设置冷却")
    async def set_cooldown(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        if not self.is_admin(user_id):
            yield event.plain_result("权限不足，只有管理员可以修改冷却时间。")
            return

        msg = event.get_message_str().strip()
        parts = msg.split()
        if len(parts) < 2:
            yield event.plain_result("用法：设置冷却 [秒数，例如 60]")
            return

        try:
            new_cd = int(parts[1])
            if new_cd < 0:
                raise ValueError
        except ValueError:
            yield event.plain_result("请输入一个有效的非负整数。")
            return

        self.config["cooldown_seconds"] = new_cd
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            yield event.plain_result(f"已将‘今天吃什么’的冷却时间设置为 {new_cd} 秒。")
        except Exception as e:
            yield event.plain_result(f"保存配置失败: {e}")

register(
    name="what_to_eat",
    description="随机推荐今天吃什么，有概率吃屎，带冷却和管理员配置",
    version="1.4",
    author="YourName"
)(WhatToEat)