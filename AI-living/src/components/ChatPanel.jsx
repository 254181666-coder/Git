import React, { useState } from 'react'
import { Card, Input, Button, Space, message, List, Avatar, Form } from 'antd'
import axios from 'axios'

const { TextArea } = Input

const ChatPanel = () => {
  const [productInfo, setProductInfo] = useState('')
  const [messageInput, setMessageInput] = useState('')
  const [messages, setMessages] = useState([])

  const handleSetProductInfo = async () => {
    try {
      await axios.post('/api/ai/product', { info: productInfo })
      message.success('商品信息已保存')
    } catch (err) {
      message.error('保存失败')
    }
  }

  const handleSendMessage = async () => {
    if (!messageInput.trim()) return
    const userMsg = { type: 'user', content: messageInput }
    setMessages([...messages, userMsg])
    setMessageInput('')

    try {
      const res = await axios.post('/api/ai/chat', { message: messageInput })
      setMessages(prev => [...prev, { type: 'ai', content: res.data.response }])
    } catch (err) {
      message.error('发送失败')
    }
  }

  return (
    <Card title="AI智能互动">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <h3>商品信息</h3>
          <TextArea
            rows={4}
            placeholder="请输入商品信息..."
            value={productInfo}
            onChange={(e) => setProductInfo(e.target.value)}
          />
          <Button type="primary" onClick={handleSetProductInfo} style={{ marginTop: 8 }}>
            保存商品信息
          </Button>
        </div>
        <div>
          <h3>聊天互动</h3>
          <List
            dataSource={messages}
            renderItem={msg => (
              <List.Item>
                <Avatar style={{ backgroundColor: msg.type === 'user' ? '#1890ff' : '#52c41a' }}>
                  {msg.type === 'user' ? 'U' : 'AI'}
                </Avatar>
                <List.Item.Meta
                  title={msg.type === 'user' ? '观众' : '主播'}
                  description={msg.content}
                />
              </List.Item>
            )}
            style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', padding: 16, borderRadius: 4 }}
          />
          <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
            <Input
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onPressEnter={handleSendMessage}
              placeholder="输入消息..."
            />
            <Button type="primary" onClick={handleSendMessage}>发送</Button>
          </div>
        </div>
      </Space>
    </Card>
  )
}

export default ChatPanel