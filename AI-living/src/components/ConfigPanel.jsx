import React, { useState } from 'react'
import { Card, Form, Input, Button, message, Space } from 'antd'
import axios from 'axios'

const ConfigPanel = () => {
  const [loading, setLoading] = useState(false)

  const handleSave = async (values) => {
    setLoading(true)
    try {
      message.success('配置已保存')
    } catch (err) {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="系统设置">
      <Form
        layout="vertical"
        onFinish={handleSave}
        initialValues={{
          openai_base_url: 'https://api.openai.com/v1',
          sadtalker_endpoint: 'http://your-aliyun-ip:8080'
        }}
      >
        <Form.Item label="OpenAI API Key" name="openai_api_key">
          <Input.Password placeholder="sk-..." />
        </Form.Item>
        <Form.Item label="OpenAI Base URL" name="openai_base_url">
          <Input placeholder="https://api.openai.com/v1" />
        </Form.Item>
        <Form.Item label="SadTalker Endpoint" name="sadtalker_endpoint">
          <Input placeholder="http://your-aliyun-ip:8080" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            保存配置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}

export default ConfigPanel