import json, urllib.request

# 查询华为App信息
payload1 = {
    "jsonrpc": "2.0",
    "id": "app-query-1",
    "method": "message/send",
    "params": {
        "message": {
            "kind": "message",
            "role": "user",
            "messageId": "app-query",
            "parts": [{
                "kind": "text",
                "text": "请协助查询华为应用市场两个App的信息：\n1. com.wzdxy.ssh.h - SSH终端工具类\n2. com.chuckfang.meow - 可能是工具类\n如果能访问华为应用市场页面，请提取App名称、开发者、分类、简介、评分等关键信息。"
            }]
        }
    }
}

req = urllib.request.Request(
    'http://127.0.0.1:8099/',
    data=json.dumps(payload1).encode(),
    headers={'Content-Type': 'application/json', 'Origin': 'http://120.46.86.165'}
)
print(urllib.request.urlopen(req, timeout=20).read().decode())