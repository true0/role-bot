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

    def call(self, params: str, **kwargs):
        current_datetime = datetime.now()
        formatted_time = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        return f"当前时间：{formatted_time}。"


@register_tool('get_day')
class GetDays(BaseTool):
    description = "获取计算机系统当前日期。"
    parameters = []  # 获取时间无需参数

    def call(self, params: str, **kwargs):
        today = datetime.now().date()
        return f"今天是{today.year}年{today.month}月{today.day}日"


@register_tool('get_weather')
class GetWeatherData(BaseTool):
    description = "获取今日天气信息。如果没有提供地点信息，需要主动询问用户地点。。"
    parameters = [{
        'name': 'location',
        'type': 'string',
        'description': '需要查询的天气的地方。如果没有提供地点信息，需要主动询问用户。',
        'required': True
    }]

    def call(self, params: str, **kwargs):
        location = json5.loads(params)['location']
        if not location:
            return "请告诉我您想查询哪个地方的天气。"
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


# 步骤 2：配置您所使用的 LLM。
llm_cfg = {
    'model': 'qwen2.5',
    'model_server': 'http://localhost:11434/v1/',  # base_url，也称为 api_base
    'api_key': 'ollama',
    # （可选） LLM 的超参数：
    'generate_cfg': {
        'top_p': 0.9
    }
}

# 步骤 3：创建一个智能体。这里我们以 `Assistant` 智能体为例，它能够使用工具并读取文件。
system_instruction = '''你是一个乐于助人的AI助手。my_image_gen
在收到用户的请求后，你应该：
- 如果用户没有提供必要的信息（如地点），主动询问用户。
- 用清晰、友好的语言回复用户。
你总是用中文回复用户。'''
tools = ['get_time', "get_day", 'get_weather', 'my_image_gen',
         'code_interpreter']  # `code_interpreter` 是框架自带的工具，用于执行代码。
bot = Assistant(llm=llm_cfg,
                system_message=system_instruction,
                function_list=tools,
                description="agent测试",
                name="ai助手")

WebUI(bot).run()
# messages = []  # 这里储存聊天历史
# while True:
#     # 例如，输入请求 "绘制一只狗并将其旋转 90 度"。
#     query = input('用户请求: ')
#     # 将用户请求添加到聊天历史。
#     messages.append({'role': 'user', 'content': query})
#     response = []
#     for response in bot.run(messages=messages):
#         # 流式输出。
#         print(response[0]['content'],end="")
#         # pprint.pprint(response, indent=2)
#     # 将机器人的回应添加到聊天历史。
#     messages.extend(response)
