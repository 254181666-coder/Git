import React, { useState, useEffect } from 'react'
import { Card, Button, Space, List, Avatar, Input, Typography, Badge } from 'antd'
import { RobotOutlined, MessageOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Text } = Typography

const AiAssistantPanel = () => {
  const [visible, setVisible] = useState(true)
  const [questions, setQuestions] = useState([])
  const [aiSuggestions, setAiSuggestions] = useState([])
  const [currentTip, setCurrentTip] = useState('')

  useEffect(() => {
    const interval = setInterval(() => {
      if (visible) {
        generateSuggestions()
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [visible])

  const generateSuggestions = async () => {
    try {
      const res = await axios.post('/api/ai/chat', {
        message: '作为直播带货主播，给我3个当前应该说的直播话术建议，简洁明了'
      })
      setAiSuggestions([res.data.response])
    } catch (err) {}
  }

  const mockQuestions = [
    { id: 1, question: '这个多少钱？', time: '刚刚' },
    { id: 2, question: '质量怎么样？', time: '1分钟前' },
    { id: 3, question: '发什么快递？', time: '2分钟前' },
  ]

  const mockSuggestions = [
    '欢迎新进来的宝宝们！今天给大家带来超级好物~',
    '关注主播不迷路，点赞到1万抽大奖！',
    '这款产品库存有限，赶紧下单吧！',
  ]

  return (
    <Card
      title={
        <Space>
          <Badge dot={visible} color="green">
            <RobotOutlined /> AI直播助手
          </Badge>
        </Space>
      }
      extra={
        <Button size="small" onClick={() => setVisible(!visible)}>
          {visible ? '隐藏' : '显示'}
        </Button>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {visible && (
          <>
            {/* AI话术建议 */}
            <div>
              <Text strong style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <MessageOutlined /> AI话术建议
              </Text>
              <List
                dataSource={mockSuggestions}
                renderItem={item => (
                  <List.Item style={{ padding: '8px 0' }}>
                    <Button
                      type="link"
                      size="small"
                      onClick={() => setCurrentTip(item)}
                      style={{ textAlign: 'left', padding: 0 }}
                    >
                      {item}
                    </Button>
                  </List.Item>
                )}
              />
            </div>

            {/* 观众问题 */}
            <div>
              <Text strong style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <MessageOutlined /> 观众问题
              </Text>
              <List
                dataSource={mockQuestions}
                renderItem={item => (
                  <List.Item style={{ padding: '8px 0' }}>
                    <List.Item.Meta
                      avatar={<Avatar style={{ backgroundColor: '#1890ff' }}>U</Avatar>}
                      title={<Text type="secondary" style={{ fontSize: 12 }}>{item.time}</Text>}
                      description={item.question}
                    />
                    <Button size="small" type="primary">
                      AI回复
                    </Button>
                  </List.Item>
                )}
              />
            </div>

            {/* 当前提示 */}
            {currentTip && (
              <div>
                <Text strong>当前提示</Text>
                <Input.TextArea
                  rows={3}
                  value={currentTip}
                  readOnly
                  style={{ marginTop: 8 }}
                />
              </div>
            )}
          </>
        )}
      </Space>
    </Card>
  )
}

export default AiAssistantPanel