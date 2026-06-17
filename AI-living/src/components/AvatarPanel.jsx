import React, { useState } from 'react'
import { Card, Button, Radio, Space, message, Form, Input, Select } from 'antd'
import axios from 'axios'

const AvatarPanel = () => {
  const [mode, setMode] = useState('camera')
  const [cameraActive, setCameraActive] = useState(false)
  const [aiDriver, setAiDriver] = useState('openai')

  const handleSetMode = async (e) => {
    const newMode = e.target.value
    setMode(newMode)
    try {
      await axios.post('/api/avatar/mode', { mode: newMode })
      message.success('驱动模式已切换')
    } catch (err) {
      message.error('切换失败')
    }
  }

  const toggleCamera = async () => {
    try {
      const endpoint = cameraActive ? '/api/avatar/camera/stop' : '/api/avatar/camera/start'
      await axios.post(endpoint)
      setCameraActive(!cameraActive)
      message.success(cameraActive ? '摄像头已关闭' : '摄像头已开启')
    } catch (err) {
      message.error('操作失败')
    }
  }

  return (
    <Card title="数字人驱动设置">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <h3>驱动模式</h3>
          <Radio.Group value={mode} onChange={handleSetMode}>
            <Radio.Button value="camera">摄像头驱动</Radio.Button>
            <Radio.Button value="cache">缓存视频驱动</Radio.Button>
            <Radio.Button value="original">原音原画驱动</Radio.Button>
            <Radio.Button value="dual_avatar">双数字人驱动</Radio.Button>
            <Radio.Button value="sadtalker">SadTalker唇形驱动</Radio.Button>
          </Radio.Group>
        </div>
        <div>
          <h3>AI驱动方式</h3>
          <Radio.Group value={aiDriver} onChange={(e) => setAiDriver(e.target.value)}>
            <Radio.Button value="openai">OpenAI (轻量级)</Radio.Button>
            <Radio.Button value="sadtalker">SadTalker (云端GPU)</Radio.Button>
          </Radio.Group>
        </div>
        <div>
          <h3>摄像头控制</h3>
          <Button type={cameraActive ? 'default' : 'primary'} onClick={toggleCamera}>
            {cameraActive ? '关闭摄像头' : '开启摄像头'}
          </Button>
        </div>
      </Space>
    </Card>
  )
}

export default AvatarPanel