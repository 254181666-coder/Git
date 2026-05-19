# 临时回调地址

如果平台允许填写 `http` 和端口，先用这几个地址：

- 授权/通用回调：`http://47.94.244.186:8080/douyin/callback`
- SPI 回调：`http://47.94.244.186:8080/douyin/spi`
- Webhook 回调：`http://47.94.244.186:8080/douyin/webhook`
- 健康检查：`http://47.94.244.186:8080/health`

如果平台强制要求 `https`，需要先给服务器绑定域名并配置 HTTPS 证书，不能直接用裸 IP 的 HTTP 地址。具体步骤见 `docs/https-callback-setup.md`。

## 在服务器上运行

把项目上传到 `47.94.244.186` 后执行：

```bash
cd /path/to/抖音数据收集
PORT=8080 npm run callback
```

确认服务器安全组/防火墙已放行 TCP `8080` 端口。

## 平台配置建议

- IP 白名单：`47.94.244.186`
- SPI 地址：`http://47.94.244.186:8080/douyin/spi`
- Webhook 地址：`http://47.94.244.186:8080/douyin/webhook`
- 授权回调地址：`http://47.94.244.186:8080/douyin/callback`

## 验证

在服务器上启动后，浏览器访问：

```text
http://47.94.244.186:8080/health
```

看到 `{"ok":true,"service":"douyin-callback-server"}` 就说明临时服务可用。
