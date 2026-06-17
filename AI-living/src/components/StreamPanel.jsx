import React, { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Space, Select, Switch, Typography, message, Divider, Collapse, Alert, Tag } from 'antd'
import { PlayCircleOutlined, StopOutlined, LinkOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Text, Title } = Typography
const { Panel } = Collapse
const { TextArea } = Input

const StreamPanel = () => {
  const [form] = Form.useForm()
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamStatus, setStreamStatus] = useState(null)
  const [platform, setPlatform] = useState('douyin')
  const [dryRun, setDryRun] = useState(true)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await axios.get('/api/live/status')
      setStreamStatus(res.data)
      setIsStreaming(res.data.is_streaming)
    } catch (err) {
      message.error('无法获取推流状态，请确认后端服务已启动')
    }
  }

  const handleStartStream = async (values) => {
    try {
      const payload = {
        ...values,
        dry_run: dryRun,
        rtmp_url: dryRun ? 'dry-run://local-demo' : values.rtmp_url
      }
      const res = await axios.post('/api/live/start', payload)
      setIsStreaming(true)
      fetchStatus()
      message.success(res.data?.message || '推流已启动')
    } catch (err) {
      message.error(err.response?.data?.message || '推流启动失败')
    }
  }

  const handleStopStream = async () => {
    try {
      await axios.post('/api/live/stop')
      setIsStreaming(false)
      fetchStatus()
      message.info('推流已停止')
    } catch (err) {
      message.error(err.response?.data?.message || '停止失败')
    }
  }

  const platformTips = {
    douyin: {
      name: '抖音',
      tip: '打开抖音APP → 我 → 创作者服务中心 → 开始直播 → 复制推流地址',
      format: 'rtmp://push-rtmp.douyin.com/live/xxx'
    },
    kuaishou: {
      name: '快手',
      tip: '打开快手直播伴侣 → 获取推流码 → 复制RTMP地址',
      format: 'rtmp://push-rtcp-hs.kuaishou.com/live/xxx'
    },
    video: {
      name: '视频号',
      tip: '打开视频号助手网页 → 创建直播 → 获取推流地址',
      format: 'rtmp://xxxx.vlive.qq.com/live/xxx'
    },
    bilibili: {
      name: 'B站',
      tip: '打开B站直播中心 → 我的直播间 → 复制推流地址',
      format: 'rtmp://live-push.bilivideo.com/live-bvc/xxx'
    },
    custom: {
      name: '自定义',
      tip: '输入任意RTMP推流地址',
      format: 'rtmp://your-server/live/xxx'
    }
  }

  return (
    <Card title="RTMP推流配置">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        
        {/* 直播状态 */}
        <Alert
          message={isStreaming ? (streamStatus?.dry_run ? '直播中 - 本地演示模式' : '直播中 - 正在推流') : '未开播'}
          description={streamStatus?.dry_run ? '当前不会连接真实RTMP或FFmpeg，适合无设备本地验收。' : undefined}
          type={isStreaming ? 'success' : 'warning'}
          showIcon
        />

        {/* 推流表单 */}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleStartStream}
          initialValues={{
            rtmp_url: '',
            width: 1080,
            height: 1920,
            fps: 30,
            bitrate: 4000,
            enable_audio: true,
            audio_bitrate: 128,
            audio_file: '',
            enable_anti_detect: true,
            dry_run: true
          }}
        >
          <Form.Item label="本地演示模式">
            <Switch checked={dryRun} onChange={setDryRun} disabled={isStreaming} />
            <Text type="secondary" style={{ marginLeft: 12 }}>
              开启后无需真实RTMP地址、FFmpeg或直播平台。
            </Text>
          </Form.Item>

          {/* 平台选择 */}
          <Form.Item label="直播平台">
            <Select value={platform} onChange={setPlatform} disabled={dryRun || isStreaming}>
              <Select.Option value="douyin">抖音</Select.Option>
              <Select.Option value="kuaishou">快手</Select.Option>
              <Select.Option value="video">视频号</Select.Option>
              <Select.Option value="bilibili">B站</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>

          {/* 各平台获取教程 */}
          <Collapse defaultActiveKey={[]} style={{ marginBottom: 16 }}>
            <Panel header={`📖 ${platformTips[platform].name}推流地址获取方法`} key="tutorial">
              <p>{platformTips[platform].tip}</p>
              <Text type="secondary">格式示例: {platformTips[platform].format}</Text>
            </Panel>
          </Collapse>

          {/* RTMP地址 */}
          <Form.Item
            name="rtmp_url"
            label="推流地址 (RTMP URL)"
            rules={[{ required: !dryRun, message: '请输入推流地址' }]}
          >
            <Input
              placeholder={dryRun ? '本地演示模式无需填写' : 'rtmp://...'}
              prefix={<LinkOutlined />}
              disabled={dryRun || isStreaming}
            />
          </Form.Item>

          {/* 推流参数 */}
          <Divider orientation="left">推流参数</Divider>
          
          <Form.Item name="width" label="分辨率宽度">
            <Select>
              <Select.Option value={720}>720</Select.Option>
              <Select.Option value={1080}>1080 (推荐)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="height" label="分辨率高度">
            <Select>
              <Select.Option value={1280}>1280 (横屏)</Select.Option>
              <Select.Option value={1920}>1920 (竖屏推荐)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="fps" label="帧率">
            <Select>
              <Select.Option value={24}>24 fps</Select.Option>
              <Select.Option value={30}>30 fps (推荐)</Select.Option>
              <Select.Option value={60}>60 fps</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="bitrate" label="码率 (kbps)">
            <Select>
              <Select.Option value={2000}>2000 kbps (低)</Select.Option>
              <Select.Option value={4000}>4000 kbps (推荐)</Select.Option>
              <Select.Option value={6000}>6000 kbps (高)</Select.Option>
            </Select>
          </Form.Item>

          <Divider orientation="left">音频</Divider>

          <Form.Item name="enable_audio" valuePropName="checked" label="推流音频轨">
            <Switch disabled={isStreaming} />
          </Form.Item>

          <Form.Item name="audio_bitrate" label="音频码率 (kbps)">
            <Select disabled={isStreaming}>
              <Select.Option value={96}>96 kbps</Select.Option>
              <Select.Option value={128}>128 kbps (推荐)</Select.Option>
              <Select.Option value={192}>192 kbps</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="audio_file" label="音频文件路径">
            <Input
              placeholder="留空时使用静音音轨，后续可填入TTS生成的音频文件"
              disabled={isStreaming}
            />
          </Form.Item>

          <Form.Item name="enable_anti_detect" valuePropName="checked" label="防检测优化">
            <Switch />
          </Form.Item>

          {/* 操作按钮 */}
          <Form.Item>
            <Space>
              <Button
                type="primary"
                danger={isStreaming}
                icon={isStreaming ? <StopOutlined /> : <PlayCircleOutlined />}
                onClick={isStreaming ? handleStopStream : () => form.submit()}
                size="large"
              >
                {isStreaming ? '停止推流' : '开始推流'}
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 状态信息 */}
        {streamStatus && (
          <Collapse>
            <Panel header="直播状态详情" key="status">
              <p>推流状态: {streamStatus.is_streaming ? '运行中' : '已停止'}</p>
              <p>运行模式: {streamStatus.dry_run ? <Tag color="blue">本地演示</Tag> : <Tag color="green">真实推流</Tag>}</p>
              <p>运行时长: {Math.round(streamStatus.runtime_seconds || 0)} 秒</p>
              <p>音频轨: {streamStatus.audio_enabled ? '已启用' : '未启用'}</p>
              <p>话术轮播: {streamStatus.is_scheduling ? '运行中' : '已停止'}</p>
              <p>AI连接: {streamStatus.ai_connected ? '已连接' : '未连接'}</p>
            </Panel>
          </Collapse>
        )}
      </Space>
    </Card>
  )
}

export default StreamPanel
