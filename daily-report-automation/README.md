# Daily Report Automation

> 已合并到 `/Users/ann/Desktop/AI/Project/每日报告`。后续优先维护主项目里的
> `scripts/wechat_sender.py`、`scripts/daily_report.py` 和 `scripts/install_launchd.py`。

第一阶段目标：按配置时间，把指定报告文件发送到微信会话，并把执行日志落到 `logs/`。

## 文件结构

- `scripts/send_to_wechat.py`：通过 macOS AppleScript/System Events 控制微信发送消息和报告文件。
- `scripts/daily_auto_send.py`：launchd 调用入口，读取配置并触发发送。
- `config/daily_auto_send.json`：本机实际配置。
- `config/daily_auto_send.example.json`：配置示例。
- `logs/`：脚本和 launchd 日志目录。
- `launchd/com.daily-report-automation.plist.template`：macOS launchd 定时任务模板。

## 配置

编辑 `config/daily_auto_send.json`：

```json
{
  "send_time": "09:30",
  "report_path": "reports/daily-report.xlsx",
  "wechat_recipient": "文件传输助手",
  "message_template": "今日报告：$report_name",
  "send_file": true,
  "wechat_app_name": "WeChat",
  "wechat_process_name": "WeChat",
  "ui_delay_seconds": 0.7,
  "log_dir": "logs",
  "log_level": "INFO"
}
```

`report_path` 可以是绝对路径，也可以是相对本项目根目录的路径。`message_template` 支持 `$report_name` 和 `$report_path`。

如果要发送到企业微信，把 `wechat_app_name` / `wechat_process_name` 改成 `企业微信`。如果本机应用或进程名显示为 `微信`、`WeChat` 或 `WeCom`，把这两个字段改成对应名称。

## 手动测试

先确保微信已登录，并在系统设置里允许运行脚本的终端或 Python 控制电脑：

`System Settings -> Privacy & Security -> Accessibility`

然后运行：

```bash
python3 scripts/daily_auto_send.py --config config/daily_auto_send.json --ignore-time
```

如果只想测试文本，不发送附件：

```bash
python3 scripts/send_to_wechat.py --config config/daily_auto_send.json --no-file
```

## 安装 launchd 定时任务

推荐使用安装脚本，它会按当前项目路径和 `send_time` 生成 LaunchAgent：

```bash
python3 scripts/install_launchd.py --config config/daily_auto_send.json
```

检查状态：

```bash
launchctl print gui/$(id -u)/com.daily-report-automation
```

也可以手动确认 `launchd/com.daily-report-automation.plist.template` 里的路径和时间后，复制到用户 LaunchAgents：

```bash
cp launchd/com.daily-report-automation.plist.template ~/Library/LaunchAgents/com.daily-report-automation.plist
launchctl unload ~/Library/LaunchAgents/com.daily-report-automation.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.daily-report-automation.plist
```

查看任务：

```bash
launchctl list | grep daily-report-automation
```

卸载任务：

```bash
launchctl unload ~/Library/LaunchAgents/com.daily-report-automation.plist
```

## 下一阶段

Fun360 自动下载跑通后，把下载完成的报告路径写入或传给 `report_path`，再复用当前发送入口。

服务器电脑部署步骤见 `DEPLOYMENT.md`。
