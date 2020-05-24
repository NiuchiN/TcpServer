# -*- coding: utf-8 -*-
import queue
import threading
import copy
import datetime
from TcpServer import Def_SendCmd as def_cmd
from TcpServer import Def_Enum as enum


class ShareData():
    def __init__(self, list_eClientID):
        self.__list_eClientId = copy.deepcopy(list_eClientID)

        self.__Lock_isThreadRun = threading.Lock()
        self.__dict_IsThreadRun = {}

        self.__Lock_DstQueData = threading.Lock()
        self.__dict_eveIsQueData = {}

        for eID in list_eClientID:
            self.__dict_IsThreadRun[eID] = False
            self.__dict_eveIsQueData[eID] = threading.Event()

        # キューに格納するのはstring型に限定する。それ以外はエラー
        self.__sharedQue = queue.Queue()

    @property
    def dict_IsThreadRun(self):
        with self.__Lock_isThreadRun:
            return self.__dict_IsThreadRun

    @dict_IsThreadRun.setter
    def dict_IsThreadRun(self, val):
        with self.__Lock_isThreadRun:
            self.__dict_IsThreadRun = val

    @property
    def dict_IsExistMyData(self):
        with self.__Lock_DstQueData:
            return self.__dict_eveIsQueData

    # 共有キューから全データ取り出し(EnqueとDequeAllのロックは呼び出しもとでかけること）
    def DequeAllData(self, eClientID, list_Data):
        if self.__dict_eveIsQueData[eClientID].is_set():
            while not self.__sharedQue.empty():
                list_Data.append(self.__sharedQue.get())
        else:
            return False

        self.dict_IsExistMyData[eClientID].clear()
        return True

    # 共有キューにデータを詰め込む(EnqueとDequeAllのロックは呼び出しもとでかけること）
    def EnqueData(self, eDstID, data):
        for eClientId in self.__list_eClientId:
            # 他のセンサ宛てのデータがすでにあればFalse
            if self.dict_IsExistMyData[eClientId].is_set():
                return False

        for d in data:
            if isinstance(d, str):
                self.__sharedQue.put(d)
            else :
                raise ValueError("共有キューに格納できるのはstring型のみです。")

        self.dict_IsExistMyData[eDstID].set()
        return True


class ErrDefine():

    # クライアント送信用のエラーコード生成
    def MakeErrResp(self, errCode):
        respData = def_cmd.ERR_SND_CMD
        errNum = str(int(errCode))
        respData += errNum.encode("utf-8")
        respData += def_cmd.DELIMITER_SND_CMD
        return respData

    def PrintException(self, ex):
        print('Exception: time={}, desc={}'.format(datetime.datetime.now(), ex))
