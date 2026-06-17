import React, { useState, useEffect, useRef } from 'react'
import { Card, Button, Radio, Space, message, Badge, Typography, Switch, Slider, InputNumber, Select } from 'antd'
import { VideoCameraOutlined, StopOutlined, UserOutlined, RobotOutlined, PictureOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Text } = Typography

const LiveModePanel = () => {
  const [mode, setMode] = useState('real_person')
  const [cameraRunning, setCameraRunning] = useState(false)
  const [cameraId, setCameraId] = useState(0)
  const [resolution, setResolution] = useState('1080x1920')
  const [fps, setFps] = useState(30)
  const [frameFit, setFrameFit] = useState('contain')
  const [frameRotation, setFrameRotation] = useState('none')
  const [useChromaKey, setUseChromaKey] = useState(false)
  const [showAiTips, setShowAiTips] = useState(true)
  const [pipPosition, setPipPosition] = useState('bottom_right')
  const [alternateInterval, setAlternateInterval] = useState(300)
  const [previewSrc, setPreviewSrc] = useState('')
  const [previewSource, setPreviewSource] = useState('demo')
  const [frameCount, setFrameCount] = useState(0)
  const previewTimerRef = useRef(null)

  useEffect(() => {
    fetchStatus()
    startPreviewPolling()
    return () => {
      if (previewTimerRef.current) clearInterval(previewTimerRef.current)
    }
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await axios.get('/api/live_mode/status')
      setCameraRunning(res.data.camera_running)
      setFrameCount(res.data.frame_count || 0)
      setUseChromaKey(Boolean(res.data.use_chroma_key))
      if (res.data.frame_fit) setFrameFit(res.data.frame_fit)
      if (res.data.frame_rotation) setFrameRotation(res.data.frame_rotation)
      if (typeof res.data.camera_id === 'number') setCameraId(res.data.camera_id)
    } catch (err) {
      message.error('无法获取摄像头状态，请确认后端服务已启动')
    }
  }

  const startPreviewPolling = () => {
    if (previewTimerRef.current) clearInterval(previewTimerRef.current)
    const fetchFrame = async () => {
      try {
        const res = await axios.get('/api/compositor/preview')
        if (res.data.frame) {
          setPreviewSrc(`data:image/jpeg;base64,${res.data.frame}`)
          setPreviewSource(res.data.source || 'demo')
        }
        fetchStatus()
      } catch (err) {
        message.error('无法获取预览画面')
      }
    }
    fetchFrame()
    previewTimerRef.current = setInterval(fetchFrame, 150)
  }

  const startCamera = async () => {
    try {
      const [width, height] = resolution.split('x').map(Number)
      
      const res = await axios.post('/api/live_mode/start', {
        mode,
        camera_id: cameraId,
        width,
        height,
        fps,
        frame_fit: frameFit,
        frame_rotation: frameRotation,
        use_chroma_key: useChromaKey,
        show_ai_tips: showAiTips,
        pip_position: pipPosition,
        alternate_interval: alternateInterval
      })
      
      if (res.data.status === 'ok') {
        setCameraRunning(true)
        message.success('摄像头已启动')
      } else {
        message.error(res.data.message || '摄像头启动失败')
      }
    } catch (err) {
      message.error(err.response?.data?.message || '摄像头启动失败')
    }
  }

  const stopCamera = async () => {
    await axios.post('/api/live_mode/stop')
    setCameraRunning(false)
    startPreviewPolling()
    message.info('摄像头已关闭')
  }

  const handleModeChange = (e) => {
    setMode(e.target.value)
    if (cameraRunning) {
      stopCamera().then(() => startCamera())
    }
  }

  const modeOptions = [
    { value: 'real_person', label: '真人出镜', icon: <UserOutlined /> },
    { value: 'ai', label: 'AI数字人', icon: <RobotOutlined /> },
    { value: 'pip', label: '画中画', icon: <PictureOutlined /> },
    { value: 'alternate', label: '交替出镜', icon: <VideoCameraOutlined /> }
  ]

  return (
    <Card title={
      <Space>
        <Badge dot={cameraRunning} color="green">
          <VideoCameraOutlined /> 真人直播模式
        </Badge>
      </Space>
    }>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 模式选择 */}
        <div>
          <Text strong>直播模式</Text>
          <Radio.Group 
            value={mode} 
            onChange={handleModeChange}
            style={{ marginTop: 8, display: 'flex', gap: 8 }}
          >
            {modeOptions.map(opt => (
              <Radio.Button key={opt.value} value={opt.value}>
                {opt.icon} {opt.label}
              </Radio.Button>
            ))}
          </Radio.Group>
        </div>

        {/* 摄像头预览 */}
        <div>
          <Text strong>摄像头预览</Text>
          <div style={{
            marginTop: 8,
            width: '100%',
            height: 360,
            background: '#000',
            borderRadius: 8,
            overflow: 'hidden',
            position: 'relative'
          }}>
            {previewSrc && (
              <img src={previewSrc} alt="摄像头预览" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            )}
            {!cameraRunning && !previewSrc && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                color: '#fff',
                textAlign: 'center'
              }}>
                <UserOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>等待摄像头画面...</p>
              </div>
            )}
            {!cameraRunning && previewSrc && (
              <Badge
                count={previewSource === 'demo' ? '演示画面' : '摄像头画面'}
                style={{ position: 'absolute', top: 12, right: 12, backgroundColor: '#1677ff' }}
              />
            )}
            {showAiTips && cameraRunning && (
              <div style={{
                position: 'absolute',
                bottom: 16,
                left: 16,
                right: 16,
                background: 'rgba(0,0,0,0.7)',
                color: '#fff',
                padding: '8px 16px',
                borderRadius: 8,
                fontSize: 14
              }}>
                AI提示：欢迎进入直播间，今天给大家带来好物...
              </div>
            )}
            {cameraRunning && (
              <Badge
                count={`帧 ${frameCount}`}
                style={{ position: 'absolute', top: 12, right: 12, backgroundColor: '#52c41a' }}
              />
            )}
          </div>
        </div>

        {/* 控制按钮 */}
        <div>
          <Space>
            <Button
              type="primary"
              danger={cameraRunning}
              icon={cameraRunning ? <StopOutlined /> : <VideoCameraOutlined />}
              onClick={cameraRunning ? stopCamera : startCamera}
            >
              {cameraRunning ? '关闭摄像头' : '开启摄像头'}
            </Button>
          </Space>
        </div>

        {/* 设置选项 */}
        <div>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text>摄像头编号：</Text>
              <InputNumber min={0} max={10} value={cameraId} onChange={value => setCameraId(value || 0)} disabled={cameraRunning} />
            </div>

            <div>
              <Text>采集分辨率：</Text>
              <Select value={resolution} onChange={setResolution} disabled={cameraRunning} style={{ width: 160 }}>
                <Select.Option value="720x1280">720 x 1280</Select.Option>
                <Select.Option value="1080x1920">1080 x 1920</Select.Option>
                <Select.Option value="1280x720">1280 x 720</Select.Option>
                <Select.Option value="1920x1080">1920 x 1080</Select.Option>
              </Select>
            </div>

            <div>
              <Text>画面适配：</Text>
              <Select value={frameFit} onChange={setFrameFit} disabled={cameraRunning} style={{ width: 160 }}>
                <Select.Option value="contain">保持比例完整</Select.Option>
                <Select.Option value="cover">填满画面裁切</Select.Option>
                <Select.Option value="stretch">拉伸填满</Select.Option>
              </Select>
            </div>

            <div>
              <Text>画面方向：</Text>
              <Select value={frameRotation} onChange={setFrameRotation} disabled={cameraRunning} style={{ width: 160 }}>
                <Select.Option value="none">不旋转</Select.Option>
                <Select.Option value="rotate90">顺时针90度</Select.Option>
                <Select.Option value="rotate180">旋转180度</Select.Option>
                <Select.Option value="rotate270">逆时针90度</Select.Option>
              </Select>
            </div>

            <div>
              <Text>采集帧率：</Text>
              <Select value={fps} onChange={setFps} disabled={cameraRunning} style={{ width: 120 }}>
                <Select.Option value={24}>24 fps</Select.Option>
                <Select.Option value={25}>25 fps</Select.Option>
                <Select.Option value={30}>30 fps</Select.Option>
              </Select>
            </div>

            <div>
              <Text>启用绿幕抠图：</Text>
              <Switch checked={useChromaKey} onChange={setUseChromaKey} disabled={cameraRunning} />
            </div>

            <div>
              <Text>显示AI提示：</Text>
              <Switch checked={showAiTips} onChange={setShowAiTips} />
            </div>
            
            {mode === 'pip' && (
              <div>
                <Text>画中画位置：</Text>
                <Radio.Group value={pipPosition} onChange={e => setPipPosition(e.target.value)}>
                  <Radio.Button value="top_left">左上</Radio.Button>
                  <Radio.Button value="top_right">右上</Radio.Button>
                  <Radio.Button value="bottom_left">左下</Radio.Button>
                  <Radio.Button value="bottom_right">右下</Radio.Button>
                </Radio.Group>
              </div>
            )}
            
            {mode === 'alternate' && (
              <div>
                <Text>交替间隔：{alternateInterval / 60}分钟</Text>
                <Slider
                  min={60}
                  max={600}
                  step={60}
                  value={alternateInterval}
                  onChange={setAlternateInterval}
                  marks={{
                    60: '1分钟',
                    300: '5分钟',
                    600: '10分钟'
                  }}
                />
              </div>
            )}
          </Space>
        </div>
      </Space>
    </Card>
  )
}

export default LiveModePanel
