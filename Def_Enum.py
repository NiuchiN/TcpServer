# -*- coding: utf-8 -*-
import enum

class Cmd(enum.Enum):
    def value_of(self, target):
        for e in self:
            if e.value == target:
                return e
        raise ValueError("{}は有効値ではありません。".format(target))


class SensorID(Cmd):
    HASS = "h01"
    SENSOR1 = "s01"


class SvcID(Cmd):
    READ    = "READ"    # センサの値を読むコマンド。コマンド例：  READ,readVarID\r\n
    WRITE   = "WRITE"   # センサの値を書くコマンド。コマンド例：  WRITE,writeVarID,writeVal\r\n
    SVC     = "SVC"     # センサ固有のサービス実行コマンド。　コマンド例：　SVC,n,data・・・\r\n
    OK      = "OK"      # HASSへのレスポンス用コマンド。     コマンド例：  OK,data・・・\r\n
    ERR     = "ERR"      # HASSへのレスポンス用コマンド。     コマンド例：  ERR,errNo\r\n

class ErrConn(enum.IntEnum):
    NONE_ERR            = 0
    NO_CLIENTS_ID       = enum.auto()
    NO_EXIST_SVC_ID     = enum.auto()
    SVC_TIMEOUT         = enum.auto()
    CLIENTS_NOT_WORKING = enum.auto()