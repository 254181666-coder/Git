import React, { useState } from 'react'
import { Card, Form, Input, Button, Tabs, message } from 'antd'
import axios from 'axios'

const AuthPanel = ({ onLogin }) => {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')

  const handleRegister = async (values) => {
    setLoading(true)
    try {
      const res = await axios.post('/api/auth/register', values)
      localStorage.setItem('token', res.data.access_token)
      onLogin(res.data.access_token, res.data.user)
    } catch (err) {
      message.error(err.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (values) => {
    setLoading(true)
    try {
      const res = await axios.post('/api/auth/login', values)
      localStorage.setItem('token', res.data.access_token)
      const userRes = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${res.data.access_token}` }
      })
      onLogin(res.data.access_token, userRes.data)
    } catch (err) {
      message.error(err.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const tabItems = [
    {
      key: 'login',
      label: '登录',
      children: (
        <Form onFinish={handleLogin} layout="vertical">
          <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      )
    },
    {
      key: 'register',
      label: '注册',
      children: (
        <Form onFinish={handleRegister} layout="vertical">
          <Form.Item name="phone" label="手机号" rules={[{ required: true }]}>
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注册
            </Button>
          </Form.Item>
        </Form>
      )
    }
  ]

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card title="播助手 Pro" style={{ width: 400 }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  )
}

export default AuthPanel