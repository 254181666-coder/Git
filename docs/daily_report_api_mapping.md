# 每日报告数据接口匹配记录

## 目标输出

每天早上生成昨天营业日的 4 个标准文件：

- `data/output/{日期}储值率分析图.png`
- `data/output/收入分析综合图_{日期}.png`
- `data/output_pdf/商品销售分析报告_{日期}.pdf`
- `data/output_pdf/同比对比分析报告_{日期}.pdf`

其中营业日按 `08:00:00` 到次日 `08:00:00` 取数。

## 本地数据表

现有生成脚本依赖这些 SQLite 表：

- `stores`
- `store_daily`
- `stored_value`
- `product_sales_summary`
- `product_sales_detail`

## 已确认接口

### OpenAPI签名

- 文档地址：`https://docs.apipost.net/docs/detail/2f74b48cf066000?target_id=418584f`
- 域名：`https://open-api.fun360.cn`
- 签名：`sign = md5("nonce={nonce}&secret={secret}&timestamp={timestamp}")`
- Query：`appid`、`nonce`、`timestamp`、`sign`
- Header：`APP-PLATFORM`、`APPID` 等目录参数
- 已验证：`TOKEN`、`Authorization` 不需要传即可调用 `/open/...` 接口。

### 门店清单

- 接口：`POST /open/shop/list`
- 用途：获取门店和 `shop_id`
- 已验证：使用 `appid/secret` 签名可成功返回 15 家门店。
- 后续用途：同步到本地 `stores.fun360_shop_id`

### 商品基础资料

- 接口：`POST /open/product/paging`
- 接口：`POST /open/product/category_list`
- 已验证：可返回门店商品资料、分类、售价等。
- 限制：这是商品档案，不是销售汇总，不能直接生成 `product_sales_summary` 的销量和销售额。

### 卡券/团购订单

- 接口：`POST /open/marketing/orders`
- 已验证：可返回 `shop_id`、`biz_day`、`paid_amount`、`refund_amount`、`card_name` 等字段。
- 可映射：可用于补充 `store_daily.online_groupbuy` 的一部分口径。

### 商品销售

- 接口：`POST /api/order/product/get_category_list`
- 接口：`POST /api/order/product/get_list`
- 参数核心字段：
  - `shop_id`
  - `brand_id`
  - `start_time`
  - `end_time`
  - `product_name`
  - `category_id`
  - `area_id`
- 已确认：单门店、单营业日可以返回商品分类汇总和商品明细。
- 可映射：
  - `product_sales_summary.product_name` <- `product_name`
  - `product_sales_summary.category` <- `category_name`
  - `product_sales_summary.unit` <- `product_unit`
  - `product_sales_summary.quantity` <- `sale_total_num`
  - `product_sales_summary.sales_amount` <- `sale_total_amount`
  - `product_sales_summary.raw_json` <- 原始行

### 会员储值明细

- 接口：`POST /api/report/member/get_list`
- 参数核心字段：
  - `brand_id`
  - `start_time`
  - `end_time`
  - `balance_type: recharge`
  - `page`
  - `page_size`
- 已确认：可以返回充值记录、充值时间、充值金额、支付信息。
- 待确认：该接口返回行暂未直接带门店字段，需要继续匹配按门店归属的来源，或使用内嵌报表规则补齐。

## 待匹配接口

### OpenAPI验证未通过的日报候选

- `POST /open/order/drink_list`：要求 `member_id`，不能按门店营业日全量拉酒水订单。
- `POST /open/order/room_list`：要求 `member_id`，不能按门店营业日全量拉订房/开房订单。
- `POST /open/order/product/get_list`：返回 404。
- `POST /open/order/product/get_category_list`：返回 404。
- `POST /open/report/filter/brand_shop`：返回 404。
- `POST /open/report/member/get_list`：返回 404。

### 营收日报

本地 `store_daily` 至少需要：

- `total_revenue`
- `stored_card_sales`
- `online_groupbuy`
- `customers_before_18`
- `customers_18_to_24`
- `customers_after_00`
- `peak_room_count`

后台前端中已发现相关报表规则：

- 收入：`dataAnalysis:operate:daily_report:data:income`
- 渠道/客流：`dataAnalysis:operate:daily_report:data:channel_num`
- 房态/房型：`dataAnalysis:operate:daily_report:data:room_plan`

这些规则通过 `/api/report/urls` 获取内嵌报表地址，仍需确认最稳定的数据拉取方式。

### 储值按门店

本地 `stored_value` 需要：

- `store_id`
- `data_date`
- `stored_amount`
- `recharge_time`
- `payment_method`
- 原始明细

目前会员储值接口可取充值行，但门店归属还需补齐。

## 自动化前置条件

要做到长期无人值守，需要 Fun360/open-api 的正式签名凭证：

- 已确认：接口实际调用只需要 `appid/secret` 生成签名。
- `TOKEN` 和 `Authorization` 属于全局公共参数文档中的历史/继承项，当前 open-api 调用不强制传入。

后台网页登录有验证码，不能依赖每天人工登录。

## 2026-05-20 验证进展

### 已跑通的明细链路

- 门店：`/open/shop/list`
- 商品档案：`/open/product/paging`
- 团购/卡券订单：`/open/marketing/orders`
- 预订单：`/open/order/preorders`
- 活跃手机号消费画像：`/open/private_marketing/user/detail`
- 开台单详情：`/open/parent_order/detail`

### 2026-05-17 样本结果

- 全部门店团购/卡券订单：31 行，净额 2546.00 元。
- 全部门店预订单：333 行。
- 当天活跃手机号：170 个。
- 成功同步手机消费画像：140 个。
- 同步开台单详情：199 个。
- 全部门店商品档案：5213 行。
- 物化 OpenAPI 对账指标：
  - `openapi_daily_store_metrics`：13 家门店。
  - `openapi_product_sales_items`：558 个商品/项目行。
- 已加入商品大类规则：
  - 酒水：啤酒、饮料
  - 下酒菜：冷荤、鸭货、小海鲜、简餐、烤炸小食
  - 干果：优选坚果、优选蜜饯、优选零食、精选拼盘、雪糕
  - 氛围：礼炮、礼品、第三方、道具、果盘
  - 备品：备品、纸抽、开机套、其他
  - 日场：日场零食
  - 其他类：无法按小类或商品名识别的兜底项
- 2026-05-17 商品大类汇总：
  - 酒水：142 行，31194.15 元
  - 干果：174 行，8553.39 元
  - 氛围：49 行，7914.60 元
  - 下酒菜：87 行，4666.37 元
  - 备品：72 行，4632.50 元
  - 其他类：33 行，600.39 元
  - 日场：1 行，8.40 元

### 当前判断

可以实现“OpenAPI 明细 -> raw 表 -> 清洗汇总 -> 报告图表”的自动化主链路。

但正式替换日报前还有两类口径需要继续对账：

1. 非会员/无效手机号订单覆盖率  
   预订单中存在测试手机号、无效手机号，无法通过消费画像补明细；需要依赖 `/open/order/preorders` 和 `/open/parent_order/detail` 补足。

2. 商品分类口径  
   商品大类规则已写入 `openapi_product_sales_items.big_category`；仍需要业务确认“其他类”中的少量无法识别项是否补充关键词，之后即可写入正式 `product_sales_summary` 并接入图表。

## 2026-05-19 业务基准对账

用户提供了现有系统生成的昨日数据：

- 收入/储值率图片：`2026-05-19`
- 商品销售分析 PDF：`商品销售分析报告_2026-05-19.pdf`

已落地为本地基准文件：

- `data/benchmarks/2026-05-19_income_benchmark.csv`
- `data/benchmarks/2026-05-19_product_category_benchmark.csv`
- `data/benchmarks/2026-05-19_product_store_benchmark.csv`

对账脚本：

- `scripts/compare_openapi_to_benchmark.py 2026-05-19`

### 商品销售对账结论

PDF 基准：

- 商品数：485
- 商品行/分类统计商品数合计：515
- 销售数量：22166
- 销售金额：22431.97 元

OpenAPI 订单详情物化：

- 商品行：365
- 销售数量：2395
- 销售金额：35081.10 元

差异说明：

- OpenAPI `/open/parent_order/detail` 当前取到的是开台单/点单里的订单项金额和数量。
- 现有商品销售报告使用的是“商品销售汇总（系统销售类别）”口径，明显包含套餐拆包、商品销售类别、数量换算或分摊后的结果。
- 因此，单靠当前订单详情 item 不能直接替代 `product_sales_summary` 的系统商品销售汇总口径。

### 收入口径对账结论

`/open/private_marketing/user/detail` 可获得部分储值、开台、点单信息，但与业务收入图表差异较大：

- 储值：部分门店明显高于或低于基准，例如上东 OpenAPI 7814 元 vs 基准 2076 元。
- 团购：部分门店未覆盖或金额口径不同，例如通辽 OpenAPI 0 元 vs 基准 610 元。
- 商品/其他收入：OpenAPI 明细金额不能直接作为收入结构图中的“其他收入”。

当前判断：

- OpenAPI 已能拉到订单链路明细，但仍缺少与后台报表一致的“日报汇总口径接口”或“商品销售汇总口径接口”。
- 若业务方确认 API 文档已经全部给出，需要继续在文档中寻找类似“商品销售汇总/经营日报/营业日报/收入结构/系统销售类别”的 open 接口，而不是继续扩大手机号扫描。
