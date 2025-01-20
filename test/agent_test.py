import urllib.parse
from datetime import datetime
import json5
import requests
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.gui import WebUI


@register_tool('get_time')
class GetTime(BaseTool):
    description = "获取计算机系统当前时间。"
    parameters = []  # 获取时间无需参数

    def call(self, params: str, **kwargs) -> str:
        current_datetime = datetime.now()
        formatted_time = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        return f"当前系统时间为：{formatted_time}。"


@register_tool('get_day')
class GetDays(BaseTool):
    description = "获取计算机系统当前日期。"
    parameters = []

    def call(self, params: str, **kwargs) -> str:
        today = datetime.now().date()
        return f"今天是{today.year}年{today.month}月{today.day}日"


@register_tool('get_weather')
class GetWeatherData(BaseTool):
    description = "获取今日天气信息。如果没有提供地点信息，需要主动询问用户地点。。"
    parameters = [{
        'name': 'location',
        'type': 'string',
        'description': '需要查询的天气的地方。如果没有提供地点信息则返回None',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        location = json5.loads(params)['location']
        if not location:
            return "请提供地点。"
        response = requests.get(
            f"https://api.seniverse.com/v3/weather/now.json?key=Si9lnzEH5n4dapO_p&location={location}&language=zh-Hans&unit=c")
        if response.status_code == 200:
            parsed_data = response.json()
            location = parsed_data["results"][0]["location"]
            weather = parsed_data["results"][0]["now"]
            last_update = parsed_data["results"][0]["last_update"]
            return f"当前{location['name']}天气：{weather['text']}, 温度{weather['temperature']}℃，更新时间：{last_update}。"


@register_tool('my_image_gen')
class MyImageGen(BaseTool):
    # `description` 用于告诉智能体该工具的功能。
    description = 'AI 绘画（图像生成）服务，输入文本描述，返回基于文本信息绘制的图像 URL。'
    # `parameters` 告诉智能体该工具有哪些输入参数。
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '期望的图像内容的详细描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` 是由 LLM 智能体生成的参数。
        prompt = json5.loads(params)['prompt']
        prompt = urllib.parse.quote(prompt)
        return json5.dumps(
            {'image_url': f'https://image.pollinations.ai/prompt/{prompt}'},
            ensure_ascii=False)


class Agent:
    def __init__(self, llm_cfg, system_instruction, tools):
        self.llm_cfg = llm_cfg
        self.system_instruction = system_instruction
        self.tools = tools
        self.bot = Assistant(llm=self.llm_cfg,
                             system_message=self.system_instruction,
                             function_list=self.tools)
        self.messages = []  # 储存聊天历史

    def send(self, query):
        self.messages.append({'role': 'user', 'content': f'{query}'})  # 将用户请求添加到聊天历史
        response = self.bot.run(messages=self.messages)
        last_response = []
        for message in response:
            last_response = message
        self.messages.extend(last_response)
        return self.messages[-1]['content']


llm_cfg = {
    'model': 'qwen2.5:14b',
    'model_server': 'http://localhost:11434/v1/',  # base_url，也称为 api_base
    'api_key': 'ollama',
    # （可选） LLM 的超参数：
    'generate_cfg': {
        'top_p': 0.9
    }
}

system_instruction = '''你是一个乐于助人的AI助手。my_image_gen
在收到用户的请求后，你应该：
- 如果用户没有提供必要的信息（如地点），主动询问用户。
- 用清晰、友好的语言回复用户。
你总是用中文回复用户。'''

tools = ['get_time', "get_day", 'get_weather', 'my_image_gen',
         'code_interpreter', 'web_extractor']  # `code_interpreter` 是框架自带的工具，用于执行代码。

bot = Assistant(llm=llm_cfg,
                system_message=system_instruction,
                function_list=tools,
                description="agent测试")

if __name__ == '__main__':
    # WebUI(bot).run()
    agent = Agent(llm_cfg, system_instruction, tools)
    while True:
        query = input('请输入你的问题：')
        print(agent.send(query))
