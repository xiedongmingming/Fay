"""
感谢北京中科大脑神经算法工程师张聪聪提供FUNASR集成代码
"""
from threading import Thread

import websocket
import json
import time
import ssl

import _thread as thread

from core import wsa_server, song_player

from utils import config_util as cfg


class FunASR:

    def __init__(self):  # 初始化

        self.__URL = "ws://{}:{}".format(cfg.local_asr_ip, cfg.local_asr_port)
        self.__ws = None
        self.__connected = False
        self.__frames = []
        self.__state = 0
        self.__closing = False
        self.__task_id = ''
        self.done = False
        self.finalResults = ""

    def __on_msg(self):

        if "暂停" in self.finalResults or "不想听了" in self.finalResults or "别唱了" in self.finalResults:
            #
            song_player.stop()

    def on_message(self, ws, message):  # 收到WEBSOCKET消息的处理

        try:

            self.done = True
            self.finalResults = message

            wsa_server.get_web_instance().add_cmd({"panelMsg": self.finalResults})

            self.__on_msg()

        except Exception as e:
            #
            print(e)

        if self.__closing:

            try:
                self.__ws.close()
            except Exception as e:
                print(e)

    def on_close(self, ws, code, msg):  # 收到WEBSOCKET错误的处理

        self.__connected = False

        print("### CLOSE:", msg)

    def on_error(self, ws, error):  # 收到WEBSOCKET错误的处理

        print("### error:", error)

    def on_open(self, ws):  # 收到WEBSOCKET连接建立的处理

        self.__connected = True

        def run(*args):

            while self.__connected:

                try:

                    if len(self.__frames) > 0:

                        frame = self.__frames[0]

                        self.__frames.pop(0)

                        if type(frame) == dict:
                            ws.send(json.dumps(frame))
                        elif type(frame) == bytes:
                            ws.send(frame, websocket.ABNF.OPCODE_BINARY)

                        # print('发送 ------> ' + str(type(frame)))

                except Exception as e:

                    print(e)

                time.sleep(0.04)

        thread.start_new_thread(run, ())

    def __connect(self):

        self.finalResults = ""
        self.done = False
        self.__frames.clear()

        websocket.enableTrace(False)

        self.__ws = websocket.WebSocketApp(
            self.__URL,
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error,
            subprotocols=["binary"]
        )

        self.__ws.on_open = self.on_open

        self.__ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def add_frame(self, frame):

        self.__frames.append(frame)

    def send(self, buf):

        self.__frames.append(buf)

    def start(self):

        Thread(target=self.__connect, args=[]).start()

        data = {
            'vad_need': False,
            'state': 'StartTranscription'
        }

        self.add_frame(data)

    def end(self):

        if self.__connected:

            try:

                for frame in self.__frames:

                    self.__frames.pop(0)

                    if type(frame) == dict:
                        self.__ws.send(json.dumps(frame))
                    elif type(frame) == bytes:
                        self.__ws.send(frame, websocket.ABNF.OPCODE_BINARY)

                    time.sleep(0.4)

                self.__frames.clear()

                frame = {'vad_need': False, 'state': 'StopTranscription'}

                self.__ws.send(json.dumps(frame))

            except Exception as e:

                print(e)

        self.__closing = True
        self.__connected = False
