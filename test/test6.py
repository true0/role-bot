import datetime
import os
import re
import threading
import time
from http import HTTPStatus
from dashscope import Application
import numpy as np
import ollama
import torch
import webrtcvad
from pyVoIP.VoIP import VoIPPhone, CallState, InvalidStateError
from config import Config
from emailSender import EmailSender
from vectorProcessor import VectorProcessor
from voiceProcessor import VoiceProcessor
from databaseConn import DatabaseConnection
from kill_thread import kill_thread


class CallPhone:
    def __init__(self, phone_number, email_receiver,
                 phone: VoIPPhone,
                 voice_processor: VoiceProcessor,
                 email_sender: EmailSender,
                 vector_processor: VectorProcessor,
                 db: DatabaseConnection,
                 task_id, container_id):
        # 通话记录ID
        self.call_id = None
        self.is_Call = threading.Event()
        # 手机号
        self.phone_number = phone_number
        # 邮箱接收者
        self.email_receiver = email_receiver
        # 话机对象
        self.phone = phone
        # 语音处理对象
        self.voice_processor = voice_processor
        # 邮件发送对象
        self.email_sender = email_sender
        # 向量处理对象
        self.vector_processor = vector_processor
        # 数据库对象
        self.db = db
        # 容器id
        self.container_id = container_id
        # 任务id
        self.task_id = task_id
        # 配置文件对象
        self.config = Config.config_init()
        # 模型名称
        self.chat_mode_name = self.config.get("Ollama", "model_name")
        # 通话对象
        self.call = None
        # vad模型
        self.vad_break_model = voice_processor.vad_model
        # 存储音频数据
        self.message_voice = []
        # 存储识别音频
        self.message_text = []
        # 是否正在说话
        self.speak = threading.Event()
        # 打断线程结束标志
        self.speak_check_thread = False

        # 线程初始化
        # 音频写回线程
        self.cw = threading.Thread(target=self.call_write, daemon=True)
        # 通话录音线程
        self.cr = threading.Thread(target=self.call_read, daemon=True)
        # 模型生成与音频生成线程
        self.cc = threading.Thread(target=self.call_chat, daemon=True)
        print("话机初始化...")

    def phone_to_call(self):
        try:
            print("开始任务")
            # 插入拨打记录
            # self.call_id = self.db.call_internal(self.phone_number, self.container_id, self.task_id)
            # 清理数据
            self.message_voice.clear()
            # 拨打电话
            self.call = self.phone.call(self.phone_number)
            print(f"{self.phone_number}-拨打中...")
            # 开始时间
            start_time = time.time()
            while True:
                print(self.call.state)
                if time.time() - start_time > 20:
                    print("20秒未接，主动挂断")
                    self.call.hangup()
                    # 设置备注与状态
                    # self.db.call_update_note("20秒未接，主动挂断", self.call_id)
                    # self.db.call_update_status(0, self.call_id)
                    break
                if self.call.state == CallState.ANSWERED:
                    break
                time.sleep(0.2)
            print(self.call.state)
            if self.call.state != CallState.ANSWERED:
                raise InvalidStateError
            self.cr.start()
            self.cw.start()
            self.cc.start()
            print("已接通...")
            print(self.call.state)
            # 设置通话状态接通
            # self.db.call_update_status(1, self.call_id)
            # 等待电话结束
            while self.call.state == CallState.ANSWERED:
                time.sleep(1)
        except InvalidStateError:
            print("电话被挂...")
        except Exception as e:
            print(e)
        finally:
            if self.call.state == CallState.ENDED:
                try:
                    self.call.hangup()
                except InvalidStateError:
                    print("电话无需挂断")

    def call_read(self):
        """
        通话录音线程
        """
        buffer = []  # 持续存储音频的缓冲区
        voice_chunk = []  # 当前检测到语音的音频片段
        silence_flag = True  # 标记是否为静音状态
        dynamic_delay = 1.5  # 动态静音延迟时间
        max_buffer_duration = 3.0  # 最大缓冲区时长（秒）
        last_confident_time = time.time()  # 上次语音检测时间
        confidence_history = []  # 用于平滑置信度
        try:
            while self.call.state == CallState.ANSWERED:
                # 读取音频数据
                audio_data = self.call.read_audio(length=256, blocking=True)
                audio_chunk = self.voice_processor.pcma_to_pcm16(audio_data)
                audio_int16 = np.frombuffer(audio_chunk, np.int16)
                audio_float32 = self.int2float(audio_int16)
                audio_float32 = self.normalize_audio(audio_float32)
                audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)

                # 使用 Silero VAD 检测置信度
                new_confidence = self.vad_break_model(audio_tensor, 16000).item()
                confidence_history.append(new_confidence)
                if len(confidence_history) > 10:  # 滑动窗口平滑
                    confidence_history.pop(0)
                avg_confidence = sum(confidence_history) / len(confidence_history)
                print("\rAverage Confidence: {:.2f}".format(avg_confidence), end="")

                # 将音频数据添加到缓冲区
                buffer.append(audio_chunk)
                if len(buffer) * 256 / 16000 > max_buffer_duration:
                    buffer.pop(0)  # 保证缓冲区长度不超过最大时长

                # 语音检测逻辑
                current_time = time.time()
                if avg_confidence > 0.3:  # 检测到语音
                    self.speak.clear()
                    if silence_flag:  # 切换到语音状态
                        print("\n检测到语音，开始处理...")
                        silence_flag = False
                        last_confident_time = current_time  # 更新语音检测时间
                        voice_chunk.extend(buffer)  # 将缓冲区音频加入语音段
                        buffer.clear()  # 清空缓冲区
                    last_confident_time = current_time  # 更新语音检测时间
                    voice_chunk.append(audio_chunk)
                elif not silence_flag:  # 检测到静音
                    time_since_last_voice = current_time - last_confident_time
                    if time_since_last_voice > dynamic_delay:
                        self.speak.set()
                        self.message_text.clear()
                        self.message_voice.clear()
                        print("\n静音结束，开始识别...")
                        # 处理当前语音段
                        audio_data = b"".join(voice_chunk)
                        result = self.voice_processor.recognition(audio_data)
                        print("语音识别结果：", result)
                        # if len(result) <= 3 and ("你好" not in result):
                        #     not_text_resp = "不好意思，我没听清楚您说什么，能在说一下吗？"
                        #     data = self.voice_processor.get_doubao_voice(not_text_resp)
                        #     # 插入用户内容
                        #     # self.db.call_history(not_text_resp, 0, self.call_id)
                        #     for voice_data in data:
                        #         self.call.write_audio(voice_data)
                        #         if (len(data) / 8000) > 0:
                        #             time.sleep(len(data) / 8000)
                        #         else:
                        #             time.sleep(0.2)
                        # else:
                        self.message_text.append(result)
                        voice_chunk.clear()  # 清空语音段
                        confidence_history = []  # 用于平滑置信度
                        voice_chunk = []  # 当前检测到语音的音频片段
                        silence_flag = True
        except Exception as e:
            print(f"发生错误: {e}")

    def call_chat(self):
        """
        模型生成与音频生成
        """
        start_text = "您好，我们现在在南沙有一个多模态荣誉花园的项目，就在地铁上盖，交通十分方便，现在两万四千元一平米，有兴趣了解一下吗？"
        history = [
            {"role": "system",
             "content": "请你扮演一个对话沟通达人，拥有超过30年的销售经验，你的能力有:1. 幽默表达:你能在适当时候用幽默的段子让沟通更有趣、轻松。2. 当客户表达出不考虑的态度，要积极引导客户重新对项目产生兴趣，不能轻易放弃客户,生成的回复必须带有标点符号，你需要根据记忆的内容，提供100%精准的回答，回复的数据要100%精准不能胡编乱造。如果客户提到房地产以外的问题时，能够100%准确回答，并结合上下文内容进行融合推理回复，并试图引导到房地产项目的相关内容上。不要说简体中文以外的语言，每次回复的内容不能超过100个中文字符。3. 应对负面:面对客户提出的负面信息或否定内容，你能扬长避短，巧妙引导客户重新关注产品优势。"},
            {
                "role": "assistant",
                "content": start_text
            }
        ]
        # 插入开头内容
        # self.db.call_history(start_text, 1, self.call_id)
        opening_voice = self.voice_processor.get_doubao_voice(start_text)
        for voice_data in opening_voice:
            self.call.write_audio(voice_data)
        while self.call.state == CallState.ANSWERED:
            self.speak.wait()
            if self.message_text:
                history.append({"role": "user", "content": self.message_text.pop(0)})
                response = self.chat_llama(history)
                printed_sentences = set()
                buffer = str()
                for i in response:
                    buffer += i
                    sentences = re.split('([，。！？])', buffer)
                    if not self.speak.is_set():
                        break
                    for j in range(0, len(sentences) - 1, 2):
                        if not self.speak.is_set():
                            break
                        sentence = sentences[j] + sentences[j + 1]
                        if sentence not in printed_sentences:
                            try:
                                data = self.voice_processor.get_doubao_voice(sentence)
                                for voice_data in data:
                                    # voice = self.voice_processor.get_voice(sentence)
                                    self.message_voice.append(voice_data)
                            except Exception as e:
                                print("合成错误", e)
                            printed_sentences.add(sentence)
                history.append({"role": "assistant", "content": buffer})
                # 插入用户内容
                # self.db.call_history(buffer, 0, self.call_id)

    def call_write(self):
        """
        音频写回
        :return:
        """
        while self.call.state == CallState.ANSWERED:
            self.speak.wait()
            if self.message_voice:
                data = self.message_voice.pop(0)
                self.call.write_audio(data)
                if (len(data) / 8000) > 0:
                    time.sleep(len(data) / 8000)
                else:
                    time.sleep(0.3)

    def chat_qwen(self, query, session=None):
        responses = Application.call(
            # 若没有配置环境变量，可用百炼API Key将下行替换为：api_key="sk-xxx"。但不建议在生产环境中直接将API Key硬编码到代码中，以减少API Key泄露风险。
            api_key="sk-8cb7a5829d9a497bb45f1196b484d071",
            app_id='38acb37c8a9746e3a21b9007a36b628a',
            session_id=session,
            prompt=query,
            stream=True,  # 流式输出
            incremental_output=True)  # 增量输出
        for response in responses:
            if response.status_code != HTTPStatus.OK:
                raise Exception
            else:
                yield response.output.text

    def chat_llama(self, history: list):
        try:
            response = ollama.chat(model=self.chat_mode_name, messages=history, stream=True, options={"top_p": 0.9})
            print("模型已回复")
            for i in response:
                yield i['message']['content']
        except ollama.ResponseError as e:
            print('Error:', e.error)

    def int2float(self, sound):
        abs_max = np.abs(sound).max()
        sound = sound.astype('float32')
        if abs_max > 0:
            sound *= 1 / 32768
        sound = sound.squeeze()
        return sound

    def normalize_audio(self, audio_float32):
        max_amplitude = np.max(np.abs(audio_float32))
        if max_amplitude > 0:
            audio_float32 = audio_float32 / max_amplitude
        return audio_float32
