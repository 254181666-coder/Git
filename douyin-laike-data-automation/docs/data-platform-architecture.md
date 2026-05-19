# 本地生活团购数据平台架构

## 目标

后台不只服务订单查询，而是统一管理 12 家店的抖音来客和美团团购数据采集、统计分析、导出和对账。

第一阶段优先打通：

- 店铺/商户账号管理
- 团购订单查询
- 商品/套餐基础信息
- 退款、核销、券状态
- 财务/账单数据
- 按平台、店铺、商品、日期统计
- 订单、核销、退款、账单之间的差异对账

暂不纳入第一阶段：

- 员工/职人绑定信息
- 员工短视频数据
- 员工业绩归因分析

## 核心对象

### 店铺

用于统一管理采集范围。

字段：

- 平台：`douyin` 或 `meituan`
- 店铺名称
- 商家主体
- 平台商户 ID，例如抖音 `account_id`、美团 `vendor_id`/`shop_id`
- 平台门店 ID，例如抖音 `poi_id`、美团门店 ID
- 授权状态
- 备注
- 数据权限状态

### 数据能力

每类接口作为一个独立数据能力，不写死在订单模块里。抖音和美团使用相同的数据域，平台差异留在 connector 内部处理。

建议能力列表：

| 数据域 | 接口方向 | 作用 |
| --- | --- | --- |
| 订单 | 订单查询 | 订单明细、订单状态、金额、商品、券状态 |
| 商品 | 商品线上数据查询 | 商品/套餐名称、SKU、上下架、适用门店 |
| 门店 | 门店查询 | 门店基础信息、POI 映射 |
| 核销 | 验券/核销记录或券状态查询 | 已核销、待使用、退款中、已退款 |
| 退款 | 团购退款单查询 | 退款金额、退款时间、退款状态 |
| 账单 | 账单详细查询 | 财务对账、结算金额、手续费 |
| 对账 | 本地汇总计算 | 订单金额、核销金额、退款金额、平台账单之间的差异 |

## 美团团购数据

美团数据管理要求与抖音一致，第一阶段只围绕团购经营和对账。

优先接入的数据：

- 团购订单明细
- 券码/券状态/核销明细
- 退款单明细
- 商品/套餐信息
- 门店基础信息
- 账单/结算明细

美团接入方式按优先级：

1. 官方 API 或服务商接口。
2. 商家后台正式导出的订单、核销、退款、账单 Excel。
3. 后台自动登录下载，仅作为临时兜底。

无论来源是 API 还是导出文件，进入系统后统一转换成标准字段，并保留美团原始字段和原始文件/响应。

## 推荐系统分层

### 1. 配置层

管理 12 家店、所属平台和能力权限。

```text
shops
shop_capabilities
```

后台页面：

- 店铺管理
- 能力开关
- 授权状态
- 最近同步状态

### 2. 采集层

每个接口一个 connector。

```text
connectors/douyin/orders.js
connectors/douyin/products.js
connectors/douyin/refunds.js
connectors/douyin/billing.js
connectors/meituan/orders.js
connectors/meituan/vouchers.js
connectors/meituan/refunds.js
connectors/meituan/billing.js
```

每个 connector 做三件事：

1. 组装请求参数。
2. 调用抖音 OpenAPI。
3. 返回标准化结果和原始响应。

### 3. 存储层

第一版可以继续使用 JSON 文件，便于快速上线。

```text
data/shops.json
data/orders.json
data/products.json
data/vouchers.json
data/refunds.json
data/billing.json
data/reconciliation-runs.json
```

数据稳定后迁移 SQLite：

```text
data/local-life-data.sqlite
```

### 4. 分析层

基于标准化数据做统计。

第一阶段看板：

- 订单数
- 支付金额
- 待使用券数量
- 已核销数量
- 退款金额
- 各店排行
- 商品/套餐排行
- 平台账单金额
- 对账差异金额和差异单数

第二阶段看板：

- 店铺经营趋势
- 商品套餐复购分析
- 退款率/核销率
- 账单与订单差异

### 5. 页面层

后台导航建议：

- 总览
- 店铺管理
- 订单
- 商品/套餐
- 券与核销
- 退款
- 账单
- 对账中心
- 数据同步日志
- 导出中心

## 当前代码下一步

当前已有：

- `scripts/douyin-order-query.js`
- `scripts/dashboard-server.js`
- `data/shops.json`
- `data/orders.json`

下一步应重构为：

```text
scripts/dashboard-server.js
scripts/lib/env.js
scripts/lib/platform-client.js
scripts/connectors/douyin/orders.js
scripts/connectors/meituan/orders.js
scripts/connectors/meituan/import-billing.js
data/shops.json
data/orders.json
data/billing.json
data/reconciliation-runs.json
```

这样后续新增接口时，只需要增加 connector 和页面，不会把所有逻辑堆进一个文件。
