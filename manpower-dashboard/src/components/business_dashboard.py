
"""
📊 经营总览页面
功能：商品销量分析、时段客单价分析
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.database import query
from src.utils import plot_chart, format_currency


@st.cache_data(ttl=300)
def load_core_store_data(start_date: str, end_date: str):
    """加载门店经营核心数据"""
    sql = """
        SELECT sd.data_date, s.store_name,
               COALESCE(sd.total_revenue, sd.revenue) as revenue,
               sd.customers,
               sd.efficiency,
               sd.daily_batch_consumption,
               sd.stored_card_sales,
               sd.times_card_sales
        FROM store_daily sd
        JOIN stores s ON s.id = sd.store_id
        WHERE sd.data_date BETWEEN ? AND ?
        ORDER BY sd.data_date, s.store_name
    """
    df = query(sql, (start_date, end_date))
    df['data_date'] = pd.to_datetime(df['data_date'])
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0) / 10
    df['stored_card_sales'] = pd.to_numeric(df['stored_card_sales'], errors='coerce').fillna(0) / 10
    df['times_card_sales'] = pd.to_numeric(df['times_card_sales'], errors='coerce').fillna(0) / 10
    df['customers'] = pd.to_numeric(df['customers'], errors='coerce').fillna(0)
    df['efficiency'] = pd.to_numeric(df['efficiency'], errors='coerce').fillna(0) / 10
    df['daily_batch_consumption'] = pd.to_numeric(df['daily_batch_consumption'], errors='coerce').fillna(0) / 10
    return df


@st.cache_data(ttl=300)
def load_time_period_data(start_date: str, end_date: str):
    """加载时段经营数据（使用order_daily表）"""
    # 从 order_daily 表读取时段数据，包含所有order_type
    sql = """
    SELECT od.data_date, od.store_name, od.time_period,
           od.order_type, od.item_count, od.revenue
    FROM order_daily od
    WHERE od.data_date BETWEEN ? AND ?
    """
    df = query(sql, (start_date, end_date))
    if not df.empty:
        df['data_date'] = pd.to_datetime(df['data_date'])
        df['item_count'] = pd.to_numeric(df['item_count'], errors='coerce').fillna(0)
        df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
    return df


@st.cache_data(ttl=300)
def load_product_data(start_date: str, end_date: str):
    """加载商品销售数据"""
    sql = """
        SELECT ps.data_date, s.store_name, ps.product_name, ps.big_category,
            SUM(ps.quantity) as quantity, SUM(ps.sales_amount) as sales_amount
        FROM product_sales_summary ps
        JOIN stores s ON ps.store_id = s.id
        WHERE ps.data_date BETWEEN ? AND ?
        GROUP BY ps.data_date, s.store_name, ps.product_name, ps.big_category
        ORDER BY ps.data_date, quantity DESC
    """
    df = query(sql, (start_date, end_date))
    if not df.empty:
        df['data_date'] = pd.to_datetime(df['data_date'])
        df['sales_amount'] = pd.to_numeric(df['sales_amount'], errors='coerce').fillna(0) / 10
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    return df


@st.cache_data(ttl=60)
def get_available_dates():
    """获取可用的日期范围（使用 order_daily 和 store_daily 的交集）"""
    df1 = query("SELECT MIN(data_date) as min1, MAX(data_date) as max1 FROM order_daily")
    df2 = query("SELECT MIN(data_date) as min2, MAX(data_date) as max2 FROM store_daily")

    # 转换为 datetime.date 类型
    def to_date(val):
        if val is None:
            return None
        if isinstance(val, str):
            return pd.to_datetime(val).date()
        if hasattr(val, 'date'):
            return val.date()
        return val

    min1 = to_date(df1['min1'].iloc[0])
    max1 = to_date(df1['max1'].iloc[0])
    min2 = to_date(df2['min2'].iloc[0])
    max2 = to_date(df2['max2'].iloc[0])

    min_date = max([d for d in [min1, min2] if d is not None])
    max_date = min([d for d in [max1, max2] if d is not None])
    return min_date, max_date


def render(date_granularity: str = "日", start_date: str = None, end_date: str = None, selected_stores: list = None):
    """渲染经营总览页面"""
    st.header("📊 经营总览")

    min_date, max_date = get_available_dates()
    if min_date is None:
        st.warning("⚠️ 数据库中无数据")
        return

    if start_date is None:
        start_date = str(min_date)
    if end_date is None:
        end_date = str(max_date)

    st.info(f"📅 日期范围: {start_date} ~ {end_date} (经营数据可用: {min_date} ~ {max_date})")

    df_core = load_core_store_data(start_date, end_date)
    df_time = load_time_period_data(start_date, end_date)
    df_product = load_product_data(start_date, end_date)

    # ------------ 店面筛选 ------------
    if selected_stores is not None and len(selected_stores) > 0:
        df_core = df_core[df_core['store_name'].isin(selected_stores)]
        df_time = df_time[df_time['store_name'].isin(selected_stores)]
        df_product = df_product[df_product['store_name'].isin(selected_stores)]
    else:
        # 默认筛选掉临河街店
        df_core = df_core[df_core['store_name'] != '临河街店']
        df_time = df_time[df_time['store_name'] != '临河街店']

    if df_core.empty and df_time.empty:
        st.warning(f"⚠️ 该日期范围内无经营数据！")
        return

    st.divider()

    # ------------ 核心指标卡片 ------------
    if not df_core.empty:
        total_revenue = df_core['revenue'].sum()
        total_customers = df_core['customers'].sum()
        avg_price = total_revenue / total_customers if total_customers > 0 else 0
        total_stored = df_core['stored_card_sales'].sum() + df_core['times_card_sales'].sum()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总营业额", format_currency(total_revenue, 0))
        with col2:
            st.metric("总客流", f"{int(total_customers):,} 人")
        with col3:
            st.metric("平均客单价", format_currency(avg_price, 1))
        with col4:
            st.metric("总储值", format_currency(total_stored, 0))

        st.divider()

    # ------------ 时段客单价分析 ------------
    st.subheader("⏰ 时段客单价分析")
    if not df_time.empty:

        # 按时段聚合统计
        period_order = ['日场', '黄金场', '午夜场']
        time_stats = df_time.groupby('time_period').agg({
            'item_count': 'sum', 'revenue': 'sum'
        }).reset_index()

        # 确保按正确的顺序显示时段
        time_stats['排序'] = time_stats['time_period'].apply(lambda x: period_order.index(x) if x in period_order else 999)
        time_stats = time_stats.sort_values('排序').drop('排序', axis=1)

        # 计算客单价
        time_stats['客单价'] = time_stats.apply(
            lambda x: x['revenue'] / x['item_count'] if x['item_count'] > 0 else 0, axis=1
        )

        col_time1, col_time2 = st.columns(2)
        with col_time1:
            fig_rev = px.bar(time_stats, x='time_period', y='revenue',
                           title='各时段营业额对比',
                           color='time_period',
                           color_discrete_map={'日场': '#1f77b4', '黄金场': '#ff7f0e', '午夜场': '#2ca02c'})
            fig_rev.update_layout(xaxis_title='', showlegend=False)
            fig_rev.update_traces(width=0.5)  # 增加柱形宽度
            plot_chart(fig_rev)

        with col_time2:
            fig_price = px.bar(time_stats, x='time_period', y='客单价',
                             title='各时段客单价对比',
                             color='time_period',
                             color_discrete_map={'日场': '#1f77b4', '黄金场': '#ff7f0e', '午夜场': '#2ca02c'})
            fig_price.update_layout(xaxis_title='', showlegend=False)
            fig_price.update_traces(width=0.5)  # 增加柱形宽度
            plot_chart(fig_price)

        # 表格显示
        time_stats_show = time_stats.copy()
        time_stats_show['revenue'] = time_stats_show['revenue'].apply(lambda x: f"¥{x:,.2f}")
        time_stats_show['客单价'] = time_stats_show['客单价'].apply(lambda x: f"¥{x:,.2f}")
        time_stats_show['item_count'] = time_stats_show['item_count'].apply(lambda x: f"{int(x):,}")
        time_stats_show.columns = ['时段', '消费数量', '营业额', '客单价']
        st.dataframe(time_stats_show, width='stretch', hide_index=True)

    else:
        st.info("暂无时段分析数据")

    st.divider()

    # ------------ 商品销量分析 ------------
    if not df_product.empty:
        st.subheader("🍺 商品销量分析")

        product_total = df_product.groupby(['product_name', 'big_category']).agg({
            'quantity': 'sum', 'sales_amount': 'sum'
        }).reset_index()
        product_top10 = product_total.sort_values('sales_amount', ascending=False).head(10)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig_p = px.bar(product_top10,
                          x='product_name', y='sales_amount',
                          color='big_category',
                          title='商品销售额TOP10',
                          labels={'product_name': '商品名称', 'sales_amount': '销售额(元)'})
            plot_chart(fig_p)

        with col_p2:
            product_top10_show = product_top10.copy()
            product_top10_show['sales_amount'] = product_top10_show['sales_amount'].apply(lambda x: f"¥{x:,.2f}")
            product_top10_show['quantity'] = product_top10_show['quantity'].apply(lambda x: f"{int(x):,}")
            product_top10_show.columns = ['商品名称', '分类', '销量(件)', '销售额(元)']
            st.dataframe(product_top10_show, width='stretch', hide_index=True)

        st.divider()

        st.subheader("📦 商品分类分析")
        category_stats = df_product.groupby('big_category').agg({
            'quantity': 'sum', 'sales_amount': 'sum'
        }).reset_index().sort_values('sales_amount', ascending=False)

        col_cat1, col_cat2 = st.columns(2)
        with col_cat1:
            fig_cat = px.pie(category_stats,
                           names='big_category',
                           values='sales_amount',
                           title='各分类销售额占比',
                           hole=0.4)
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_cat2:
            category_stats_show = category_stats.copy()
            category_stats_show['sales_amount'] = category_stats_show['sales_amount'].apply(lambda x: f"¥{x:,.2f}")
            category_stats_show['quantity'] = category_stats_show['quantity'].apply(lambda x: f"{int(x):,}")
            category_stats_show.columns = ['大分类', '销量(件)', '销售额(元)']
            st.dataframe(category_stats_show, width='stretch', hide_index=True)
    else:
        st.info("暂无商品销售数据")

    st.divider()

    # ------------ 门店对比 ------------
    if not df_core.empty:
        st.subheader("🏪 门店经营对比")
        store_stats = df_core.groupby('store_name').agg({
            'revenue': 'sum', 'customers': 'sum',
            'stored_card_sales': 'sum', 'times_card_sales': 'sum'
        }).reset_index().sort_values('revenue', ascending=False)

        store_stats['客单价'] = store_stats.apply(lambda x: x['revenue'] / x['customers'] if x['customers'] > 0 else 0, axis=1)
        store_stats['总储值'] = store_stats['stored_card_sales'] + store_stats['times_card_sales']

        fig_store = px.bar(store_stats, x='store_name', y='revenue',
                       title='各门店营业额对比',
                       labels={'store_name': '门店', 'revenue': '营业额(元)'},
                       color='store_name')
        fig_store.update_layout(showlegend=False)
        plot_chart(fig_store)

        store_stats_show = store_stats.copy()
        for col in ['revenue', 'stored_card_sales', 'times_card_sales', '总储值', '客单价']:
            store_stats_show[col] = store_stats_show[col].apply(lambda x: f"¥{x:,.2f}")
        store_stats_show['customers'] = store_stats_show['customers'].apply(lambda x: f"{int(x):,}")
        store_stats_show.columns = ['门店', '营业额', '客流', '储值卡', '次卡', '客单价', '总储值']
        st.dataframe(store_stats_show, width='stretch', hide_index=True)
