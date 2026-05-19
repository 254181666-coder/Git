# 数据后台

轻量后台用于维护 12 家店的平台账号、手动触发数据采集，并把订单、核销、商品、退款、账单等接口数据整理成经营看板。后续会扩展为抖音来客和美团团购统一后台。

## 启动

```bash
node scripts/dashboard-server.js
```

默认监听：

```text
http://127.0.0.1:3010
```

如需改端口：

```bash
DASHBOARD_PORT=3010 DASHBOARD_HOST=127.0.0.1 node scripts/dashboard-server.js
```

## 数据文件

- `data/shops.json`：店铺配置。
- `data/orders.json`：采集到的订单。
- `data/employees.json`：员工/职人绑定数据，当前预留入口，待接入抖音职人/员工绑定接口。
- `data/vouchers.json`：券与核销数据，后续新增。
- `data/refunds.json`：退款数据，后续新增。
- `data/billing.json`：账单/结算数据，后续新增。
- `data/reconciliation-runs.json`：对账结果，后续新增。

## 使用方式

1. 在页面左侧新增店铺，填写店铺名称、`account_id`、可选 `poi_id` 和备注。
2. 在右侧选择店铺和时间范围。
3. 点击“拉取订单”。
4. 查看订单列表，或点击“导出 CSV”。

## 当前看板指标

总览页会基于已采集订单自动计算：

- 店铺数、订单数、支付金额、商家应收、待使用、已退款。
- 客单价、核销/履约率、退款率、待使用/履约中订单。
- 按店铺 GMV 排行。
- 按商品/套餐 GMV 排行。
- 按日期汇总的支付金额趋势。
- 订单/券状态分布。

这些指标先从 `data/orders.json` 直接计算，适合试点阶段快速验证口径。等 12 家店稳定接入后，再把核销、退款、账单数据分别落到 `data/vouchers.json`、`data/refunds.json`、`data/billing.json`，并扩展为跨表对账。

## 分析口径

- 支付金额：订单 `pay_amount` 汇总。
- 商家应收：订单 `receipt_amount` 汇总。
- 客单价：支付金额 / 订单数。
- 核销/履约率：已履约订单数 / 订单数。
- 退款率：已退款订单数 / 订单数。
- 商品排行：按订单中的 `product_id`、`sku_id` 或商品名聚合。
- 日期趋势：优先按支付时间归档，没有支付时间则按创单时间归档。

## 员工/职人数据预留

后台已预留员工/职人页和 API：

- `GET /api/employees`：读取 `data/employees.json`。
- `POST /api/shops/:shopId/employees/sync`：同步入口占位，当前会返回 501，提示待接入 connector。

后续接入前需要确认：

- 开放平台能力：`life.capacity.craftsman_openapi.merchat.craftsman.bind_info.all`。
- 计划接口：`/goodlife/v2/craftsman_openapi/merchat/craftsman/bind_info/all/`。
- 每家店的精确 `account_id` 已确认。
- 商家授权包含员工/职人绑定能力。
- 如果要做员工短视频分析，还需要员工号/品牌号绑定、经营授权和 `business_token`。

## 说明

第一版后台不引入数据库，便于服务器直接运行。后续如果订单量和对账数据增加，可以把 JSON 文件平滑迁移到 SQLite。
