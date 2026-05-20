# 自有数据清洗与汇总系统规划

## 目标

把项目从“按接口拉数据生成报表”升级为“有稳定数据资产的业务系统”。

核心目标不是先做页面，而是先形成一套可信的数据生产链路：

```text
Fun360 / OpenAPI / 其他来源
        ↓
Raw 原始层
        ↓
Clean 清洗层
        ↓
Mart 汇总层
        ↓
日报、看板、经营分析、预警、API
```

## 设计原则

1. 原始数据可追溯  
   Raw 层保留接口返回和同步时间，不在这一层改业务含义。

2. 清洗规则集中管理  
   门店、营业日、订单状态、退款、商品分类、金额单位等规则只能在 Clean 层定义一次。

3. 指标只在 Mart 层统一暴露  
   页面、日报、分析脚本、API 都查 Mart 层，避免每个脚本各算一套。

4. 先对账，再替换  
   在 mart 与现有日报基准连续对齐之前，不直接替换 `store_daily` 和 `product_sales_summary`。

5. 粒度先行  
   每张事实表先声明“一行代表什么”，再决定字段和汇总方式。

## 分层规划

### Raw 层

职责：接口数据落库、保留原始 JSON、记录同步时间。

当前已有：

- `raw_openapi_products`
- `raw_openapi_marketing_orders`
- `raw_openapi_preorders`
- `raw_openapi_members`
- `raw_openapi_member_consume`
- `raw_openapi_mobile_consume`
- `raw_openapi_parent_order_details`

近期要补：

- raw 同步批次表：记录每次同步的日期、范围、参数、成功/失败、行数。
- raw 覆盖率检查：例如当天活跃手机号里有多少拿到了消费画像。
- raw 重跑策略：支持按日期、门店、接口单独重跑。

### Clean 层

职责：把接口数据变成统一业务事件。

建议建设的 Clean 表：

- `clean_store`
- `clean_product`
- `clean_member`
- `clean_marketing_order`
- `clean_preorder`
- `clean_parent_order`
- `clean_product_order_item`
- `clean_stored_value_event`
- `clean_refund_event`

关键清洗规则：

- 营业日统一为 `08:00 ~ 次日 08:00`。
- 金额统一为“元”，保留原始金额单位字段。
- 门店统一到 `stores.id` 和 `fun360_shop_id`。
- 商品统一到商品档案，缺档案时用订单明细兜底。
- 商品大类只通过 `resolve_big_category()` 归一。
- 退款不直接丢弃，要拆出退款金额、退款数量、净额。
- 无效状态、取消订单、测试数据要可解释地过滤。

### Mart 层

职责：给业务直接使用的汇总表。

当前已有：

- `openapi_daily_store_metrics`
- `openapi_product_sales_items`

建议扩展：

- `mart_daily_store_revenue`
- `mart_daily_product_sales`
- `mart_daily_category_sales`
- `mart_daily_member_recharge`
- `mart_daily_groupbuy`
- `mart_monthly_store_revenue`
- `mart_monthly_product_sales`

## 业务主题域

### 1. 门店经营

问题：

- 每家店当天收入多少？
- 收入来自团购、储值、房费、商品的比例是多少？
- 和去年同期、上周同期相比怎么样？

核心事实：

- `fact_store_day`

粒度：

- 一行 = 一个门店 + 一个营业日。

核心指标：

- 总营收
- 净营收
- 房费收入
- 商品收入
- 储值收入
- 团购收入
- 客流/开台数
- 客单价

### 2. 商品销售

问题：

- 哪些商品卖得好？
- 哪些大类贡献最高？
- 商品销售是否受门店、时段、套餐影响？

核心事实：

- `fact_product_sale_item`

粒度：

- 一行 = 一个订单商品明细行，或物化后一行 = 门店 + 营业日 + 商品 + 分类。

核心指标：

- 销售数量
- 原始销售额
- 退款数量
- 退款金额
- 净销售额
- 销售门店数

### 3. 会员与储值

问题：

- 哪些门店储值强？
- 新老会员储值差异？
- 储值后是否产生消费？

核心事实：

- `fact_member_recharge`
- `fact_member_consume`

粒度：

- 一行 = 一笔会员储值事件。
- 一行 = 一笔会员消费事件。

核心指标：

- 储值金额
- 储值笔数
- 首充金额
- 复充金额
- 储值会员数
- 储值后消费金额

### 4. 团购与预订

问题：

- 团购订单实际贡献多少？
- 团购与到店开台如何关联？
- 哪些平台或券种表现好？

核心事实：

- `fact_marketing_order`
- `fact_preorder`

粒度：

- 一行 = 一笔团购/卡券订单。
- 一行 = 一笔预订。

核心指标：

- 团购订单数
- 团购实收
- 团购退款
- 到店核销数
- 预订到店率

## 数据质量体系

### 基础质量

- 主键不为空。
- 业务唯一键不重复。
- 外键能关联到门店、商品、会员。
- 金额字段单位统一。
- 日期落在目标营业窗口。

### 业务质量

- 门店日汇总金额不应异常为负。
- 商品数量不应为负。
- 商品净额为负允许存在，但必须标记为退款/冲减。
- 每日 mart 门店数不能突然大幅下降。
- 会员画像覆盖率低于阈值时报警。
- 开台单详情覆盖率低于阈值时报警。

### 对账质量

- mart 与旧日报基准按门店对账。
- mart 与旧日报基准按商品大类对账。
- 差异按金额绝对值和比例排序。
- 差异要能追溯到 raw 记录。

## 开发阶段

### 阶段 1：管道成型

状态：已开始。

目标：

- `./run.sh pipeline 日期 --skip-raw` 可稳定跑通。
- mart 表可重复物化。
- 质量检查可输出明确异常。
- benchmark 对账可一键执行。

已完成：

- `scripts/run_openapi_pipeline.py`
- `scripts/check_openapi_pipeline.py`
- `scripts/materialize_openapi_daily_metrics.py`
- `docs/data_pipeline.md`

### 阶段 2：Clean 层落库

目标：

- 不再只在 Python 内存中清洗，而是落出 clean 表。
- 每个 clean 表有明确主键、粒度、来源、过滤规则。
- mart 只从 clean 表生成。

优先顺序：

1. `clean_product`
2. `clean_marketing_order`
3. `clean_preorder`
4. `clean_member_consume_order`
5. `clean_parent_order_detail`
6. `clean_product_order_item`

### 阶段 3：对账闭环

目标：

- 对账结果写入表，而不是只打印。
- 每天能看到差异排行榜。
- 每个差异能追溯到门店、订单、商品、接口来源。

建议表：

- `dq_pipeline_runs`
- `dq_check_results`
- `dq_reconciliation_results`

### 阶段 4：指标服务化

目标：

- 报表、看板、API 都从 mart/semantic 指标层读取。
- 建立统一指标字典。
- 支持按门店、日期、商品大类、会员类型查询。

### 阶段 5：系统化

目标：

- 管道调度
- 运行日志
- 失败重试
- 数据质量看板
- 指标字典页面
- 门店经营看板
- 商品分析看板
- 会员储值分析

## 近期最该做的任务

1. 把 `materialize_openapi_daily_metrics.py` 里的清洗逻辑拆成可落库的 Clean 层。
2. 新增 `dq_pipeline_runs`，记录每次 pipeline 运行。
3. 新增对账结果表，保存 benchmark 差异。
4. 针对 2026-05-19 的差异做专项排查。
5. 补退款字段：原始金额、退款金额、净金额。
6. 补覆盖率指标：会员画像覆盖率、开台详情覆盖率。
7. 建立第一版指标字典，并让所有报表引用同一套定义。
