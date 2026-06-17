#!/bin/bash
# 启动内网穿透启动脚本
# 先启动 Streamlit，然后启动 ngrok

echo "========================================="
echo "启动综合经营数据看板"
echo "========================================="

cd "$(dirname "$0")/.."

# 检查 ngrok 是否已安装
if ! command -v ngrok &> /dev/null; then
    echo "ngrok 未安装，请先安装："
    echo "macOS: brew install --cask ngrok"
    echo "或者访问 https://ngrok.com/download"
    exit 1
fi

# 检查 ngrok 是否已配置（可选但推荐）
if [ ! -f ~/.ngrok2/ngrok.yml ]; then
    echo "提示：建议配置 ngrok authtoken，访问 https://ngrok.com 获取"
fi

# 在后台启动 Streamlit
echo "启动 Streamlit 服务..."
streamlit run app.py --server.port 8502 > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo "Streamlit PID: $STREAMLIT_PID"
sleep 3

# 启动 ngrok
echo "启动 ngrok 内网穿透..."
echo "访问 http://localhost:4040 查看 ngrok 状态"
ngrok http 8502
