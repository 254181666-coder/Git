# 宝塔面板部署 HTTPS 回调服务

目标域名：

```text
douyin-api.xyht618.cn
```

目标回调地址：

```text
https://douyin-api.xyht618.cn/douyin/callback
https://douyin-api.xyht618.cn/douyin/spi
https://douyin-api.xyht618.cn/douyin/webhook
```

## 1. 确认 DNS

阿里云 DNS 已添加：

```text
主机记录：douyin-api
记录类型：A
记录值：47.94.244.186
```

等待几分钟后，在本机或服务器测试：

```bash
ping douyin-api.xyht618.cn
```

能解析到 `47.94.244.186` 即可。

## 2. 宝塔添加站点

在宝塔面板：

```text
网站 -> 添加站点
```

填写：

```text
域名：douyin-api.xyht618.cn
根目录：默认即可，例如 /www/wwwroot/douyin-api.xyht618.cn
数据库：不创建
PHP版本：纯静态 或 不启用 PHP
```

提交后，先用浏览器访问：

```text
http://douyin-api.xyht618.cn
```

能看到宝塔默认页或站点页即可。

## 3. 申请 SSL 证书

进入刚创建的网站设置：

```text
网站 -> douyin-api.xyht618.cn -> 设置 -> SSL
```

选择：

```text
Let's Encrypt
```

勾选：

```text
douyin-api.xyht618.cn
```

点击申请。成功后开启：

```text
强制 HTTPS
```

然后访问：

```text
https://douyin-api.xyht618.cn
```

能打开且浏览器不报证书错误即可。

## 4. 目录关系

宝塔里会看到两个目录，它们不是同一个角色：

```text
/www/wwwroot/douyin-api.xyht618.cn
/www/wwwroot/douyin-laike-data
```

含义如下：

- `douyin-api.xyht618.cn` 是宝塔网站目录，负责绑定域名、SSL 和 Nginx 反向代理。
- `douyin-laike-data` 是回调服务代码目录，负责真正运行 `/health`、`/douyin/callback`、`/douyin/spi`、`/douyin/webhook`。
- 域名站点通过反向代理把请求转发到 `127.0.0.1:8080`，8080 上运行的服务可以来自 `douyin-laike-data` 目录。

所以“`douyin-api.xyht618.cn` 的启动文件在 `douyin-laike-data` 里”是允许的。更准确地说：`douyin-api.xyht618.cn` 没有启动文件，它只是域名入口；启动文件属于 `douyin-laike-data` 这个回调服务项目。

## 5. 上传项目或创建回调脚本

推荐代码目录：

```text
/www/wwwroot/douyin-laike-data
```

当前推荐先用 Python 临时回调服务，因为它更适合抖音平台链接测试，会处理 `challenge` 校验：

```text
scripts/douyin-callback-server.py
```

如果使用 Node/PM2，则需要服务器上存在：

```text
scripts/douyin-callback-server.js
package.json
```

不要把 Python 脚本填到宝塔的 Node 项目启动文件里；Node 项目只能启动 `.js`。

## 6. 启动回调服务

### 推荐：先启动 Python 临时服务

SSH 进入服务器后运行：

```bash
cd /www/wwwroot/douyin-laike-data
PORT=8080 HOST=127.0.0.1 python3 scripts/douyin-callback-server.py
```

看到下面输出说明服务已启动：

```text
Douyin callback server listening on http://127.0.0.1:8080
```

这个方式适合先完成抖音平台校验。缺点是 SSH 窗口关闭后服务可能停止，正式长期运行建议后续改成 systemd、Supervisor 或 PM2。

### 可选：使用 Node/PM2 长期运行

在宝塔面板安装：

```text
软件商店 -> PM2管理器
```

然后进入：

```text
PM2管理器 -> 添加项目
```

填写：

```text
项目目录：/www/wwwroot/douyin-laike-data
启动文件：scripts/douyin-callback-server.js
项目名称：douyin-callback
运行用户：www
端口：8080
```

环境变量添加：

```text
PORT=8080
HOST=127.0.0.1
```

启动后确认项目状态为运行中。

如果不用 PM2，也可以先 SSH 临时运行：

```bash
cd /www/wwwroot/douyin-laike-data
PORT=8080 HOST=127.0.0.1 node scripts/douyin-callback-server.js
```

## 7. 配置反向代理

进入站点设置：

```text
网站 -> douyin-api.xyht618.cn -> 设置 -> 反向代理 -> 添加反向代理
```

填写：

```text
代理名称：douyin-callback
目标 URL：http://127.0.0.1:8080
发送域名：$host
```

如果宝塔支持代理目录，填：

```text
代理目录：/
```

保存后，访问：

```text
https://douyin-api.xyht618.cn/health
```

预期返回：

```json
{"ok":true,"service":"douyin-callback-server"}
```

## 8. 抖音平台链接测试

宝塔侧健康检查通过后，在抖音开放平台填写：

```text
授权/通用回调地址：https://douyin-api.xyht618.cn/douyin/callback
SPI地址：https://douyin-api.xyht618.cn/douyin/spi
Webhook地址：https://douyin-api.xyht618.cn/douyin/webhook
```

请求方式选：

```text
POST
```

数据格式选：

```text
JSON
```

然后点击链接测试。

## 9. 常见问题

- `https` 打不开：检查 DNS、80/443 安全组、SSL 是否申请成功。
- `/health` 404：反向代理没有生效，或代理目录不是 `/`。
- `/health` 502：回调服务没启动，或端口不是 `8080`。
- 宝塔 Node 项目提示 `Script not found`：说明 Node 启动文件路径下没有 `.js` 文件；如果当前用的是 Python 临时服务，可以先忽略 Node 项目的未启动状态，或者停掉这个 Node 项目。
- 抖音链接测试失败：看宝塔网站日志和 PM2 日志，确认平台请求是否打到服务器。
