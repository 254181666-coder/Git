// UWB轨迹追踪前端脚本

// 初始化ECharts
var myChart = echarts.init(document.getElementById('chart-container'));

// 房间尺寸（需要根据你的实际情况修改）
var ROOM_WIDTH = 10;   // 米
var ROOM_HEIGHT = 8;   // 米

// 基站坐标（需要和后端config.py保持一致）
var ANCHORS = [
    {x: 0, y: 0, name: '基站1'},
    {x: 0, y: 8, name: '基站2'},
    {x: 10, y: 8, name: '基站3'},
    {x: 10, y: 0, name: '基站4'},
];

// 轨迹数据
var trackData = [];
var currentPosition = null;
var tracking = true;
var updateInterval = null;

// 转换坐标到画布坐标系
function toCanvasX(x) {
    return (x / ROOM_WIDTH) * 100;
}
function toCanvasY(y) {
    // Y轴翻转，因为画布坐标系原点在左上角
    return 100 - (y / ROOM_HEIGHT) * 100;
}

// 绘制图表
function renderChart() {
    var option = {
        title: {
            text: '室内定位轨迹',
            left: 'center'
        },
        tooltip: {
            formatter: function(params) {
                if (params.componentType === 'markPoint') {
                    return params.name + ': ' + params.data.coord;
                }
                return 'X: ' + params.value[0].toFixed(2) + 'm, Y: ' + params.value[1].toFixed(2) + 'm';
            }
        },
        grid: {
            left: 50,
            right: 20,
            top: 50,
            bottom: 50,
            containLabel: true
        },
        xAxis: {
            min: 0,
            max: ROOM_WIDTH,
            name: 'X (m)',
            type: 'value'
        },
        yAxis: {
            min: 0,
            max: ROOM_HEIGHT,
            name: 'Y (m)',
            type: 'value'
        },
        series: [
            {
                name: '轨迹',
                type: 'line',
                smooth: true,
                symbol: 'none',
                lineStyle: {
                    color: '#1890ff',
                    width: 2
                },
                data: trackData.map(p => [p.x, p.y])
            },
            {
                name: '当前位置',
                type: 'scatter',
                symbolSize: 15,
                itemStyle: {
                    color: '#ff4d4f'
                },
                data: currentPosition ? [[currentPosition.x, currentPosition.y]] : []
            },
            {
                name: '基站',
                type: 'scatter',
                symbolSize: 10,
                itemStyle: {
                    color: '#52c41a'
                },
                markPoint: {
                    data: ANCHORS.map(a => ({
                        coord: [a.x, a.y],
                        name: a.name,
                        symbolSize: 15
                    }))
                }
            }
        ]
    };

    myChart.setOption(option);
}

// 获取最新位置
async function fetchPosition() {
    try {
        const response = await fetch('/api/position');
        const data = await response.json();
        if (data.success && data.position) {
            currentPosition = {
                x: data.position.x,
                y: data.position.y,
                timestamp: data.position.timestamp
            };
            trackData.push({x: data.position.x, y: data.position.y});
            
            // 更新信息面板
            document.getElementById('current-x').textContent = data.position.x.toFixed(2);
            document.getElementById('current-y').textContent = data.position.y.toFixed(2);
            document.getElementById('update-time').textContent = new Date().toLocaleString();
            
            renderChart();
        }
    } catch (error) {
        console.error('获取位置失败:', error);
    }
}

// 加载历史轨迹
async function loadHistory() {
    try {
        const response = await fetch('/api/history?tag_id=0');
        const data = await response.json();
        if (data.success && data.history) {
            trackData = data.history.map(h => ({x: h.x, y: h.y}));
            if (trackData.length > 0) {
                currentPosition = trackData[trackData.length - 1];
                document.getElementById('current-x').textContent = currentPosition.x.toFixed(2);
                document.getElementById('current-y').textContent = currentPosition.y.toFixed(2);
            }
            renderChart();
        }
    } catch (error) {
        console.error('加载历史失败:', error);
    }
}

// 切换追踪
function toggleTracking() {
    tracking = !tracking;
    var btn = document.getElementById('toggle-btn');
    if (tracking) {
        btn.textContent = '暂停追踪';
        updateInterval = setInterval(fetchPosition, 200);
    } else {
        btn.textContent = '开始追踪';
        clearInterval(updateInterval);
    }
}

// 清除轨迹
function clearTrace() {
    trackData = [];
    currentPosition = null;
    document.getElementById('current-x').textContent = '--';
    document.getElementById('current-y').textContent = '--';
    document.getElementById('update-time').textContent = '--';
    renderChart();
}

// 初始化
window.onload = function() {
    // 加载历史轨迹
    loadHistory();
    // 开始定时更新
    updateInterval = setInterval(fetchPosition, 200);
    // 自适应resize
    window.addEventListener('resize', function() {
        myChart.resize();
    });
};
