# 指标字典草案

这是第一版业务指标定义，后续 Mart 表和系统 API 都应以这里为准。

## 通用维度

| 维度 | 定义 |
| --- | --- |
| 营业日 | 当日 08:00:00 到次日 08:00:00 |
| 门店 | 统一使用 `stores.id`，外部来源使用 `fun360_shop_id` 关联 |
| 商品大类 | 统一使用 `src.config.resolve_big_category()` |
| 金额单位 | Mart 层统一为元 |

## 门店经营指标

| 指标 | 英文字段建议 | 定义 | 粒度 |
| --- | --- | --- | --- |
| 总营收 | `total_revenue` | 房费收入 + 商品收入 + 储值收入 + 团购收入 + 其他已确认收入 | 门店 + 营业日 |
| 净营收 | `net_revenue` | 扣除退款/冲减后的确认收入 | 门店 + 营业日 |
| 房费收入 | `room_amount` | 开台/包房相关净收入 | 门店 + 营业日 |
| 商品收入 | `product_amount` | 商品明细净销售额 | 门店 + 营业日 |
| 储值收入 | `stored_amount` | 会员储值实收金额 | 门店 + 营业日 |
| 团购收入 | `marketing_amount` | 团购/卡券订单实收减退款 | 门店 + 营业日 |
| 开台数 | `room_orders` | 符合有效状态的开台订单数 | 门店 + 营业日 |
| 商品订单数 | `product_orders` | 含商品销售的订单数 | 门店 + 营业日 |

## 商品指标

| 指标 | 英文字段建议 | 定义 | 粒度 |
| --- | --- | --- | --- |
| 销售数量 | `quantity` | 销售数量 - 退款数量 | 门店 + 营业日 + 商品 |
| 原始销售额 | `gross_sales_amount` | 未扣退款的商品销售额 | 门店 + 营业日 + 商品 |
| 退款金额 | `refund_amount` | 商品退款/冲减金额 | 门店 + 营业日 + 商品 |
| 净销售额 | `net_sales_amount` | 原始销售额 - 退款金额 | 门店 + 营业日 + 商品 |
| 销售门店数 | `store_count` | 发生该商品净销售的门店数量 | 营业日 + 商品 |
| 商品大类销售额 | `category_sales_amount` | 按商品大类聚合的净销售额 | 门店 + 营业日 + 大类 |

## 会员储值指标

| 指标 | 英文字段建议 | 定义 | 粒度 |
| --- | --- | --- | --- |
| 储值笔数 | `stored_orders` | 有效储值事件数量 | 门店 + 营业日 |
| 储值金额 | `stored_amount` | 有效储值实收金额 | 门店 + 营业日 |
| 储值会员数 | `stored_member_count` | 发生储值的去重会员数 | 门店 + 营业日 |
| 首充金额 | `first_recharge_amount` | 首次储值会员贡献金额 | 门店 + 营业日 |
| 复充金额 | `repeat_recharge_amount` | 非首次储值会员贡献金额 | 门店 + 营业日 |

## 团购/预订指标

| 指标 | 英文字段建议 | 定义 | 粒度 |
| --- | --- | --- | --- |
| 团购订单数 | `marketing_orders` | 有效团购/卡券订单数量 | 门店 + 营业日 |
| 团购实收 | `marketing_paid_amount` | 团购/卡券支付金额 | 门店 + 营业日 |
| 团购退款 | `marketing_refund_amount` | 团购/卡券退款金额 | 门店 + 营业日 |
| 团购净额 | `marketing_net_amount` | 团购实收 - 团购退款 | 门店 + 营业日 |
| 预订数 | `preorder_count` | 目标营业窗口内预订数量 | 门店 + 营业日 |
| 预订到店数 | `preorder_arrived_count` | 已关联开台/消费的预订数量 | 门店 + 营业日 |
| 预订到店率 | `preorder_arrival_rate` | 预订到店数 / 预订数 | 门店 + 营业日 |

## 数据质量指标

| 指标 | 英文字段建议 | 定义 |
| --- | --- | --- |
| 会员画像覆盖率 | `member_consume_coverage_rate` | 已同步消费画像的活跃手机号数 / 当天活跃手机号数 |
| 开台详情覆盖率 | `parent_detail_coverage_rate` | 已同步开台详情数 / 当天相关开台单数 |
| 商品归类率 | `product_category_coverage_rate` | 已归类商品明细数 / 商品明细总数 |
| 门店映射完整率 | `store_mapping_coverage_rate` | 可关联到 `stores` 的来源记录数 / 来源记录总数 |
| 对账差异率 | `reconciliation_diff_rate` | mart 指标与基准指标差异 / 基准指标 |
