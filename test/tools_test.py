from datetime import datetime
import ollama
import requests

# 定义工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当你想知道现在的时间时非常有用。",
            "parameters": {}  # 获取当前时间无需输入参数
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "当你想查询指定城市的天气时非常有用。",
            "parameters": {  # 查询天气时需要提供位置，因此参数设置为location
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市或县区，比如北京市、杭州市、余杭区等。"
                    }
                }
            },
            "required": [
                "location"
            ]
        }
    }
]


# 获取当前时间的工具函数
def get_current_time():
    current_datetime = datetime.now()
    formatted_time = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    return f"当前时间：{formatted_time}。"


def get_current_weather(location):
    response = requests.get(
        f"https://api.seniverse.com/v3/weather/now.json?key=Si9lnzEH5n4dapO_p&location={location}&language=zh-Hans&unit=c")
    if response.status_code == 200:
        parsed_data = response.json()
        location = parsed_data["results"][0]["location"]
        weather = parsed_data["results"][0]["now"]
        last_update = parsed_data["results"][0]["last_update"]
        return f"当前{location['name']}天气：{weather['text']}, 温度{weather['temperature']}℃，更新时间：{last_update}。"


# 调用模型并处理工具调用
def chat_llama_tools(history: list):
    response = ollama.chat(model="qwen2.5:14b", messages=history, stream=False, tools=tools)
    # 检查是否调用了工具
    if "tool_calls" in response["message"] and response["message"]["tool_calls"]:
        print("模型调用了工具！")
        print("调用的工具:", response["message"]["tool_calls"])
        for tool_call in response["message"]["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            if tool_name == "get_current_time":
                # 执行工具函数
                tool_result = get_current_time()
                print("工具执行结果:", tool_result)

                # 将工具结果返回给模型
                history.append({"role": "assistant", "content": None, "tool_calls": response["message"]["tool_calls"]})
                history.append({"role": "tool", "name": tool_name, "content": tool_result})
                # 再次调用模型，传递工具结果
                response = ollama.chat(model="qwen2.5:14b", messages=history, stream=False)
                print("模型最终回复:", response["message"]["content"])
            if tool_name == "get_current_weather":
                location = tool_call["function"]["arguments"]['location']
                tool_result = get_current_weather(location)
                print("工具执行结果:", tool_result)
                history.append({"role": "assistant", "content": None, "tool_calls": response["message"]["tool_calls"]})
                history.append({"role": "tool", "name": tool_name, "content": tool_result})
                # 再次调用模型，传递工具结果
                response = ollama.chat(model="qwen2.5:14b", messages=history, stream=False)
                print("模型最终回复:", response["message"]["content"])
    else:
        print("模型没有调用工具，直接生成文本内容。")
        print("生成的内容:", response["message"]["content"])

    return response


# 主程序
if __name__ == '__main__':
    history = [{"role": "system", "content": "你是一个智能助手，给你的数据都是准确的，不要说多余的话"},
               {"role": "user", "content": "现在时间多少了"}]
    response = chat_llama_tools(history)
    # print(response)
