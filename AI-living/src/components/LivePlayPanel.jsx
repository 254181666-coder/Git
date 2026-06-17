import React, { useState, useEffect } from 'react'
import { Card, Button, Upload, Space, message, Switch, Typography } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Title, Text } = Typography

const LivePlayPanel = () => {
  const [deduplicate, setDeduplicate] = useState(false)
  const [timestamp, setTimestamp] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      axios.get('/api/live/timestamp')
        .then(res => setTimestamp(res.data.timestamp))
        .catch(() => {})
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleVideoUpload = (file) => {
    message.success('视频已加载')
    return false
  }

  const toggleStream = async () => {
    try {
      if (isStreaming) {
        await axios.post('/api/live/stop')
        setIsStreaming(false)
        message.info('直播已停止')
      } else {
        await axios.post('/api/live/start', {
          rtmp_url: 'rtmp://your-stream-server/live',
          enable_anti_detect: true
        })
        setIsStreaming(true)
        message.success('直播已启动')
      }
    } catch (err) {
      message.error('操作失败')
    }
  }

  return (
    <Card title="直播玩法">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <h3>直播控制</h3>
          <Button type={isStreaming ? 'danger' : 'primary'} onClick={toggleStream}>
            {isStreaming ? '停止直播' : '启动直播'}
          </Button>
        </div>
        <div>
          <h3>录播转播</h3>
          <Upload beforeUpload={handleVideoUpload} accept="video/*" fileList={[]}>
            <Button icon={<UploadOutlined />}>加载录播视频</Button>
          </Upload>
        </div>
        <div>
          <h3>画面去重</h3>
          <Space>
            <Text>开启画面去重：</Text>
            <Switch checked={deduplicate} onChange={setDeduplicate} />
          </Space>
        </div>
        <div>
          <h3>实时报时</h3>
          <Title level={2} style={{ color: '#1890ff', margin: 0 }}>{timestamp || '--:--:--'}</Title>
          <Text type="secondary">当前时间</Text>
        </div>
      </Space>
    </Card>
  )
}

export default LivePlayPanel