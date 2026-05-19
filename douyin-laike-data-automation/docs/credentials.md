# 凭证保存说明

当前试点应用信息：

- APPID / ClientKey: `aw7elzin3yewy6sj`
- AppSecret: 不写入仓库文件，按密码保存

## 推荐保存方式

在本机创建 `.env` 文件，内容参考 `.env.example`：

```env
DOUYIN_APP_ID=aw7elzin3yewy6sj
DOUYIN_APP_SECRET=你的真实AppSecret
DOUYIN_OPENAPI_BASE_URL=https://open.douyin.com
```

`.env` 已加入 `.gitignore`，不会被正常提交。

## 安全注意

- 不要把 AppSecret 发到微信群、飞书群、GitHub、共享文档或截图里。
- 如果怀疑 AppSecret 已经泄露，在抖音开放平台重新生成。
- 后续程序只从环境变量或本机钥匙串读取 AppSecret，不硬编码到代码里。
