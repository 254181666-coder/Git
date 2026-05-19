# HTTPS 回调地址配置

抖音开放平台如果要求 `https` 回调地址，不能直接使用裸 IP 的 `http://47.94.244.186:8080/...`。推荐配置：

```text
域名 -> 47.94.244.186 -> Nginx HTTPS -> 127.0.0.1:8080 临时回调服务
```

## 需要先准备

- 一个域名或子域名，例如 `douyin-api.yourdomain.com`
- DNS A 记录指向：`47.94.244.186`
- 服务器安全组放行：`80`、`443`
- 服务器安装：Node.js、Nginx、Certbot

## 平台里最终填写

把 `your-domain.example.com` 替换成你的真实域名：

```text
授权/通用回调地址：
https://your-domain.example.com/douyin/callback

SPI 地址：
https://your-domain.example.com/douyin/spi

Webhook 地址：
https://your-domain.example.com/douyin/webhook

健康检查：
https://your-domain.example.com/health
```

## 服务器上启动回调服务

```bash
cd /path/to/抖音数据收集
PORT=8080 node scripts/douyin-callback-server.js
```

建议后续再改成 systemd 常驻服务。试点当天可以先用前台运行，确认平台配置通过。

## Nginx 配置

项目里提供了模板：

```text
deploy/nginx-douyin-callback.conf
```

使用前把里面的：

```text
your-domain.example.com
```

替换成你的真实域名。

## 证书申请示例

以下命令需要在服务器上执行：

```bash
sudo certbot --nginx -d your-domain.example.com
```

如果服务器还没有安装 certbot，需要先按服务器系统安装。阿里云/腾讯云服务器也可以用云厂商免费证书，但 Nginx 配置路径要改成实际证书路径。

## 验证

浏览器打开：

```text
https://your-domain.example.com/health
```

看到类似下面内容说明 HTTPS 回调服务可用：

```json
{"ok":true,"service":"douyin-callback-server"}
```
