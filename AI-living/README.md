# 播助手 - 数字人直播系统

基于飞书文档开发的数字人直播系统，支持多种驱动模式、智能互动和直播玩法。

## 功能特性

### 1. 数字人驱动
- 摄像头驱动
- 数字人缓存驱动
- 原音原画驱动
- 双数字人驱动

### 2. 音频驱动
- 碎片化音频素材管理
- 音频剪辑功能
- 随机/顺序播放模式
- 智能口型同步

### 3. 智能互动
- AI实时聊天回复
- 商品信息配置
- 对话历史记录

### 4. 直播玩法
- 录播转播
- 画面去重
- 抖音转播
- 报时功能

## 项目结构

```
AI-living/
├── backend/
│   ├── app.py              # Flask后端服务
│   └── modules/
│       ├── avatar_driver.py    # 数字人驱动模块
│       ├── audio_driver.py     # 音频驱动模块
│       ├── chatbot.py          # 智能聊天模块
│       └── live_play.py        # 直播玩法模块
├── src/
│   ├── components/
│   │   ├── AvatarPanel.jsx     # 数字人驱动面板
│   │   ├── AudioPanel.jsx      # 音频驱动面板
│   │   ├── ChatPanel.jsx       # 智能互动面板
│   │   ├── LivePlayPanel.jsx   # 直播玩法面板
│   │   └── ConfigPanel.jsx     # 设置面板
│   ├── App.jsx
│   └── main.jsx
├── requirements.txt        # Python依赖
├── package.json            # Node.js依赖
├── vite.config.js
└── index.html
```

## 快速开始

### 1. 安装Python依赖

```bash
cd backend
pip install -r ../requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置OpenAI API：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 启动后端服务

```bash
cd backend
python app.py
```

后端服务将在 `http://localhost:5000` 启动

### 4. 安装前端依赖

```bash
npm install
```

### 5. 启动前端开发服务器

```bash
npm run dev
```

前端将在 `http://localhost:3000` 启动

## 使用说明

### 数字人驱动
1. 选择驱动模式（摄像头/缓存/原音原画/双数字人）
2. 开启摄像头进行实时驱动

### 音频驱动
1. 上传音频素材
2. 使用音频剪辑功能生成分段音频
3. 选择播放模式（随机/顺序）

### 智能互动
1. 配置商品信息
2. 在聊天窗口输入问题，AI将自动回复

### 直播玩法
1. 加载录播视频
2. 开启画面去重
3. 使用报时功能

## 技术栈

- **后端**: Flask, OpenCV, PyAudio, OpenAI
- **前端**: React, Ant Design, Vite
- **AI**: OpenAI GPT-3.5/4

## API接口

### 健康检查
`GET /api/health`

### 数字人驱动
- `POST /api/avatar/mode` - 设置驱动模式
- `POST /api/avatar/camera/start` - 开启摄像头
- `POST /api/avatar/camera/stop` - 关闭摄像头

### 音频驱动
- `POST /api/audio/clips` - 加载音频素材
- `POST /api/audio/mode` - 设置播放模式
- `POST /api/audio/split` - 剪辑音频

### 智能互动
- `POST /api/chat/product` - 设置商品信息
- `POST /api/chat` - 发送聊天消息

### 直播玩法
- `POST /api/live/video` - 加载视频
- `POST /api/live/deduplicate` - 画面去重
- `GET /api/live/timestamp` - 获取时间戳

## 注意事项

1. 确保已安装所需的系统依赖（如PyAudio、OpenCV等）
2. 配置有效的OpenAI API密钥才能使用智能互动功能
3. 音频和视频处理需要充足的系统资源
