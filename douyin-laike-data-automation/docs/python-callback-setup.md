# Python 临时回调服务

如果宝塔里的 Node/PM2 一直报错，先不要继续折腾它，直接用 Python 起临时回调服务。

## 文件位置

把这个文件放到服务器：

```text
/www/wwwroot/douyin-laike-data/scripts/douyin-callback-server.py
```

## 启动命令

```bash
cd /www/wwwroot/douyin-laike-data
PORT=8080 HOST=127.0.0.1 python3 scripts/douyin-callback-server.py
```

如果服务器默认 `python3` 不存在，先试：

```bash
python --version
python3 --version
```

## 验证

```bash
curl http://127.0.0.1:8080/health
```

正常返回：

```json
{"ok":true,"service":"douyin-callback-server"}
```

Webhook 连接测试时，如果平台发来 `content.challenge`，服务端必须原样返回：

```json
{"challenge":12345}
```

## 抖音平台地址

和之前一样，平台里填：

```text
https://douyin-api.xyht618.cn/douyin/callback
https://douyin-api.xyht618.cn/douyin/spi
https://douyin-api.xyht618.cn/douyin/webhook
```
