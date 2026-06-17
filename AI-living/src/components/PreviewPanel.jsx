import React, { useState, useEffect, useRef } from 'react'
import { Card, Button, Space, Radio, Upload, Typography, message, Tag, Divider, Alert } from 'antd'
import { VideoCameraOutlined, PictureOutlined, BgColorsOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Text } = Typography
const { Dragger } = Upload

const PreviewPanel = () => {
  const [previewSrc, setPreviewSrc] = useState('')
  const [previewMeta, setPreviewMeta] = useState({ source: 'demo', camera_running: false })
  const [chromaColor, setChromaColor] = useState('green')
  const [textOverlay, setTextOverlay] = useState('')
  const intervalRef = useRef(null)

  // 实时预览
  useEffect(() => {
    const fetchPreview = async () => {
      try {
        const res = await axios.get('/api/compositor/preview')
        if (res.data.frame) {
          setPreviewSrc(`data:image/jpeg;base64,${res.data.frame}`)
        }
        setPreviewMeta(res.data)
      } catch (err) {
        message.error('无法获取预览画面，请确认后端服务已启动')
      }
    }

    intervalRef.current = setInterval(fetchPreview, 100) // 100ms刷新
    return () => clearInterval(intervalRef.current)
  }, [])

  const handleChromaColorChange = async (color) => {
    setChromaColor(color)
    try {
      await axios.post('/api/compositor/chromakey', { color })
      message.success(`抠图颜色已切换为${color === 'green' ? '绿色' : color === 'blue' ? '蓝色' : '红色'}`)
    } catch (err) {
      message.error('切换失败')
    }
  }

  const handleBackgroundUpload = async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      await axios.post('/api/compositor/upload/background', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      message.success('背景已上传')
    } catch (err) {
      message.error('上传失败')
    }
    return false
  }

  const handleOverlayUpload = async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('x', '50')
    formData.append('y', '50')
    
    try {
      await axios.post('/api/compositor/upload/overlay', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      message.success('贴片已添加')
    } catch (err) {
      message.error('上传失败')
    }
    return false
  }

  const handleAddTextOverlay = async () => {
    if (!textOverlay) return
    try {
      await axios.post('/api/compositor/overlay', {
        type: 'text',
        source: textOverlay,
        x: 50,
        y: 100,
        z_index: 1
      })
      message.success('文字贴片已添加')
      setTextOverlay('')
    } catch (err) {
      message.error('添加失败')
    }
  }

  const handleClearOverlays = async () => {
    await axios.post('/api/compositor/overlay/clear')
    message.success('贴片已清空')
  }

  return (
    <Card title="画面合成与实时预览">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 实时预览 */}
        <div>
          <Text strong>实时预览</Text>
          {previewMeta.source === 'demo' && (
            <Alert
              style={{ marginTop: 8 }}
              type="info"
              showIcon
              message="演示画面已启用"
              description="当前没有摄像头输入，系统正在返回可用于本地验收的动态合成画面。"
            />
          )}
          <div style={{
            marginTop: 8,
            width: '100%',
            maxWidth: 360,
            aspectRatio: '9/16',
            background: '#000',
            borderRadius: 8,
            overflow: 'hidden',
            position: 'relative',
            border: '2px solid #1890ff'
          }}>
            {previewSrc ? (
              <img src={previewSrc} alt="预览" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                color: '#fff',
                textAlign: 'center'
              }}>
                <VideoCameraOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>等待摄像头画面...</p>
              </div>
            )}
            <Tag color={previewMeta.source === 'camera' ? 'green' : 'blue'} style={{ position: 'absolute', top: 8, left: 8 }}>
              {previewMeta.source === 'camera' ? 'CAMERA PREVIEW' : 'DEMO PREVIEW'}
            </Tag>
          </div>
        </div>

        <Divider />

        {/* 绿幕抠图 */}
        <div>
          <Text strong><BgColorsOutlined /> 绿幕抠图</Text>
          <div style={{ marginTop: 8 }}>
            <Radio.Group value={chromaColor} onChange={e => handleChromaColorChange(e.target.value)}>
              <Radio.Button value="green">绿色</Radio.Button>
              <Radio.Button value="blue">蓝色</Radio.Button>
              <Radio.Button value="red">红色</Radio.Button>
            </Radio.Group>
          </div>
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            提示：使用绿幕拍摄时选择"绿色"，蓝幕选"蓝色"
          </Text>
        </div>

        <Divider />

        {/* 背景设置 */}
        <div>
          <Text strong><PictureOutlined /> 背景设置</Text>
          <div style={{ marginTop: 8 }}>
            <Dragger beforeUpload={handleBackgroundUpload} accept="image/*" maxCount={1}>
              <p>点击或拖拽上传背景图</p>
            </Dragger>
          </div>
        </div>

        <Divider />

        {/* 贴片管理 */}
        <div>
          <Text strong><PictureOutlined /> 贴片管理</Text>
          
          <Space direction="vertical" style={{ width: '100%', marginTop: 8 }}>
            <div>
              <Text>图片贴片：</Text>
              <Upload beforeUpload={handleOverlayUpload} accept="image/*" listType="text">
                <Button size="small">上传图片贴片</Button>
              </Upload>
            </div>
            
            <div>
              <Text>文字贴片：</Text>
              <Space>
                <input
                  value={textOverlay}
                  onChange={e => setTextOverlay(e.target.value)}
                  placeholder="输入文字内容"
                  style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #d9d9d9' }}
                />
                <Button size="small" type="primary" onClick={handleAddTextOverlay}>
                  添加文字
                </Button>
              </Space>
            </div>

            <Button size="small" danger onClick={handleClearOverlays}>
              清空所有贴片
            </Button>
          </Space>
        </div>
      </Space>
    </Card>
  )
}

export default PreviewPanel
