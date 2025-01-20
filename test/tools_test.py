import smtplib
from datetime import datetime
import ollama
import requests
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
            "name": "get_day",
            "description": "当你想查询今天是哪天时非常有用。",
            "parameters": {}  # 获取当前时间无需输入参数
        }
    },
    {
        "type": "function",
        "function": {
            "name": "websearch",
            "description": "当你想获取网络上最新的未知信息是非常有用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "你想要查询的问题，目前仅支持中文问题。"
                    }
                }
            },
            "required": [
                "query"
            ]
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
                        "description": "城市或地区，如广东、广西，南宁市、广州市等。"
                    }
                }
            },
            "required": [
                "location"
            ]
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_msg",
            "description": "当你想发送邮件的时候非常有用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "receiver": {
                        "type": "string",
                        "description": "邮件的接收人，如果用户未提供则为None"
                    },
                    "title": {
                        "type": "string",
                        "description": "邮件的标题,生成你认为最合适的"
                    },
                    "body": {
                        "type": "string",
                        "description": "邮件的主要内容,可以生成你认为的尽量美观的邮件html格式"
                    }
                },
                "required": [  # required 是 parameters 的直接子字段
                    "receiver",
                    "title",
                    "body"
                ]
            }
        }
    }
]


# 获取当前时间的工具函数


def get_current_time():
    current_datetime = datetime.now()
    formatted_time = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    return f"当前时间：{formatted_time}。"


def send_msg(receiver, title, body) -> str:
    if not receiver:
        return "未确定收件人"
    msg = MIMEMultipart()
    msg['From'] = "327057576@qq.com"
    msg['To'] = receiver
    msg['Subject'] = title
    msg.attach(MIMEText(body, 'html'))
    try:
        smtp_obj = smtplib.SMTP('smtp.qq.com', 587)
        smtp_obj.starttls()
        smtp_obj.login('327057576@qq.com', 'fghpmlptqwwzbicj')
        smtp_obj.sendmail('327057576@qq.com', receiver, msg.as_string())
        smtp_obj.quit()
        return "邮件发送成功"
    except smtplib.SMTPAuthenticationError as e:
        print("email authentication error:", e)
        return "邮件发送失败，认证错误"
    except Exception as e:
        print("email send fail", e)
        return "邮件发送失败"


def get_day():
    today = datetime.now().date()
    return f"今天是{today.year}年{today.month}月{today.day}日"


def get_current_weather(location):
    response = requests.get(
        f"https://api.seniverse.com/v3/weather/now.json?key=Si9lnzEH5n4dapO_p&location={location}&language=zh-Hans&unit=c")
    if response.status_code == 200:
        parsed_data = response.json()
        location = parsed_data["results"][0]["location"]
        weather = parsed_data["results"][0]["now"]
        last_update = parsed_data["results"][0]["last_update"]
        return f"当前{location['name']}天气：{weather['text']}, 温度{weather['temperature']}℃，更新时间：{last_update}。"


def websearch(query):
    print("拿到的问题为:", query)
    return "功能暂未实现"


# 调用模型并处理工具调用
def chat_llama_tools(history: list):
    response = ollama.chat(model="qwen2.5:14b", messages=history, stream=False, tools=tools)
    print("完整响应:", response)  # 打印完整响应以检查格式

    # 检查是否调用了工具
    if "tool_calls" in response["message"] and response["message"]["tool_calls"]:
        print("模型调用了工具！")
        print("调用的工具:", response["message"]["tool_calls"])

        # 遍历所有工具调用
        for tool_call in response["message"]["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"].get("arguments", {})  # 获取参数

            # 根据工具名称调用对应的函数
            if tool_name == "get_current_time":
                tool_result = get_current_time()
            elif tool_name == "get_day":
                tool_result = get_day()
            elif tool_name == "get_current_weather":
                location = tool_args.get("location", "")
                tool_result = get_current_weather(location)
            elif tool_name == "websearch":
                query = tool_args.get("query", "")
                tool_result = websearch(query)
            elif tool_name == "send_msg":
                receiver = tool_args.get("receiver", None)
                title = tool_args.get("title", "")
                body = tool_args.get("body", "")
                print("发送邮件给:", receiver, "标题:", title, "内容:", body)
                tool_result = send_msg(receiver, title, body)
            else:
                tool_result = "未知工具"

            print(f"工具 {tool_name} 执行结果:", tool_result)

            # 将工具结果添加到历史记录中
            history.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
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
               {"role": "user",
                "content": "帮我给宋珠文songzhuwen@multimodality.cn发一封邮件，告诉他今晚早点睡，明天要上班。"}]
    response = chat_llama_tools(history)
