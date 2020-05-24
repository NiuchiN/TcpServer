
# センサクライアントへ送信するコマンド文字列の定義
READ_SND_CMD = b"READ,"
WRITE_SND_CMD = b"WRITE,"
SVC_SND_CMD = b"SVC,"

# HASSクライアントへ送信するコマンド文字列の定義
OK_SND_CMD = b"OK,"

# 両クライアントへ送信するコマンド文字列の定義
ACCEPT_SND_CMD = b"ACCEPT\r\n"
ERR_SND_CMD = b"ERR,"

SEP_SND_CMD = b","
DELIMITER_SND_CMD = b"\r\n"

# クライアントから受信するコマンド文字列の定義
CONN_END_CMD = b"END\\r\\n"