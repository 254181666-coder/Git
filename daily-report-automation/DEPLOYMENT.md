# 服务器电脑部署清单

目标：把当前项目复制到一台不关机的 macOS 电脑上，由 launchd 每天定时发送企业微信。

## 1. 复制项目

把整个 `daily-report-automation` 文件夹复制到服务器电脑，例如：

```text
/Users/服务器用户名/Documents/daily-report-automation
```

不要只复制 `scripts/`，配置、日志目录、launchd 模板也要一起带过去。

## 2. 修改配置

编辑 `config/daily_auto_send.json`：

```json
{
  "send_time": "09:30",
  "report_path": "/绝对路径/每日报告.xlsx",
  "wechat_recipient": "企业微信群或联系人名称",
  "message_template": "今日报告：$report_name",
  "send_file": true,
  "wechat_app_name": "企业微信",
  "wechat_process_name": "企业微信",
  "ui_delay_seconds": 0.7,
  "log_dir": "logs",
  "log_level": "INFO"
}
```

`report_path` 建议用绝对路径。明天还没接 Fun360 自动下载前，先指向一个已经存在的测试报告文件。

## 3. 开权限

在服务器电脑上打开：

```text
System Settings -> Privacy & Security -> Accessibility
```

允许 Terminal 或 iTerm 控制电脑。企业微信需要保持已登录状态。

## 4. 手动测试

进入项目目录：

```bash
cd /Users/服务器用户名/Documents/daily-report-automation
```

先只测文本发送：

```bash
python3 scripts/daily_auto_send.py --config config/daily_auto_send.json --ignore-time --no-file
```

再测附件发送：

```bash
python3 scripts/daily_auto_send.py --config config/daily_auto_send.json --ignore-time
```

如果提示找不到报告文件，先修正 `report_path`。

## 5. 安装定时任务

手动测试通过后运行：

```bash
python3 scripts/install_launchd.py --config config/daily_auto_send.json
```

检查状态：

```bash
launchctl print gui/$(id -u)/com.daily-report-automation
```

看到 `StartCalendarInterval` 里是配置的时间，且脚本路径指向服务器电脑上的项目目录即可。

## 6. 看日志

```bash
tail -n 100 logs/daily_auto_send.log
tail -n 100 logs/send_to_wechat.log
tail -n 100 logs/launchd.err.log
```

## 7. 常见问题

- `Report file not found`：`report_path` 指向的文件不存在。
- `can't open file /Users/.../scripts/daily_auto_send.py`：没有进入项目目录，或 launchd plist 里路径旧了；重新运行 `scripts/install_launchd.py`。
- 企业微信没反应：确认企业微信已登录，并给 Terminal/Python 开了 Accessibility 权限。
- 找不到企业微信进程：把 `wechat_app_name` / `wechat_process_name` 尝试改成 `WeCom`。
