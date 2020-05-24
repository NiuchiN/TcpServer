import sys
import traceback
import socket
import threading
import select
import datetime
import Def_Enum as enum
import ThreadShareData as share
import Def_SendCmd as def_cmd
import CmdArgParse as Arg
import time


SOCKET_TIMEOUT_SEC = 10
server_ip = "127.0.0.1"
server_port = 49152
listen_num = 5
buffer_size = 1024
list_eClientID = [enum.SensorID.HASS, enum.SensorID.SENSOR1]

shareData = share.ShareData(list_eClientID)
ErrDef = share.ErrDefine()
Lock_SharedQue = threading.Lock()

class Client:
    def __init__(self, ID, con, addr):
        self.clientID = ID
        self.connection = con
        self.addr = addr[0]
        self.port = addr[1]
        self.usableSvcCmd = {}

    # このクライアントで使用できるサービスコマンドの定義
    def defUsableSvcCmd(self):
        # クラスごとに対応するサービスコマンドを定義してオーバライドすること
        pass

    # キューに自分宛てのデータが入るまで無限待ち
    def waitQue(self, val = None):
        return shareData.dict_IsExistMyData[self.clientID].wait(val)

    def clearBuf(self):
        # クライアントへコマンド送信する前に、受信バッファの値をクリアしておく
        rs, _, _ = select.select([self.connection], [], [], 0.1)
        for r in rs:
            self.connection.recv(buffer_size)

    # 共有キューからデータを取り出す
    def dequeueMyData(self, list_Data):
        with Lock_SharedQue:
            return shareData.DequeAllData(self.clientID, list_Data)

    # 共有キューへデータを詰める
    def enqueueMyData(self, eDstID, list_Data):
        with Lock_SharedQue:
            return  shareData.EnqueData(eDstID, list_Data)

    # 自分が管理しているクライアントからコマンド受信
    def recvCmdFromClient(self, res):
        pass

    # 自分が管理しているクライアントにコマンドを送付
    def sendCmdToClient(self, cmdData):
        pass

    # 他のセンサから共有キューを経由して自分宛てのコマンドを受信
    def recvCmdFromAnotherSensor(self, resp_CmdData):
        if not self.dequeueMyData(resp_CmdData):
            print("cmd Error")
            return False

        if not self.usableSvcCmd[enum.SvcID(resp_CmdData[0])]:
            print("クライアントが対応していないSVCだった。")
            self.sendCmdToClient(self.makeErrCmd(enum.ErrConn.NO_EXIST_SVC_ID))
            return False

        return True

    # 別のセンサへレスポンス送信
    # 共有キューにデータを詰める。
    def sendCmdToAnotherSensor(self, eDstID ,list_Data):
        while True:
            if self.enqueueMyData(eDstID, list_Data):
                break

    def procSendDataFromAnoterSensorToClient(self, timeOutSec):
        if not self.waitQue(timeOutSec):
            print("キュー待ちタイムアウト {}".format(self.clientID))
            return False

        resp_CmdData = []
        if not self.recvCmdFromAnotherSensor(resp_CmdData):
            return False
        self.sendCmdToClient(resp_CmdData)
        return True

    # main処理
    def procMain(self):
        pass

class ClientHass(Client):

    def defUsableSvcCmd(self):
        self.usableSvcCmd[enum.SvcID.OK] = True
        self.usableSvcCmd[enum.SvcID.ERR] = True

    # Hassから受信したコマンドの宛先IDを解析
    def parseDstinationID(self, strDstID):
        try:
            eDstID = enum.SensorID(strDstID)
        except ValueError as e:
            print("Dstination SensorID Error no ID {}".format(self.clientID))
            return False, 0

        if not (shareData.dict_IsThreadRun[eDstID]):
            print("Destination SensorID Erro no Working {}".format(self.clientID))
            return False, 0
        return True, eDstID

    # Hassから受信したコマンドのサービスIDを解析
    def parseSvcID(self, recv_CmdData, send_CmdData):
        try:
            enum.SvcID(recv_CmdData[0])
        except ValueError as e:
            print("SvcID Cmd Error {}".format(self.clientID))
            return False

        for cmd in recv_CmdData:
            send_CmdData.append(cmd)

        return True

    # 受信コマンドの解析してセンサ送付用データを作成する
    def parseRecvCmd(self, recv_CmdData, send_CmdData, strDstID):
        # 送付先センサID解析
        res = self.parseDstinationID(strDstID)
        if not res[0]:
            return enum.ErrConn.CLIENTS_NOT_WORKING, 0
        eDstID = res[1]

        # 実行サービスの解析
        if not(self.parseSvcID(recv_CmdData, send_CmdData)):
            return enum.ErrConn.NO_EXIST_SVC_ID, 0

        return enum.ErrConn.NONE_ERR, eDstID

    # HASSクライアントへ送付するNGコマンドを生成
    def makeErrCmd(self, eErrCode):
        return ErrDef.MakeErrResp(eErrCode)

    # HASSクライアントへ送付するOKコマンドを生成
    def makeOkCmd(self, cmdData):
        cmd = def_cmd.OK_SND_CMD
        cmd += cmdData.encode("utf-8")
        cmd += def_cmd.DELIMITER_SND_CMD
        return cmd

    # HASSクライアントからコマンド受信（無限待ちする）
    def recvCmdFromClient(self):
        print("クライアントコマンド受信待ち{}".format(self.clientID))
        res = self.connection.recv(buffer_size)
        if res == def_cmd.CONN_END_CMD:
            return False, 0
        else :
            print("クライアントコマンド受信OK{}".format(self.clientID))
            return True, res

    # HASSクライアントへコマンド送付
    def sendCmdToClient(self, list_CmdData):
        try:
            svcID = enum.SvcID(list_CmdData.pop(0))
            if svcID == enum.SvcID.OK:
                cmd = self.makeOkCmd(list_CmdData.pop(0))
            elif svcID == enum.SvcID.ERR:
                cmd = self.makeErrCmd(list_CmdData.pop(0))

        except ValueError:
            cmd = def_cmd.ERR_SND_CMD
            cmd += def_cmd.DELIMITER_SND_CMD

        self.clearBuf()
        self.connection.send(cmd)

    def procMain(self):
        self.defUsableSvcCmd()
        while True:
            res = self.recvCmdFromClient()
            if not res[0]:
                break

            recv_cmd = res[1]
            recv_CmdData = recv_cmd.decode("utf-8").split(',')
            send_CmdData = []
            strDstID = recv_CmdData.pop(0)

            res = self.parseRecvCmd(recv_CmdData, send_CmdData, strDstID)
            if res[0] == enum.ErrConn.NONE_ERR:
                # ChekOKだったらセンサへコマンド送付
                self.sendCmdToAnotherSensor(res[1], send_CmdData)
            else:
                # CheckNGだったらNGレスポンスをHASSへ返して受信待ちへ戻る
                send_CmdData.append(enum.SvcID.ERR)
                send_CmdData.append(enum.ErrConn.NO_EXIST_SVC_ID)
                self.sendCmdToClient(send_CmdData)
                continue

            # キューにセンサからのレスポンスが入るまでは受信待ち
            self.procSendDataFromAnoterSensorToClient(SOCKET_TIMEOUT_SEC * 2)

class ClientSensor(Client):

    def defUsableSvcCmd(self):
        self.usableSvcCmd[enum.SvcID.READ] = True
        self.usableSvcCmd[enum.SvcID.WRITE] = True
        self.usableSvcCmd[enum.SvcID.SVC] = True

    # READコマンド生成（cmdData[0] = ReadVarID)
    # 生成コマンド例： b"READ,ReadVarID\r\n"
    def makeReadCmd(self, cmdData):
        cmd = def_cmd.READ_SND_CMD
        cmd += cmdData[0].encode("utf-8")
        cmd += def_cmd.DELIMITER_SND_CMD
        return cmd

    # WRITEコマンド生成（cmdData[0] = WriteVarID, cmdData[1] = WriteVal）
    # 生成コマンド例： b"WRITE,WriteVarID,WritVal\r\n"
    def makeWriteCmd(self, cmdData):
        cmd = def_cmd.WRITE_SND_CMD
        cmd += cmdData[0].to_bytes(2, "little")
        cmd += def_cmd.SEP_SND_CMD
        cmd += cmdData[1].to_bytes(2, "little")
        cmd += def_cmd.DELIMITER_SND_CMD
        return cmd

    # SVCコマンド生成（cmdData[0] = SvcID, cmdData[n] = data)
    # 生成コマンド例：b"SVC,SvcID,data・・・\r\n"
    def makeSvcCmd(self, cmdData):
        cmd = def_cmd.SVC_SND_CMD
        # TODO: センサ毎のサービスコマンド生成
        cmd += def_cmd.DELIMITER_SND_CMD
        return cmd

    # HASSクライアントからコマンド受信（タイムアウト付き）
    def recvCmdFromClient(self):
        rs, _, _ = select.select([self.connection], [], [], SOCKET_TIMEOUT_SEC)
        if len(rs) == 0:
            # 受信タイムアウト
            return False, 0

        res = self.connection.recv(buffer_size)
        return True, res

    # クライアントにコマンド送信
    def sendCmdToClient(self, list_cmdData):
        svcID = enum.SvcID(list_cmdData.pop(0))
        if svcID == enum.SvcID.READ:
            cmd = self.makeReadCmd(list_cmdData)
        elif svcID == enum.SvcID.WRITE:
            cmd = self.makeWriteCmd(list_cmdData)
        elif svcID == enum.SvcID.SVC:
            cmd = self.makeSvcCmd(list_cmdData)
        else:
            cmd = def_cmd.ERR_SND_CMD
            cmd += def_cmd.DELIMITER_SND_CMD

        self.clearBuf()
        self.connection.send(cmd)

    # ERRレスポンスを作成
    def makeErrRespForHass(self, eErrCode):
        sndData = []
        sndData.append(enum.SvcID.ERR.value)
        sndData.append(str(eErrCode.value))
        return sndData

    # OKレスポンスを作成
    def makeOKRespForHass(self, byData):
        sndData = []
        sndData.append(enum.SvcID.OK.value)
        sndData.append(byData)
        return sndData

    def procSendDataFromAnoterSensorToClient(self):
        self.waitQue()
        resp_CmdData = []
        if not self.recvCmdFromAnotherSensor(resp_CmdData):
            return False
        print("受信データをクライアントへ {}".format(self.clientID))
        self.sendCmdToClient(resp_CmdData)
        return True

    def procMain(self):
        self.defUsableSvcCmd()
        while True:
            print("他センサデータ受信待ち　{}".format(self.clientID))
            if not self.procSendDataFromAnoterSensorToClient():
                continue

            res = self.recvCmdFromClient()
            if not res[0]:
                print("SVC 実行タイムアウト {}".format(self.clientID))
                self.sendCmdToAnotherSensor(enum.SensorID.HASS, self.makeErrRespForHass(enum.ErrConn.SVC_TIMEOUT))
                continue

            print(res[1])
            self.sendCmdToAnotherSensor(enum.SensorID.HASS, self.makeOKRespForHass(res[1].decode("utf-8")))  # HASSにレスポンス送信


def ProcClientsConnection(clientsCls, con):
    try:
        clientsCls.procMain()

    except Exception as ex:
        ErrDef.PrintException(ex)
        traceback.print_exc()

    finally:
        print("all finish")
        con.close()

def ClientsHandler(th_number, con, addr):
    # クライアントIDを受信するまで無限待ち
    res = con.recv(buffer_size).decode("utf-8").replace('\\r\\n', '')

    try:
        if res == '':
            return False
        else:
            eClientID = enum.SensorID(res)
    except ValueError as e:
        print("SensorID Cmd Error")
        cmd = ErrDef.MakeErrResp(enum.ErrConn)
        con.send(cmd)
        con.close()
        return

    shareData.dict_IsThreadRun[eClientID] = True
    con.send(def_cmd.ACCEPT_SND_CMD)

    if eClientID == enum.SensorID.HASS:
        hass = ClientHass(enum.SensorID.HASS, con, addr)
        ProcClientsConnection(hass, con)

    elif eClientID == enum.SensorID.SENSOR1:
        s1 = ClientSensor(enum.SensorID.SENSOR1, con, addr)
        ProcClientsConnection(s1, con)

    shareData.dict_IsThreadRun[eClientID] = False
    print("Thread-{} : Closed".format(eClientID.value))

def TcpServerStart():
    # 1.ソケットオブジェクトの作成
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 2.作成したソケットオブジェクトにIPアドレスとポートを紐づける
    tcp_server.bind((server_ip, server_port))

    # 3.作成したオブジェクトを接続可能状態にする
    tcp_server.listen(listen_num)

    print("TCP Server Started!")

    thread_no = 1;

    # 4.ループして接続を待ち続ける
    while True:
        try:
            # クライアント接続待ち
            con, address = tcp_server.accept()
        except KeyboardInterrupt:
            # Ctrl + C でプログラム終了
            sock.close()
            exit()
            break

        print("{} : {}  Connection Open!".format(address[0], address[1]))
        thread = threading.Thread(target = ClientsHandler, args = (thread_no, con, address), daemon = True)
        thread.start()
        thread_no +=1

if __name__ == "__main__":
    args = Arg.get_args()
    if args.addr:
        server_ip = args.addr
    if args.port:
        server_port = args.port

    print("Server IP = {}, Port = {}".format(server_ip, server_port))
    TcpServerStart()

