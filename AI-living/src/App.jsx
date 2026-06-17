import React, { useState, useEffect } from 'react'
import { Layout, Menu, Typography, Card, Tabs, message, Button, Badge } from 'antd'
import { VideoCameraOutlined, AudioOutlined, MessageOutlined, PlaySquareOutlined, SettingOutlined, DashboardOutlined, UserOutlined, RobotOutlined, PictureOutlined, RocketOutlined } from '@ant-design/icons'
import axios from 'axios'
import AuthPanel from './components/AuthPanel'
import DashboardPanel from './components/DashboardPanel'
import LiveModePanel from './components/LiveModePanel'
import AiAssistantPanel from './components/AiAssistantPanel'
import PreviewPanel from './components/PreviewPanel'
import StreamPanel from './components/StreamPanel'
import AvatarPanel from './components/AvatarPanel'
import AudioPanel from './components/AudioPanel'
import ChatPanel from './components/ChatPanel'
import LivePlayPanel from './components/LivePlayPanel'
import ConfigPanel from './components/ConfigPanel'

const { Header, Content, Sider } = Layout
const { Title } = Typography

const demoUser = {
  id: 'dev-local',
  phone: 'dev-local',
  status: 'active',
  plan_type: 'free',
  remaining_minutes: 30,
  created_at: new Date().toISOString()
}

function App() {
  const [activeTab, setActiveTab] = useState('1')
  const [isAuthenticated, setIsAuthenticated] = useState(true)
  const [userInfo, setUserInfo] = useState(demoUser)
  const [liveStatus, setLiveStatus] = useState({ is_streaming: false, is_scheduling: false })

  useEffect(() => {
    checkHealth()
    fetchLiveStatus()
    const interval = setInterval(fetchLiveStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    try {
      const res = await axios.get('/api/health')
      console.log('服务状态:', res.data)
    } catch (err) {
      console.error('服务未启动:', err)
    }
  }

  const fetchLiveStatus = async () => {
    try {
      const res = await axios.get('/api/live/status')
      setLiveStatus(res.data)
    } catch (err) {
      setLiveStatus({ is_streaming: false, is_scheduling: false })
    }
  }

  const handleLogin = (token, user) => {
    localStorage.setItem('token', token)
    setIsAuthenticated(true)
    setUserInfo(user)
    message.success('登录成功')
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsAuthenticated(true)
    setUserInfo(demoUser)
    message.info('已重置为本地演示用户')
  }

  if (!isAuthenticated) {
    return <AuthPanel onLogin={handleLogin} />
  }

  const menuItems = [
    { key: '1', icon: <UserOutlined />, label: '真人直播模式' },
    { key: '2', icon: <RobotOutlined />, label: 'AI直播助手' },
    { key: '3', icon: <DashboardOutlined />, label: '数据看板' },
    { key: '4', icon: <PictureOutlined />, label: '画面合成预览' },
    { key: '5', icon: <RocketOutlined />, label: 'RTMP推流' },
    { key: '6', icon: <VideoCameraOutlined />, label: '数字人驱动' },
    { key: '7', icon: <AudioOutlined />, label: '音频驱动' },
    { key: '8', icon: <MessageOutlined />, label: 'AI智能互动' },
    { key: '9', icon: <PlaySquareOutlined />, label: '直播玩法' },
    { key: '10', icon: <SettingOutlined />, label: '设置' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Title level={3} style={{ margin: 0, color: '#1890ff' }}>播助手 Pro - AI数字人直播系统</Title>
        <div>
          <Badge count={liveStatus.is_streaming ? '直播中' : 0}>
            <Button onClick={handleLogout}>重置演示</Button>
          </Badge>
        </div>
      </Header>
      <Layout>
        <Sider width={200} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[activeTab]}
            items={menuItems}
            onClick={({ key }) => setActiveTab(key)}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content>
            <Card>
              <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
                { key: '1', label: '真人直播模式', children: <LiveModePanel /> },
                { key: '2', label: 'AI直播助手', children: <AiAssistantPanel /> },
                { key: '3', label: '数据看板', children: <DashboardPanel userInfo={userInfo} /> },
                { key: '4', label: '画面合成预览', children: <PreviewPanel /> },
                { key: '5', label: 'RTMP推流', children: <StreamPanel /> },
                { key: '6', label: '数字人驱动', children: <AvatarPanel /> },
                { key: '7', label: '音频驱动', children: <AudioPanel /> },
                { key: '8', label: 'AI智能互动', children: <ChatPanel /> },
                { key: '9', label: '直播玩法', children: <LivePlayPanel /> },
                { key: '10', label: '设置', children: <ConfigPanel /> },
              ]} />
            </Card>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default App
