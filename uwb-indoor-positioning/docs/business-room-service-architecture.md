# UWB、房态与服务流程架构草案

记录日期：2026-05-24

## 一、定位

UWB 接入自有系统的核心价值，不是“看员工在哪”，而是把现场服务流程变成可感知、可追溯、可提醒的业务事件。

它应该连接：

```text
房态 room_state
    ↓
开台会话 room_session
    ↓
服务任务 service_task
    ↓
员工位置 uwb_position_event
    ↓
服务流程 service_workflow_event
```

最终目标：

```text
让系统知道一个包厢正在发生什么、应该由谁服务、服务是否已经到达、是否超时、是否需要升级提醒。
```

## 二、为什么 UWB 必须和房态相连

如果 UWB 只做员工轨迹，会有三个问题：

1. 管理价值弱，容易变成“监控员工”。
2. 位置数据太多，无法解释业务意义。
3. 不能直接驱动收银端和管理后台动作。

如果 UWB 绑定房态，它就能回答：

- 使用中包厢是否有服务员响应？
- 服务铃响后多久有人到门口/进入包厢？
- 出品任务生成后是否有人送达？
- 结算中包厢是否有人到场处理？
- 关房后是否进入清洁流程？
- 清洁是否持续了合理时长？
- 锁房、坏房、试机房是否有人异常进入？
- 高峰期服务员是否集中在某些区域，导致其他区域无人覆盖？

所以 UWB 不是单独模块，而是 `room_session` 的现场感知层。

## 三、硬件对象

### 1. UWB Anchor

固定基站。

字段建议：

| 字段 | 说明 |
| --- | --- |
| `anchor_id` | 基站 ID |
| `store_id` | 门店 |
| `floor_id` | 楼层 |
| `zone_id` | 区域 |
| `x/y/z` | 店内坐标 |
| `status` | 在线、离线、异常 |
| `installed_at` | 安装时间 |

### 2. UWB Tag

移动标签，可以是员工工牌、手环、托盘标签、设备标签。

字段建议：

| 字段 | 说明 |
| --- | --- |
| `tag_id` | 标签 ID |
| `tag_type` | `staff/tray/device/temp` |
| `bound_staff_id` | 绑定员工 |
| `bound_device_id` | 绑定设备 |
| `status` | 在线、离线、低电、未绑定 |
| `battery_level` | 电量 |
| `last_seen_at` | 最后在线时间 |

### 3. Zone

UWB 位置必须先归一到业务区域，不能直接把坐标暴露给业务系统。

区域类型：

- 包厢
- 包厢门口
- 走廊
- 出品口
- 前台
- 仓库
- 清洁间
- 员工休息区
- 禁入区

字段建议：

| 字段 | 说明 |
| --- | --- |
| `zone_id` | 区域 ID |
| `store_id` | 门店 |
| `zone_type` | `room/doorway/corridor/kitchen/frontdesk/storage/cleaning/blocked` |
| `room_id` | 如果是包厢或门口，关联包厢 |
| `polygon` | 区域边界 |
| `confidence_rule` | 坐标归属规则 |

## 四、UWB 原始事件与业务事件

### Raw 位置事件

粒度：

```text
一行 = 一个标签在某一时刻的一次定位结果
```

建议表：

- `raw_uwb_position_events`

字段：

- `tag_id`
- `store_id`
- `occurred_at`
- `x/y/z`
- `accuracy`
- `anchor_count`
- `raw_payload`

Raw 层只保存，不直接参与管理判断。

### Clean 位置事件

粒度：

```text
一行 = 一个标签进入、停留、离开一个业务区域
```

建议表：

- `clean_uwb_zone_presence`

字段：

| 字段 | 说明 |
| --- | --- |
| `presence_id` | 区域停留事件 |
| `tag_id` | 标签 |
| `staff_id` | 员工 |
| `store_id` | 门店 |
| `zone_id` | 区域 |
| `room_id` | 包厢，可为空 |
| `entered_at` | 进入时间 |
| `left_at` | 离开时间 |
| `duration_seconds` | 停留时长 |
| `confidence` | 置信度 |
| `source` | UWB |

### 服务流程事件

UWB 进入业务区域后，要转换成服务流程事件。

建议表：

- `clean_service_workflow_event`

事件类型：

| 事件 | 触发 |
| --- | --- |
| `staff_arrived_room_door` | 员工进入包厢门口区域 |
| `staff_entered_room` | 员工进入包厢区域 |
| `staff_left_room` | 员工离开包厢区域 |
| `service_response_started` | 服务铃后首次到达 |
| `service_response_completed` | 服务任务完成 |
| `delivery_arrived` | 出品送达包厢 |
| `cleaning_started` | 关房后员工进入清洁 |
| `cleaning_finished` | 员工离开并转空闲 |
| `abnormal_entry` | 异常房态下进入 |
| `no_response_timeout` | 服务超时无人到达 |

## 五、服务任务模型

UWB 不直接定义任务，任务来自业务系统。

建议表：

- `service_task`

任务来源：

- 服务铃
- 打印异常
- 贩卖机通知
- 点单出品
- 结算协助
- 关房清洁
- 维护报修
- 店长手工派单

字段建议：

| 字段 | 说明 |
| --- | --- |
| `task_id` | 任务 ID |
| `store_id` | 门店 |
| `room_id` | 包厢 |
| `room_session_id` | 当前开台会话 |
| `task_type` | `service_call/delivery/cleaning/payment_help/maintenance/manual` |
| `source_id` | 服务铃 ID、订单 ID、打印任务 ID 等 |
| `priority` | 优先级 |
| `status` | `created/dispatched/responding/in_progress/completed/canceled/escalated` |
| `created_at` | 创建时间 |
| `assigned_staff_id` | 指派员工 |
| `accepted_at` | 接单时间 |
| `first_arrived_at` | 首次到达时间，由 UWB 推断 |
| `completed_at` | 完成时间 |
| `sla_seconds` | 要求响应时间 |

## 六、房态驱动的服务流程

### 1. 使用中包厢服务铃

流程：

```text
服务铃产生
  -> service_task.created
  -> 对讲机/收银端提醒
  -> UWB 检测员工进入包厢门口
  -> service_response_started
  -> 员工进入包厢或停留足够时间
  -> service_response_completed
```

关键指标：

- 服务响应时间：`first_arrived_at - created_at`
- 服务处理时长：`completed_at - first_arrived_at`
- 超时次数
- 未响应次数
- 重复呼叫次数

### 2. 点单出品送达

流程：

```text
订单商品需要出品
  -> delivery_task.created
  -> 出品口领取
  -> UWB 标签或员工从出品口离开
  -> 员工进入目标包厢门口/包厢
  -> delivery_arrived
```

第一期不一定要给托盘贴标签，可以先用“员工从出品口到包厢”的路径推断。

关键指标：

- 出品到达时长
- 高峰期出品堵点
- 包厢漏送/延迟提醒

### 3. 关房清洁

流程：

```text
room_session.closed
  -> cleaning_task.created
  -> 房态转 cleaning
  -> UWB 检测清洁员工进入包厢
  -> cleaning_started
  -> 员工离开包厢
  -> 可选人工确认
  -> 房态转 idle
```

关键指标：

- 关房到清洁开始时长
- 清洁耗时
- 清洁后回空闲时长
- 清洁超时
- 未清洁直接回空闲异常

### 4. 结算中包厢

流程：

```text
room_state = settling
  -> payment_help_task.created
  -> 收银员/服务员到达包厢
  -> 协助支付或确认
  -> room_state open_paid/closed
```

关键指标：

- 结算等待时长
- 结算协助响应时间
- 结算中长时间无人处理异常

### 5. 锁房、坏房、试机异常进入

流程：

```text
room_state in locked/maintenance/test
  + UWB 检测非授权员工进入
  -> abnormal_entry
  -> 记录或提醒
```

这类事件不一定要实时打扰门店，但应进入数据质量和安全审计。

## 七、UWB 与房态的判断规则

### 当前房态必须参与判断

同样是员工进入包厢，业务意义取决于房态：

| 房态 | 员工进入含义 |
| --- | --- |
| 空闲 | 巡检、布置、异常进入 |
| 预订 | 预订准备、迎客 |
| 使用中未结 | 服务、出品、销售、巡房 |
| 使用中已结 | 关房提醒、清场 |
| 结算中 | 结算协助 |
| 清洁 | 清洁执行 |
| 锁房/坏房 | 异常进入或维修 |
| 试机 | 测试行为 |

所以规则引擎输入必须包含：

- `room_state`
- `room_session_id`
- `service_task`
- `staff_role`
- `uwb_zone_presence`
- `time_window`

### 位置事件需要置信度

UWB 可能出现边界抖动，不能每秒进出都生成业务动作。

建议规则：

- 进入包厢门口超过 5 秒，才算到达门口。
- 进入包厢超过 10 秒，才算进入包厢。
- 位置在两个房间边界跳动时，按高置信度区域或持续时间归属。
- 同一员工同一房间 60 秒内重复进出合并为一次服务片段。

## 八、提醒和对讲机联动

现有接口里已经有：

- 服务铃列表
- 待完成服务铃列表
- 取消服务铃
- 对讲机文字转语音发送
- 按包厢角色发送对讲机语音

自有系统可以这样联动：

```text
service_task 超时
  -> 找到最近可服务员工
  -> 发送对讲机提醒
  -> 收银端/店长端标红
```

提醒策略：

| 场景 | 首次提醒 | 升级提醒 |
| --- | --- | --- |
| 服务铃无人到达 | 60 秒 | 120 秒通知店长 |
| 出品未送达 | 5 分钟 | 8 分钟通知出品口和区域负责人 |
| 关房未清洁 | 3 分钟 | 8 分钟通知店长 |
| 结算中无人处理 | 2 分钟 | 5 分钟通知收银/店长 |
| UWB 标签离线 | 5 分钟 | 15 分钟进入设备异常 |

## 九、数据层建议

第一版服务流程、房态、UWB、SLA 和隐私边界已预配置：

- `configs/service_workflow_config.json`
- `docs/service_workflow_config.md`

### Raw 层

- `raw_uwb_position_events`
- `raw_uwb_device_status`
- `raw_service_notifications`
- `raw_ptt_messages`

### Clean 层

- `clean_uwb_anchor`
- `clean_uwb_tag`
- `clean_uwb_zone`
- `clean_uwb_zone_presence`
- `clean_service_task`
- `clean_service_workflow_event`
- `clean_room_state_event`

### Mart 层

- `mart_daily_service_response`
- `mart_daily_staff_service`
- `mart_room_service_timeline`
- `mart_room_cleaning_efficiency`
- `mart_service_exception`
- `mart_uwb_device_health`

## 十、未来页面设计

### 收银端房态屏

每个包厢除了房态，还显示：

- 当前服务任务数
- 服务铃是否待响应
- 最近员工到达时间
- 清洁是否进行中
- 结算是否超时
- 异常提醒

### 店长现场屏

展示：

- 全店服务任务队列
- 超时任务
- 员工所在区域，不显示精细轨迹
- 哪些区域无人覆盖
- 哪些包厢高频呼叫

### 数据后台

展示：

- 服务响应排行
- 清洁效率
- 出品送达效率
- 员工服务覆盖
- 高峰期服务压力
- 异常进入
- UWB 设备健康

## 十一、隐私与管理边界

UWB 必须从一开始就设边界，否则容易变成员工抵触的监控系统。

建议原则：

1. 管理页面默认展示区域和流程，不展示秒级轨迹。
2. 只有异常排查时才能查看详细轨迹片段。
3. 轨迹保留周期短于业务指标，原始位置可定期归档或脱敏。
4. 员工看板用于服务调度，不用于单独惩罚。
5. 指标重点是流程是否顺畅，而不是盯人。

## 十二、分阶段落地

### 阶段 1：房态 + 服务铃

不接 UWB 也能先做：

- 同步服务铃
- 建 `service_task`
- 和 `room_session` 关联
- 做服务超时提醒

### 阶段 2：UWB 到达确认

接入员工标签：

- 员工进入包厢门口
- 员工进入包厢
- 服务铃自动确认到达
- 清洁自动确认开始

### 阶段 3：流程化服务

接入出品、清洁、结算：

- 出品送达
- 清洁耗时
- 结算协助
- 区域服务覆盖

### 阶段 4：智能调度

基于房态、任务、位置：

- 推荐最近员工
- 自动升级超时任务
- 高峰期服务压力预测
- 异常动线分析

## 十三、关键结论

1. UWB 必须绑定 `room_session` 和 `room_state`，不能孤立做定位。
2. UWB 原始坐标不应直接进管理页面，必须先归一成业务区域和流程事件。
3. 服务铃、出品、清洁、结算是第一批最适合 UWB 驱动的流程。
4. 对讲机接口可以作为提醒触达层。
5. 未来系统的竞争力不只是收银，而是“收银 + 房态 + 服务流程 + 数据管理”的闭环。
