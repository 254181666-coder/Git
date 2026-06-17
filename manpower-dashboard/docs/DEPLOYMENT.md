# 综合经营数据看板 - 部署指南

## 一、性能优化总结

已完成的性能优化：

1. **数据库连接池优化** - 使用 SQLAlchemy 连接池，复用连接减少开销
2. **查询缓存** - 使用 `@st.cache_data` 装饰器缓存重复查询
3. **配置优化** - 创建了 .streamlit/config.toml 配置文件

## 二、内网穿透方案

### 方案一：使用 ngrok（推荐用于快速测试）

#### 1. 安装 ngrok

```bash
# macOS
brew install --cask ngrok

# 其他系统访问 https://ngrok.com/download 下载
```

#### 2. 配置 ngrok（可选但推荐）

访问 https://ngrok.com 注册账号获取 authtoken，然后运行：

```bash
ngrok config add-authtoken <your-token>
```

#### 3. 一键启动

```bash
# 使用脚本启动（推荐）
./scripts/start_with_ngrok.sh

# 或者手动分步启动
# 终端 1：启动 Streamlit
streamlit run app.py --server.port 8502

# 终端 2：启动 ngrok
ngrok http 8502
```

启动后，ngrok 会显示公网访问地址（例如：https://abc123.ngrok.io）

### 方案二：使用 frp（适合长期使用）

如果需要稳定的内网穿透，可以使用 frp：

1. 下载 frp: https://github.com/fatedier/frp/releases
2. 配置 frps（服务端）和 frpc（客户端）
3. 详细配置见 frp 文档

## 三、公网部署方案

### 方案一：云服务器部署（推荐用于生产环境）

#### 1. 准备云服务器

购买阿里云/腾讯云/华为云等云服务器

#### 2. 环境准备

```bash
# 安装 Python 3.9+
# 安装 MySQL（可选，也可以继续用 SQLite）
# 克隆或上传项目代码
```

#### 3. 安装依赖

```bash
cd /path/to/Manpower
pip install -r requirements.txt
```

#### 4. 配置数据库

修改 `src/config.py` 中的数据库配置

#### 5. 使用 systemd 管理服务（推荐）

创建服务文件 `/etc/systemd/system/ktv-dashboard.service:

```ini
[Unit]
Description=KTV Comprehensive Business Dashboard
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Manpower
ExecStart=/usr/bin/streamlit run app.py --server.port 8502
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ktv-dashboard
sudo systemctl start ktv-dashboard
```

#### 6. 配置 Nginx 反向代理

创建 Nginx 配置文件：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 7. 配置 SSL（可选，使用 Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 方案二：使用 Docker 部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8502

CMD ["streamlit", "run", "app.py", "--server.port", "8502", "--server.address", "0.0.0.0"]
```

创建 `docker-compose.yml`:

```yaml
version: '3'
services:
  dashboard:
    build: .
    ports:
      - "8502:8502"
    restart: always
```

## 四、快速开始

### 本地开发测试

```bash
cd /Users/ann/Desktop/AI/Project/Manpower
streamlit run app.py
```

访问：http://localhost:8502

### 内网穿透测试

```bash
./scripts/start_with_ngrok.sh
```

## 五、注意事项

1. **安全建议：
   
   - 生产环境建议配置身份验证
   - 定期备份数据库
   - 监控服务器资源使用情况

2. **性能建议：**
   
   - 已配置连接池，建议监控连接数
   - 缓存已配置 TTL（缓存过期时间）
   - 建议监控数据库索引优化

3. **日志：
   
   - Streamlit 日志在 `logs/streamlit.log`
