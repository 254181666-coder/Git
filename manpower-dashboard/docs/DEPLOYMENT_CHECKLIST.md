# 部署前检查清单

## 一、配置检查

- [ ] 已创建 `.env` 文件并配置好数据库连接
- [ ] 数据库密码已从代码中移除，使用环境变量配置
- [ ] `USE_MYSQL` 配置正确（生产环境建议使用 MySQL）
- [ ] Streamlit 生产配置已正确设置（使用 `config.prod.toml`）
- [ ] `.gitignore` 文件已正确配置，敏感文件不会提交

## 二、依赖检查

- [ ] `requirements.txt` 已更新，包含所有必要依赖
- [ ] 新依赖 `python-dotenv` 已添加
- [ ] 已测试在干净环境中安装依赖无错误

## 三、数据库检查

- [ ] 数据库已正确初始化
- [ ] 数据库连接测试通过
- [ ] 数据库备份策略已规划
- [ ] 数据库用户权限已正确配置

## 四、安全检查

- [ ] 生产环境 `showErrorDetails` 已设置为 `false`
- [ ] `enableXsrfProtection` 已启用
- [ ] 敏感信息（密码、密钥）不在代码中
- [ ] CORS 配置合理

## 五、性能检查

- [ ] 数据库连接池已正确配置
- [ ] Streamlit 缓存 TTL 设置合理
- [ ] 日志级别已设置为 warning 或 error
- [ ] 已考虑使用 Nginx 反向代理

## 六、文件结构检查

- [ ] `.gitkeep` 文件已添加到空目录
- [ ] 临时文件已清理
- [ ] 旧的检查脚本已归档或清理

## 七、Docker 检查（如果使用 Docker）

- [ ] `Dockerfile` 配置正确
- [ ] `docker-compose.yml` 包含必要的 volume 挂载
- [ ] 健康检查配置正确
- [ ] 时区设置正确（Asia/Shanghai）

## 八、启动测试

- [ ] 本地测试启动正常
- [ ] 所有页面功能正常
- [ ] 数据库查询正常
- [ ] 数据导出功能正常

## 九、文档检查

- [ ] README 已更新
- [ ] 部署文档完整
- [ ] 环境变量说明已提供
- [ ] 维护手册（如果需要）已准备

## 快速部署流程

### 方式一：直接部署

1. 复制项目到服务器
2. 创建 `.env` 配置文件
3. 安装依赖：`pip install -r requirements.txt`
4. 使用生产配置启动：`streamlit run app.py --server.port 8502 --server.address 0.0.0.0`

### 方式二：Docker 部署

1. 构建镜像：`docker-compose build`
2. 启动容器：`docker-compose up -d`
3. 查看日志：`docker-compose logs -f`
