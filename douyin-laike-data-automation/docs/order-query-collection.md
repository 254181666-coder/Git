# 订单查询数据采集

本项目的数据采集主链路先使用抖音生活服务 `订单查询` OpenAPI，不依赖三方码 SPI。

## 已验证订单

开放平台排查工具已能查询到两笔测试订单：

| 订单 ID | 状态 | 商品 ID | 支付金额 | 支付时间 |
| --- | --- | --- | --- | --- |
| `1094809189459863475` | 履约中 | `1835498536345603` | 25.80 元 | 2026-05-18 10:04:16 |
| `1094913539424664223` | 履约中 | `1855363134789644` | 9.99 元 | 2026-05-18 10:17:23 |

## 需要的权限

- 能力：`life.capacity.order.query`
- 接口：`GET https://open.douyin.com/goodlife/v1/trade/order/query/`
- Token：通过 `POST https://open.douyin.com/oauth/client_token/` 获取 `client_token`

## 本地配置

在 `.env` 中保存：

```env
DOUYIN_APP_ID=aw7elzin3yewy6sj
DOUYIN_APP_SECRET=你的真实AppSecret
DOUYIN_ACCOUNT_ID=7586893465921964032
DOUYIN_OPENAPI_BASE_URL=https://open.douyin.com
```

`.env` 不提交到仓库。

## 查询单笔订单

```bash
npm run order:query -- --order-id 1094809189459863475
```

## 按更新时间增量采集

```bash
npm run order:query -- --update-start "2026-05-18 00:00:00" --update-end "2026-05-18 23:59:59" --page-size 100
```

日常增量建议使用 `update_order_start_time` 和 `update_order_end_time`，因为退款、核销、订单状态变化会发生在创单之后。

## 注意事项

- 如果返回 `2100007 IP不在白名单，请开通权限`，说明代码和 token 请求已经打到抖音，但当前运行脚本的出口 IP 没有加入开放平台白名单。采集脚本建议部署在固定公网 IP 的服务器上，例如 `47.94.244.186`，并在应用的开发配置/安全配置中加入该 IP。
- `page_size` 最大 100。
- 普通页码翻页有 `page_num * page_size <= 10000` 限制，数据量大时改用 `cursor`。
- 脚本会把 `client_token` 缓存在 `.cache/douyin-client-token.json`，避免频繁刷新导致旧 token 失效。
- 如果接口返回应用未获商家授权，需要先在开放平台完成对应商家的授权绑定。
