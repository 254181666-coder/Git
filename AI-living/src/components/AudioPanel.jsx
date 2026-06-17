import React, { useState } from 'react'
import { Card, Button, Radio, Upload, Space, message, List, Form, Input } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import axios from 'axios'

const AudioPanel = () => {
  const [mode, setMode] = useState('random')
  const [audioClips, setAudioClips] = useState([])

  const handleSetMode = async (e) => {
    const newMode = e.target.value
    setMode(newMode)
    try {
      await axios.post('/api/audio/mode', { mode: newMode })
      message.success('播放模式已切换')
    } catch (err) {
      message.error('切换失败')
    }
  }

  const handleAudioUpload = (file) => {
    setAudioClips([...audioClips, file.name])
    message.success('音频已添加')
    return false
  }

  const handleSplitAudio = () => {
    message.info('音频剪辑功能开发中...')
  }

  return (
    <Card title="音频驱动设置">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <h3>播放模式</h3>
          <Radio.Group value={mode} onChange={handleSetMode}>
            <Radio.Button value="random">随机播放</Radio.Button>
            <Radio.Button value="sequential">顺序播放</Radio.Button>
          </Radio.Group>
        </div>
        <div>
          <h3>音频素材</h3>
          <Upload beforeUpload={handleAudioUpload} fileList={[]}>
            <Button icon={<UploadOutlined />}>上传音频</Button>
          </Upload>
          <List
            dataSource={audioClips}
            renderItem={item => <List.Item>{item}</List.Item>}
            style={{ marginTop: 16 }}
          />
        </div>
        <div>
          <h3>音频剪辑</h3>
          <Button type="primary" onClick={handleSplitAudio}>
            剪辑碎片化音频素材
          </Button>
        </div>
      </Space>
    </Card>
  )
}

export default AudioPanel