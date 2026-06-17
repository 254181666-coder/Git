"""
综合经营数据看板 — 重构版
唯一入口: streamlit run app.py

架构:
- src/config.py      → 全局配置（路径、常量、分类）
- src/database.py    → 统一数据库操作层
- src/utils.py       → 工具函数 + Plotly图表包装器
- src/components/    → 每个标签页一个独立模块
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# 加载环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except ImportError:
        pass

from src.config import TAB_OPTIONS
from src.database import query
from src.components.business_overview import (
    load_revenue_data, load_stored_value_data,
    load_product_data_from_db, get_valid_stores, render as render_business
)
from src.components.business_dashboard import render as render_dashboard
from src.components.product_analysis import render as render_product
from src.components.staff_efficiency import (
    load_staffing_data, render as render_staff
)
from src.components.room_sales import render as render_room
from src.components.customer_retention import render as render_customer
from src.components.year_over_year import render as render_yoy

from src.components.qingzhou_daily import QingZhouDailyAPI, render as render_qingzhou


@st.cache_data(ttl=60)
def get_date_range():
    """缓存日期范围，每分钟刷新一次"""
    min_date = query("SELECT MIN(data_date) as md FROM store_daily").iloc[0, 0]
    max_date = query("SELECT MAX(data_date) as md FROM store_daily").iloc[0, 0]
    return min_date, max_date


st.set_page_config(
    page_title="综合经营数据看板",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@media (max-width: 768px) {
    .main .block-container { padding: 1rem !important; }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }
    .stDataFrame { font-size: 0.75rem !important; }
    .js-plotly-plot .plotly .modebar { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 综合经营数据看板")

# ============================================
# 获取日期范围
# ============================================
min_date_db, max_date_db = get_date_range()
valid_stores = get_valid_stores()

# ============================================
# 侧边栏 — 筛选条件 + 标签页导航
# ============================================
st.sidebar.header("筛选条件")

# 日/周/月切换
date_granularity = st.sidebar.radio(
    "日期粒度",
    options=["日", "周", "月"],
    index=1,
    horizontal=True
)

# 根据粒度计算默认日期范围
from datetime import timedelta
today = pd.to_datetime(max_date_db)

if date_granularity == "日":
    default_start = today
    default_end = today
elif date_granularity == "周":
    default_start = today - timedelta(days=6)
    default_end = today
else:  # 月
    first_day_of_month = today.replace(day=1)
    default_start = first_day_of_month
    default_end = today

date_range = st.sidebar.date_input(
    f"选择日期范围（{date_granularity}）",
    value=(default_start, default_end),
    min_value=pd.to_datetime(min_date_db),
    max_value=pd.to_datetime(max_date_db)
)

selected_store = st.sidebar.selectbox(
    "选择门店",
    options=["全部门店"] + valid_stores,
    index=0
)

if selected_store == "全部门店":
    selected_stores = valid_stores
else:
    selected_stores = [selected_store]

if len(date_range) == 2:
    start_date, end_date = date_range
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
else:
    st.warning("请选择完整的日期范围")
    st.stop()

# ============================================
# 标签页导航（sidebar radio + session_state，解决切换日期后跳回首页的问题）
# ============================================
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

active_tab = st.sidebar.radio(
    "切换页面",
    TAB_OPTIONS,
    index=st.session_state.active_tab,
    label_visibility="collapsed"
)
st.session_state.active_tab = TAB_OPTIONS.index(active_tab)

# 轻舟日报日期选择
qingzhou_api = QingZhouDailyAPI()
qingzhou_available_dates = qingzhou_api.get_available_dates()
if qingzhou_available_dates:
    qz_default = pd.to_datetime(qingzhou_available_dates[0])
    qz_min = pd.to_datetime(qingzhou_available_dates[-1])
    qz_max = pd.to_datetime(qingzhou_available_dates[0])
    qingzhou_date = st.sidebar.date_input(
        "📊 轻舟日报日期",
        value=qz_default, min_value=qz_min, max_value=qz_max
    )
    qingzhou_date_str = qingzhou_date.strftime("%Y-%m-%d")
else:
    qingzhou_date_str = pd.to_datetime(max_date_db).strftime("%Y-%m-%d")

# ============================================
# 加载数据（统一加载一次，各组件共享）
# ============================================
revenue_df = load_revenue_data(start_date_str, end_date_str)
stored_df = load_stored_value_data(start_date_str, end_date_str)
product_df = load_product_data_from_db(start_date_str, end_date_str, selected_stores)
staffing_df = load_staffing_data()

if selected_stores:
    revenue_df = revenue_df[revenue_df['store_name'].isin(selected_stores)]
    stored_df = stored_df[stored_df['store_name'].isin(selected_stores)]

# ============================================
# 按标签页渲染对应组件
# ============================================
if active_tab == "📊 经营总览":
    render_dashboard(date_granularity, start_date_str, end_date_str, selected_stores)

elif active_tab == "🍺 商品销售分析":
    render_product(product_df)

elif active_tab == "🎤 包房销售分析":
    render_room()

elif active_tab == "👥 人效分析":
    render_staff(revenue_df, staffing_df, start_date_str, end_date_str)

elif active_tab == "📋 客户存留分析":
    render_customer()

elif active_tab == "📈 同比分析":
    render_yoy()

elif active_tab == "📊 日报分析":
    render_qingzhou(qingzhou_api, qingzhou_date_str, qingzhou_available_dates)

# 页脚
st.divider()
st.caption(f"数据更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
