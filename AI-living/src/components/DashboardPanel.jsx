import React, { useState, useEffect } from 'react'
import { Card, Statistic, Row, Col, Progress, Tag } from 'antd'
import { ClockCircleOutlined, DollarOutlined, VideoCameraOutlined } from '@ant-design/icons'
import axios from 'axios'

const DashboardPanel = ({ userInfo }) => {
  const [usageStats, setUsageStats] = useState({
    total_minutes: 0,
    total_cost: 0,
    remaining_minutes: 30,
    current_month_usage: 0
  })
  const [liveStatus, setLiveStatus] = useState({ is_streaming: false, is_scheduling: false })

  useEffect(() => {
    if (userInfo?.id) {
      fetchUsageStats()
    }
    fetchLiveStatus()
  }, [userInfo])

  const fetchUsageStats = async () => {
    try {
      const res = await axios.get(`/api/billing/usage/${userInfo.id}`)
      setUsageStats(res.data)
    } catch (err) {}
  }

  const fetchLiveStatus = async () => {
    try {
      const res = await axios.get('/api/live/status')
      setLiveStatus(res.data)
    } catch (err) {}
  }

  return (
    <div>
      <h2>数据看板</h2>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="今日剩余时长"
              value={usageStats.remaining_minutes}
              suffix="分钟"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: usageStats.remaining_minutes > 10 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="累计消费"
              value={usageStats.total_cost}
              precision={2}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="直播状态"
              value={liveStatus.is_streaming ? '直播中' : '未开播'}
              prefix={<VideoCameraOutlined />}
              valueStyle={{ color: liveStatus.is_streaming ? '#52c41a' : '#999' }}
            />
          </Card>
        </Col>
      </Row>
      <Card style={{ marginTop: 16 }}>
        <h3>本月使用统计</h3>
        <Progress
          percent={Math.min(100, (usageStats.current_month_usage / 30) * 100)}
          status={usageStats.current_month_usage > 25 ? 'exception' : 'normal'}
        />
        <p>已使用: {usageStats.current_month_usage.toFixed(1)} / 30 分钟</p>
      </Card>
    </div>
  )
}

export default DashboardPanel