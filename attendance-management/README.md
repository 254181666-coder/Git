# 考勤工资管理系统

一个基于 FastAPI 的企业级考勤与工资管理系统。

## 功能特性

- 员工管理
- 店面管理
- 考勤记录
- 请假管理
- 工资核算
- 工资审核
- Excel 导入/导出

## 技术栈

- **后端框架**: FastAPI
- **数据库 ORM**: SQLAlchemy
- **数据库**: MySQL
- **Excel 处理**: Pandas + Openpyxl
- **密码安全**: Passlib + Bcrypt

## 快速开始

### 当前冻结运行入口

当前项目处于从单文件应用向 `app/` 模块化包迁移的中间阶段。迁移尚未完成，`app/` 目录仅作为后续重构草稿保留。

**本地测试和业务验证请统一使用根目录入口：**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

暂不要使用：

```bash
uvicorn app.main:app
```

明天继续测试时，所有业务规则、工资核算、最终确认、考勤导入导出，都以根目录 `main.py` / `models.py` 为准。

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并根据你的环境修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接和管理员账号：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=attendance

# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

### 3. 启动服务

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，访问以下地址：

- 应用首页: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 交互式 API: http://localhost:8000/redoc

## 项目结构

```
考勤管理/
├── main.py              # 当前冻结运行入口，包含完整 API 和业务规则
├── models.py            # 当前生效的数据模型定义
├── app/                 # 模块化迁移草稿，暂不作为运行入口
├── config.py            # 配置管理模块
├── security.py          # 安全工具（密码哈希等）
├── requirements.txt     # Python 依赖列表
├── .env.example         # 环境变量示例
├── .gitignore          # Git 忽略文件配置
└── README.md           # 项目说明文档
```

## 主要模块

### 数据库模型 (models.py)

- `Store`: 店面信息
- `Employee`: 员工信息
- `AttendanceRecord`: 考勤记录
- `AttendanceResult`: 考勤结果
- `PositionAttendanceRule`: 岗位考勤规则
- `LeaveRequest`: 请假申请
- `SalaryRecord`: 工资记录
- `SalaryRule`: 工资规则
- `SalaryStandard`: 工资标准
- `SalaryImportBatch`: 工资导入批次
- `SalaryDraft`: 工资草稿
- `SalaryAuditResult`: 工资审核结果
- `User`: 用户账号
- `OperationLog`: 操作日志
- `AttendanceSettings`: 考勤设置

### API 端点

- `/api/stores`: 店面管理
- `/api/employees`: 员工管理
- `/api/positions`: 岗位管理
- `/api/salary-rules`: 工资规则
- `/api/salary-standards`: 工资标准
- `/api/login`: 用户登录
- `/api/logs`: 操作日志

## 安全建议

1. **生产环境必须修改默认密码**
2. **使用强密码作为管理员密码**
3. **配置正确的 CORS 来源**
4. **使用 HTTPS**
5. **定期备份数据库**
6. **不要将 .env 文件提交到版本控制**

## 开发说明

### 添加新依赖

在 `requirements.txt` 中添加新依赖，然后运行：

```bash
pip install -r requirements.txt
```

### 数据库迁移

本项目使用 SQLAlchemy 的 `create_all()` 来创建表。对于生产环境，建议使用 Alembic 进行数据库迁移管理。

## 优化改进历史

### 安全优化

- 移除硬编码的数据库密码
- 移除硬编码的管理员账号密码
- 使用环境变量管理配置
- 改用 bcrypt 进行密码哈希（更安全）
- 使用动态 token 代替固定 token
- 添加 .gitignore 保护敏感文件

### 架构优化

- 创建独立的配置模块 (config.py)
- 创建安全工具模块 (security.py)
- 添加依赖管理文件 (requirements.txt)
- 添加环境变量示例 (.env.example)

## 许可证

本项目仅供内部使用。
