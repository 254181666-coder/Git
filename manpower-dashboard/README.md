# KTV 综合经营分析系统

> 重构后模块化架构，结构清晰，易于维护。

## 📁 项目结构

```
Manpower/
├── app.py                              # Streamlit 主程序入口（唯一入口）
├── README.md                           # 本文件
├── requirements.txt                    # Python依赖
├── 系统使用说明.md                      # 完整使用说明（保留原文档）
├── 每日自动报表任务表.md                 # 定时任务说明
│
├── src/                                # 源代码包
│   ├── __init__.py
│   ├── config.py                       # 全局配置（路径、常量）
│   ├── database.py                     # 数据库操作统一封装
│   ├── utils.py                        # 工具函数
│   └── components/                     # 每个标签页一个独立组件
│       ├── __init__.py
│       ├── business_overview.py        # 📈 基础经营数据
│       ├── product_analysis.py         # 🍺 商品销售分析
│       ├── staff_efficiency.py         # 👥 人效分析
│       ├── room_sales.py               # 🎤 包房销售分析
│       └── qingzhou_daily.py           # 📊 轻舟日报分析
│
├── scripts/                            # 数据导入和报表脚本
│   ├── import_data.py                  # 数据导入（Excel → SQLite）
│   ├── generate_reports_standard.py    # 生成HTML/PDF报告
│   ├── daily_auto_report.py            # 每日自动执行全流程
│   └── ... 其他工具脚本
│
├── database/                           # SQLite数据库
│   ├── ktv_analysis.db                 # 主数据库
│   └── backups/                        # 备份目录
│
├── data/
│   ├── source/                         # 源文件（上传的Excel）
│   └── output/                         # 输出报表（HTML/PDF）
│
├── logs/                               # 日志
└── qingzhou_daily/                     # 轻舟日报模块
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/ann/Desktop/AI/Project/Manpower
pip install -r requirements.txt
```

### 2. 启动看板

```bash
streamlit run app.py --server.port 8502
```

访问：http://localhost:8502/

### 3. 日常工作流

1. 将下载的Excel放到 `data/source/` 目录（建议文件名带日期）
2. 导入数据：`python scripts/import_data.py`
3. 生成报表：`python scripts/generate_reports_standard.py 2026-04-10`
4. 在浏览器看板看交互式分析

详细说明见 `系统使用说明.md`。

## 🔧 重构改进

对比原来的结构：

| 问题                 | 改进                               |
| ------------------ | -------------------------------- |
| 根目录两个dashboard文件重复 | 统一到一个入口 `app.py`                 |
| 所有代码堆在一个文件上千行      | 按标签页拆分成独立模块，每个模块几百行，好维护          |
| 数据库连接代码重复          | 统一封装到 `src/database.py`，一处修改全局生效 |
| 常量散落各处             | 统一配置到 `src/config.py`            |
| 工具函数重复             | 整理到 `src/utils.py`               |

## 📊 功能模块

| 模块      | 功能                   |
| ------- | -------------------- |
| 📈 基础经营 | 收入趋势、储值趋势、门店排名       |
| 🍺 商品销售 | 分类占比、门店对比、Top商品、通辽标杆 |
| 👥 人效分析 | 门店人效排名、提成基尼系数、员工明细   |
| 🎤 包房销售 | 包房分类占比、Top商品         |
| 📊 轻舟日报 | 展示自动生成的轻舟日报图表        |

## 🗓️ 定时任务

已配置 crontab：

```
*/5 10-22 * * * cd /Users/ann/Desktop/AI/Project/Manpower && python3 scripts/daily_auto_report.py
```

每天 10:00-22:00 每5分钟检查一次，有新文件自动处理。

## 部署到公网（宝塔面板）

完整步骤见 `docs/宝塔部署说明.md`（如果需要）。

## 维护者

Ann
