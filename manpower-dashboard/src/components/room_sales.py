"""
🎤 包房销售分析标签页
分析重点商品分类在各包房的销售覆盖情况
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_room_product_data(start_date: str, end_date: str):
    """从数据库加载包房销售数据"""
    from src.database import query
    
    sql = """
        SELECT
            s.store_name as 门店,
            ps.room_no as 包厢编号,
            ps.room_type as 包厢类型,
            ps.product_name as 商品名称,
            ps.quantity as 售卖数量,
            ps.sales_amount as 收入金额,
            ps.data_date as 销售日期
        FROM product_sales_detail ps
        JOIN stores s ON ps.store_id = s.id
        WHERE ps.data_date BETWEEN ? AND ?
          AND s.store_name NOT IN ('临河街店', '总部')
          AND ps.room_no IS NOT NULL
          AND ps.room_no != ''
          AND ps.room_no != '超市包'
        ORDER BY s.store_name, ps.room_no
    """
    df = query(sql, [start_date, end_date])
    if not df.empty:
        df['收入金额'] = pd.to_numeric(df['收入金额'], errors='coerce').fillna(0) / 10
        df['大分类'] = df['商品名称'].apply(get_big_category)
        # 用room_no作为包厢唯一标识，展示时同时显示编号和类型
        df['包厢'] = df['包厢编号'].astype(str)
    return df


from src.config import CATEGORY_MAP

PRODUCT_CATEGORY_EXTRA = {
    '啤酒': '酒水', '饮料': '酒水', '可口可乐': '酒水', '青岛啤酒': '酒水', '雪花勇闯': '酒水', '崂山啤酒': '酒水',
    '冷荤': '下酒菜', '鸭货': '下酒菜', '小海鲜': '下酒菜', '黄瓜拼盘': '下酒菜', '明太鱼': '下酒菜', '五香毛豆': '下酒菜', '水煮花生': '下酒菜',
    '简餐': '下酒菜', '烤炸小食': '下酒菜',
    '瓜子': '干果', '蜜饯': '干果', '零食': '干果', '拼盘': '干果', '洽洽': '干果', '金鸽': '干果', '眼镜小猫': '干果', '安小脆': '干果', '花椒锅巴': '干果', '自营干果': '干果',
    '礼品': '氛围', '第三方': '氛围', '道具': '氛围', '果盘': '氛围', '华子礼炮': '氛围', '豪华果盘': '氛围', '精美果盘': '氛围', '至尊果盘': '氛围',
    '备品': '备品', '纸抽': '备品', '开机套': '备品', '麦克风套': '备品',
    '日场零食': '日场',
}

def get_big_category(product_name):
    for keyword, category in sorted(PRODUCT_CATEGORY_EXTRA.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in str(product_name):
            return category
    for keyword, category in sorted(CATEGORY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in str(product_name):
            return category
    return '其他'


def render():
    """渲染包房销售分析标签页"""
    st.header("🎤 包房销售分析")

    from src.database import query
    min_date_result = query("SELECT MIN(data_date) as md FROM product_sales_detail")
    max_date_result = query("SELECT MAX(data_date) as md FROM product_sales_detail")

    if min_date_result.empty or max_date_result.empty:
        st.warning("⚠️ 数据库中没有日期数据")
        return

    max_date = pd.to_datetime(max_date_result.iloc[0]['md'])
    min_date = max_date

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", value=max_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    df = load_room_product_data(start_date_str, end_date_str)

    if df.empty:
        st.warning("⚠️ 在指定日期范围内未找到包房销售数据")
        return

    stores = sorted(df['门店'].unique())

    selected_store = st.session_state.get('selected_room_store', None)
    if selected_store and selected_store not in stores:
        selected_store = None
        st.session_state['selected_room_store'] = None

    st.subheader("🏪 门店选择")

    col_btn, col_select = st.columns([2, 1])
    with col_btn:
        if st.button("🌐 全部门店", key="room_all_stores", type="primary" if not selected_store else "secondary"):
            st.session_state['selected_room_store'] = None

    with col_select:
        store_options = ["选择门店..."] + stores
        selected_idx = 0
        if selected_store and selected_store in stores:
            selected_idx = stores.index(selected_store) + 1
        selected = st.selectbox("门店", store_options, index=selected_idx, key="room_store_select")
        if selected != "选择门店...":
            st.session_state['selected_room_store'] = selected

    selected_store = st.session_state.get('selected_room_store', None)

    if selected_store and selected_store not in stores:
        selected_store = None
        st.session_state['selected_room_store'] = None

    KEY_CATEGORIES = ['酒水', '下酒菜', '干果', '氛围', '备品']

    if selected_store:
        df = df[df['门店'] == selected_store]

    total_amount = df['收入金额'].sum()
    total_qty = df['售卖数量'].sum()
    room_count = df[df['包厢'] != '']['包厢'].nunique()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总销售额", f"¥{total_amount:,.2f}")
    with col2:
        st.metric("总销售量", f"{int(total_qty):,}")
    with col3:
        st.metric("包厢数", f"{room_count}")

    st.divider()

    analysis_df = df[df['包厢'] != '']

    if selected_store:
        st.subheader(f"📋 {selected_store} - 各包房分类销售情况")
    else:
        st.subheader("📋 各店包房分类销售覆盖率对比")

    store_stats = []
    target_stores = [selected_store] if selected_store else stores

    for store in target_stores:
        store_df = analysis_df[analysis_df['门店'] == store]
        total_rooms = store_df['包厢'].nunique()

        if total_rooms == 0:
            continue

        for cat in KEY_CATEGORIES:
            cat_rooms = store_df[store_df['大分类'] == cat]['包厢'].nunique()
            coverage_rate = cat_rooms / total_rooms * 100
            store_stats.append({
                '门店': store,
                '分类': cat,
                '总包厢数': total_rooms,
                '有销售包厢数': cat_rooms,
                '覆盖率': coverage_rate
            })

    stats_df = pd.DataFrame(store_stats)

    if not stats_df.empty:
        pivot_df = stats_df.pivot(index='门店', columns='分类', values='覆盖率')
        pivot_df = pivot_df[['酒水', '下酒菜', '干果', '氛围']]
        st.dataframe(pivot_df.style.format("{:.1f}%"), use_container_width=True)

        st.divider()

        fig = px.bar(
            stats_df, x='门店', y='覆盖率', color='分类',
            barmode='group',
            title='各店分类销售覆盖率对比',
            labels={'覆盖率': '覆盖率 (%)', '门店': '门店'},
            color_discrete_sequence=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        )
        fig.update_layout(template="plotly_white", height=400)
        fig.update_yaxes(range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**说明:** 覆盖率 = 有该分类销售的包厢数 ÷ 总包厢数 × 100%")

    if selected_store:
        st.divider()
        st.subheader(f"📊 {selected_store} - 各包房详细情况")

        room_detail = []
        rooms = analysis_df['包厢'].unique()
        for room in rooms:
            room_df = analysis_df[analysis_df['包厢'] == room]
            row = {'包厢': room}
            for cat in KEY_CATEGORIES:
                cat_sales = room_df[room_df['大分类'] == cat]['收入金额'].sum()
                row[cat] = "✅" if cat_sales > 0 else "❌"
            room_detail.append(row)

        detail_df = pd.DataFrame(room_detail)
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader(f"📦 {selected_store} - 分类销售明细")

        for cat in KEY_CATEGORIES:
            cat_df = analysis_df[analysis_df['大分类'] == cat]
            if cat_df.empty:
                continue

            cat_rooms = cat_df['包厢'].nunique()
            cat_revenue = cat_df['收入金额'].sum()
            cat_qty = cat_df['售卖数量'].sum()

            with st.expander(f"{cat} - {cat_rooms}个包厢有销售 | ¥{cat_revenue:,.2f} | {int(cat_qty)}件"):
                product_summary = cat_df.groupby('商品名称').agg({
                    '售卖数量': 'sum',
                    '收入金额': 'sum'
                }).reset_index()
                product_summary.columns = ['商品', '销量', '销售额']
                product_summary = product_summary.sort_values('销售额', ascending=False)
                st.dataframe(product_summary, hide_index=True)

    st.markdown("**图例:** ✅ 有销售  |  ❌ 无销售")
