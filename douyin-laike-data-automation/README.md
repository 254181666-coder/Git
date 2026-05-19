# 本地生活团购数据自动化试点

这个目录用于推进 12 家独立商家主体的抖音来客和美团团购数据自动化。第一阶段先跑通抖音官方 API 数据闭环，同时按同一套口径预留美团团购数据管理、自动统计分析和对账能力。

## 明天的目标

1. 选定 1 家试点店。
2. 完成抖音开放平台「生活服务商家应用」和该商家主体的授权绑定。
3. 验证能否访问门店、订单、核销、退款、商品/套餐数据。
4. 把试点流程沉淀为可复制步骤。

## 文件说明

- [docs/authorization-pilot.md](docs/authorization-pilot.md)：现场授权步骤和验收标准。
- [data/authorization-ledger.csv](data/authorization-ledger.csv)：12 家商家主体授权台账。
- [data/api-verification-checklist.csv](data/api-verification-checklist.csv)：试点接口验证清单。
- [docs/data-fields.md](docs/data-fields.md)：第一阶段需要确认的数据口径。
- [docs/order-query-collection.md](docs/order-query-collection.md)：订单查询数据采集脚本和验证步骤。
- [docs/meituan-groupbuy-integration.md](docs/meituan-groupbuy-integration.md)：美团团购数据接入和对账方案。
- [docs/dashboard.md](docs/dashboard.md)：店铺管理和订单采集后台。

## 订单查询采集

第一版数据采集优先使用抖音生活服务 `订单查询` OpenAPI：

```bash
npm run order:query -- --order-id 1094809189459863475
```

脚本会从本机 `.env` 读取 `DOUYIN_APP_ID`、`DOUYIN_APP_SECRET` 和 `DOUYIN_ACCOUNT_ID`。

## 数据后台

启动内部后台：

```bash
node scripts/dashboard-server.js
```

打开：

```text
http://127.0.0.1:3010
```

后台支持维护店铺 `account_id`、按店铺拉取订单、查看订单列表并导出 CSV。

## 执行原则

- 优先使用抖音官方 API。
- 美团优先使用官方 API、服务商接口或商家后台正式导出，不把页面抓取作为主链路。
- 后台自动登录和下载 Excel 只作为备用方案。
- 第一阶段只做团购订单、核销、退款、商品/套餐、账单和对账，不做员工分析。
