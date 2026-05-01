import time
import requests
print(len("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))
print(len("ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"))
a = int(time.time())
print(a)

import socket

# 1. 测试连接是否通
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
s.connect(('127.0.0.1', 1883))
print("✅ 连接成功！协议端口正常")

# 2. 发送一条 MQTT Connect 报文（最简单的合法报文）
# MQTT Connect 固定头: 0x10, 剩余长度, 协议名"MQTT"等
# 这里发一个简化版（实际需要完整报文，但先测试连接层）
s.send(b'\x10\x0C\x00\x04MQTT\x04\x02\x00\x3C\x00\x00')
print("✅ 已发送 MQTT Connect 报文")

# 3. 接收响应（如果有）
resp = s.recv(1024)
print(f"✅ 收到响应: {resp.hex()}")
s.close()