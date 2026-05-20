# 数据管道设计

本项目后续按三层数据模型演进：

## Raw 原始层

Raw 层保存 Fun360 / OpenAPI 的接口返回，尽量不改业务字段，只做必要主键落库。

当前代表表：

- `raw_openapi_products`
- `raw_openapi_marketing_orders`
- `raw_openapi_preorders`
- `raw_openapi_members`
- `raw_openapi_member_consume`
- `raw_openapi_mobile_consume`
- `raw_openapi_parent_order_details`

对应入口：

```bash
./run.sh pipeline 2026-05-19
```

只同步 raw：

```bash
python3 scripts/sync_fun360_openapi_raw.py 2026-05-19
```

## Clean 清洗层

Clean 层的职责是把原始事件转成统一口径：

- 营业日：`08:00 ~ 次日 08:00`
- 门店：统一到 `stores.id` / `fun360_shop_id`
- 金额：统一为元
- 商品：统一商品名、分类、大类
- 订单：过滤退款、取消和无效状态
- 关联：把会员消费、预订、开台单详情、商品明细串起来

当前第一版清洗逻辑主要在：

- `scripts/materialize_openapi_daily_metrics.py`
- `scripts/build_daily_metrics_from_openapi_raw.py`（旧对账辅助）

第一阶段正式产出：

- `clean_payment_event`：统一房费、商品、储值、团购支付事件，金额单位为元
- `clean_order_item`：统一商品销售明细、退款数量/金额和商品大类

当前口径：储值销售在充值发生的营业日确认为当日营收。

门店维度必须以 `store_id` + `shop_id` 为主键。门店简称只允许用于 benchmark CSV 的入口匹配和报表展示，不能作为 clean/mart 聚合键。

## Mart 汇总层

Mart 层给报表、看板、系统 API 使用，不直接暴露 raw 结构。

当前代表表：

- `mart_daily_store_revenue`
- `openapi_daily_store_metrics`
- `openapi_product_sales_items`

重新物化 mart：

```bash
./run.sh pipeline 2026-05-19 --skip-raw
```

检查管道结果：

```bash
python3 scripts/check_openapi_pipeline.py 2026-05-19
```

如存在 benchmark CSV，可做对账：

```bash
./run.sh pipeline 2026-05-19 --skip-raw --compare-benchmark
```

## 切换日报数据源的原则

短期内不直接替换 `store_daily` 和 `product_sales_summary`，先用 mart 表持续对账。

当这些指标连续稳定后，再把日报脚本改为读取 mart：

- 收入图：从 `openapi_daily_store_metrics` 读取
- 商品报告：从 `openapi_product_sales_items` 读取
- 同比报告：从 mart 派生日汇总读取

这样可以避免在清洗口径尚未完全确认时影响每日交付。
