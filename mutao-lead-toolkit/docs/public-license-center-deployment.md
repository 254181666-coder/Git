# 公网授权中心部署说明

更新时间：2026-06-04

## 部署目标

当前商业化落地先部署“授权中心”后台，不把客户线索、评论、账号登录态或平台授权数据放到公网。公网服务只负责：

- 平台管理员登录后台。
- 生成 3 天、7 天、30 天短授权码。
- 管理授权续期、停用、设备绑定和校验记录。
- 给客户桌面端提供短码激活接口：`POST /api/license/activate-short-code`。
- 给客户桌面端提供授权状态校验接口：`POST /api/license/status`。

## 服务器建议

- 系统：Ubuntu 22.04 LTS 或 24.04 LTS
- 配置：1 核 1G 起步，小规模测试建议 2 核 2G
- 域名：例如 `license.example.com`
- 开放端口：80、443
- Node.js：20 LTS 或 22 LTS
- 反代：Nginx + Let's Encrypt HTTPS

## 目录规划

```text
/opt/mutao-license-center          # 应用代码
/var/lib/mutao-license-center      # 运行数据，不随代码发布覆盖
/etc/mutao-license-center.env      # 生产环境变量
/etc/mutao-license-center/         # 授权私钥
```

## 首次部署

1. 创建运行用户和目录：

```bash
sudo useradd --system --create-home --home-dir /var/lib/mutao-license-center --shell /usr/sbin/nologin mutao
sudo mkdir -p /opt/mutao-license-center /var/lib/mutao-license-center /etc/mutao-license-center
sudo chown -R mutao:mutao /var/lib/mutao-license-center
```

2. 上传代码到 `/opt/mutao-license-center`，安装生产依赖：

```bash
cd /opt/mutao-license-center
npm ci --omit=dev
```

3. 准备生产环境变量：

```bash
sudo cp deploy/license-center.env.example /etc/mutao-license-center.env
sudo nano /etc/mutao-license-center.env
sudo chmod 600 /etc/mutao-license-center.env
```

必须修改：

- `HKT_LICENSE_SERVER_URL=https://你的授权域名`
- `HKT_LICENSE_PRIVATE_KEY_PATH=/etc/mutao-license-center/license-private.pem`

4. 准备授权私钥：

```bash
sudo cp keys/license-private.pem /etc/mutao-license-center/license-private.pem
sudo chown root:mutao /etc/mutao-license-center/license-private.pem
sudo chmod 640 /etc/mutao-license-center/license-private.pem
```

私钥只放服务器和服务方本机，不放客户安装包。

5. 安装 systemd 服务：

```bash
sudo cp deploy/mutao-license-center.service /etc/systemd/system/mutao-license-center.service
sudo systemctl daemon-reload
sudo systemctl enable --now mutao-license-center
sudo systemctl status mutao-license-center
```

6. 配置 Nginx：

```bash
sudo cp deploy/nginx-license-center.conf /etc/nginx/sites-available/mutao-license-center.conf
sudo ln -s /etc/nginx/sites-available/mutao-license-center.conf /etc/nginx/sites-enabled/mutao-license-center.conf
sudo nano /etc/nginx/sites-available/mutao-license-center.conf
sudo nginx -t
sudo systemctl reload nginx
```

把模板里的 `license.example.com` 全部替换为真实域名。

7. 申请 HTTPS 证书：

```bash
sudo certbot --nginx -d license.example.com
```

8. 验证健康检查：

```bash
curl https://license.example.com/api/health
```

正常应返回：

```json
{"ok":true,"service":"license-center"}
```

## 后台初始化

浏览器打开：

```text
https://license.example.com
```

默认平台管理员：

```text
admin / admin123
```

上线后第一件事：登录后台后修改默认管理员密码，或在数据文件中创建新的强密码管理员并停用默认密码。

## 客户端接入

客户桌面端要启用联网短码激活和定期授权校验，启动时配置：

```bash
HKT_LICENSE_SERVER_URL=https://license.example.com
```

客户仍可使用长离线码兜底；联网模式下，短码激活只上传短码、设备码、版本号和产品名。

## 运维命令

查看服务：

```bash
sudo systemctl status mutao-license-center
```

看日志：

```bash
sudo journalctl -u mutao-license-center -f
```

重启：

```bash
sudo systemctl restart mutao-license-center
```

备份运行数据：

```bash
sudo tar -czf mutao-license-center-data-$(date +%F).tgz /var/lib/mutao-license-center
```

## 发布更新

```bash
cd /opt/mutao-license-center
git pull
npm ci --omit=dev
sudo systemctl restart mutao-license-center
curl https://license.example.com/api/health
```

更新前先备份 `/var/lib/mutao-license-center`。

## 上线检查清单

- 域名解析到服务器公网 IP。
- 80、443 已放行，8795 不对公网开放。
- `HKT_LICENSE_CENTER=1`。
- `HKT_AUTO_LICENSE=0`，公网后台不自动使用内置测试授权。
- `HKT_DATA_DIR` 指向 `/var/lib/mutao-license-center`。
- 私钥权限不高于 `640`，且不进入 Git。
- HTTPS 可用，`/api/health` 返回正常。
- 默认管理员密码已更换。
- 已做一次授权码生成、短码激活、续期、停用测试。
