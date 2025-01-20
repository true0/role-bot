import re

import ollama


def chat_llama(history: list):
    try:
        response = ollama.Client(host='http://192.168.88.253:11434').chat(model="llama3.1:8b", messages=history,
                                                                          stream=True, options={"top_p": 0.9})
        print("模型已回复")
        buffer = ""
        for chunk in response:
            if content := chunk['message']['content']:
                buffer += content
                while match := re.search(r'[^，。！？]*[，。！？]', buffer):
                    yield match.group()
                    buffer = buffer[match.end():]
        if buffer.strip():
            yield buffer
    except ollama.ResponseError as e:
        print('Error:', e.error)


if __name__ == '__main__':
    history = [{'role': 'system', 'content': '请你扮演一个知识百科,用简短的回复回复内容,回答不要超过100字'},
               {"role": "user", "content": "喂你好"}]
    printed_sentences = set()
    printed_sentences_list = list()
    response = chat_llama(history)
    for sentence in response:
        if sentence in printed_sentences:  # 跳过已经处理过的句子
            continue
        printed_sentences.add(sentence)
        printed_sentences_list.append(sentence)
    print(''.join(printed_sentences))
    print(printed_sentences_list)
