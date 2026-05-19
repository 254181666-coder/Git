# 美团团购数据接入和对账方案

## 目标

美团侧与抖音侧使用同一套管理要求：围绕团购订单做自动数据统计、分析、导出和对账。第一阶段不做员工分析。

## 数据范围

第一阶段需要覆盖：

- 团购订单明细：订单号、店铺、商品/套餐、支付金额、订单状态、支付时间、更新时间。
- 券与核销：券码或券 ID、券状态、核销时间、核销门店、核销金额。
- 退款：退款单号、原订单号、退款金额、申请时间、成功时间、退款状态。
- 商品/套餐：商品 ID、套餐名、SKU、售价、上下架状态、适用门店。
- 账单/结算：账单日期、订单号或核销单号、应收、实收、平台服务费、补贴、结算金额。

## 接入方式

优先级从高到低：

1. 美团官方 API 或服务商接口：适合自动同步和长期运行。
2. 美团商家后台正式导出 Excel：适合先跑通对账口径。
3. 自动登录后台下载文件：只能作为临时兜底，后续应替换为正式接口或人工导出导入。

## 统一字段

无论美团来源是 API 还是 Excel，入库前统一转换为平台无关字段。

### 订单

```text
platform
shop_id
platform_shop_id
order_id
product_id
product_name
sku_id
sku_name
order_status
pay_amount
receipt_amount
pay_time
update_time
raw
synced_at
```

### 核销

```text
platform
shop_id
order_id
voucher_id
voucher_status
verify_time
verify_amount
platform_shop_id
raw
synced_at
```

### 退款

```text
platform
shop_id
order_id
refund_id
refund_status
refund_amount
refund_apply_time
refund_success_time
raw
synced_at
```

### 账单

```text
platform
shop_id
bill_date
order_id
voucher_id
gross_amount
refund_amount
service_fee
subsidy_amount
settlement_amount
raw
imported_at
```

## 对账逻辑

第一版对账按天、平台、店铺三个维度计算：

- 订单支付金额合计。
- 已核销金额合计。
- 退款金额合计。
- 账单结算金额合计。
- 本地计算应结算金额与平台账单金额差异。
- 差异订单、差异券码、缺失账单记录。

建议先使用以下基础公式：

```text
本地应结算金额 = 已核销金额 - 已退款金额 - 平台服务费 + 平台补贴
对账差异 = 本地应结算金额 - 平台账单结算金额
```

如果美团账单口径里已经扣除了服务费或包含补贴，需要在试点账单里确认后调整公式。

## 后台页面

建议新增或改造这些页面：

- 总览：抖音和美团汇总经营数据。
- 店铺管理：每家店绑定平台、平台店铺 ID、授权状态。
- 订单：支持平台、店铺、日期筛选。
- 券与核销：展示待使用、已核销、退款中、已退款。
- 退款：统计退款金额和退款率。
- 账单：导入或同步平台账单。
- 对账中心：展示差异金额、差异单数和可导出的差异明细。

## 开发顺序

1. 店铺配置增加 `platform`、`platform_shop_id`、`platform_account_id`。
2. 抽出统一订单字段，抖音订单先写入 `platform: "douyin"`。
3. 增加美团 Excel 导入 connector，用样表跑通订单、核销、退款、账单。
4. 增加对账计算模块和对账中心页面。
5. 拿到美团 API 权限后，把 Excel connector 替换或并行为 API connector。
