# 本地授权与签名方案

## 当前实现

- 授权模式：离线授权码。
- 授权校验：安装包内置公钥，客户输入的授权码必须通过 RSA-SHA256 签名校验。
- 授权内容：客户名称、套餐、签发时间、到期时间、可选设备码。
- 到期限制：到期后可登录查看历史数据，但不能新增任务、导入来源、运行发现、转线索、导出或下载备份。
- 私钥位置：`keys/license-private.pem`，只保留在服务方本机，已加入 `.gitignore`，不会打进客户安装包。

生成授权码：

```bash
npm run license:create -- --customer 客户名称 --plan 月度版 --expires 2026-06-30
```

绑定设备码：

```bash
npm run license:create -- --customer 客户名称 --plan 月度版 --expires 2026-06-30 --device 设备码
```

## 长期授权规划

### 第一阶段：本地授权

- 客户拿到安装包后本机激活。
- 服务方按月生成新授权码。
- 可选绑定设备码，减少授权码外传复用。
- 适合早期成交、私域交付、线下安装。

### 第二阶段：半联网授权

- 软件仍本地运行，定期联网校验授权状态。
- 离线宽限 7-15 天，避免客户网络不稳定导致无法使用。
- 服务方后台可管理客户、设备、到期时间、套餐和停用状态。
- 续费后软件自动延长，不必手动粘贴新授权码。

### 第三阶段：商业授权后台

- 增加客户管理后台、订单记录、授权码发放、设备解绑、续费提醒。
- 增加版本更新通道，按套餐控制高级功能。
- 增加授权审计：激活时间、机器码、版本、最近校验时间。
- 数据仍保存在客户本地，授权服务器只保存授权状态，不保存客户线索数据。

## Windows 签名方案

当前安装包可以安装，但未签名时 Windows 可能显示“未知发布者”。生产交付建议分两步：

### 快速商用

- 购买 OV 代码签名证书，或使用 Microsoft Azure Artifact Signing。
- 在 Windows 打包机或 CI 上签名 `release/获客工具包-版本-安装包.exe`。
- 使用 SHA-256 和时间戳，保证证书过期后历史安装包仍可验证。

### 正式品牌交付

- 使用 Azure Artifact Signing 或 EV/OV 代码签名证书。
- 在发布流水线中自动签名、校验签名、生成校验哈希。
- 每个客户交付包保留版本号、签名状态、授权批次和发布记录。
- 发布者名称建议统一为「灵数工坊」，与安装包作者信息、软件界面和代码签名主体保持一致。

参考资料：

- Microsoft Windows 代码签名选项：<https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options>
- Microsoft SignTool：<https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool>
- Azure Artifact Signing：<https://azure.microsoft.com/en-gb/products/trusted-signing/>
- electron-builder Windows 签名：<https://www.electron.build/code-signing-win.html>
