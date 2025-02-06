from common.config import conf
import os
from datetime import datetime
import json

default_prompt = """请你扮演一个知识百科,用简短的回复回复内容,回答不要超过100字"""


class Message(object):
    def __init__(self, sys_prompt=None):
        if sys_prompt is None:
            self.sys_prompt = conf().get("sys_prompt", default_prompt)
        else:
            self.sys_prompt = sys_prompt
        self.messages = []
        self.reset()

    def reset(self):
        if len(self.messages) > 0:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
            history_dir = os.path.join(config_dir, "history")
            os.makedirs(history_dir, exist_ok=True)
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{current_time}.json"
            filepath = os.path.join(history_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)

        system_item = {"role": "system", "content": self.sys_prompt}
        self.messages = [system_item]

    def set_prompt(self, prompt):
        self.sys_prompt = prompt
        self.reset()

    def add_query(self, query):
        user_item = {"role": "user", "content": query}
        self.messages.append(user_item)

    def add_reply(self, reply):
        assistant_item = {"role": "assistant", "content": reply}
        self.messages.append(assistant_item)
