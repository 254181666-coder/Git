"""
📈 基础经营数据标签页 (Tab1)
- 收入/储值趋势
- 商品分类销售趋势
- 通辽店标杆分析
- 门店日收入明细
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List

from src.database import query
from src.utils import plot_chart, plot_pie
from src.config import BIG_CATEGORIES, CATEGORY_MAP


@st.cache_data
def load_revenue_data(start_date: str, end_date: str) -> pd.DataFrame:
    query_str = """
        SELECT sd.data_date, s.store_name,
               sd.revenue, sd.customers, sd.staff_count, sd.efficiency
        FROM store_daily sd
        JOIN stores s ON sd.store_id = s.id
        WHERE sd.data_date BETWEEN ? AND ?
          AND s.store_name NOT IN ('临河街店', '总部')
        ORDER BY sd.data_date, sd.revenue DESC
    """
    df = query(query_str, (start_date, end_date))
    df['data_date'] = pd.to_datetime(df['data_date'])
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0) / 10
    df['efficiency'] = pd.to_numeric(df['efficiency'], errors='coerce').fillna(0) / 10
    return df


@st.cache_data
def load_stored_value_data(start_date: str, end_date: str) -> pd.DataFrame:
    query_str = """
        SELECT sv.data_date, s.store_name,
               SUM(sv.stored_amount) as total_stored_amount,
               SUM(sv.stored_count) as total_stored_count
        FROM stored_value sv
        JOIN stores s ON sv.store_id = s.id
        WHERE sv.data_date BETWEEN ? AND ?
          AND s.store_name NOT IN ('临河街店', '总部')
        GROUP BY sv.data_date, s.store_name
        ORDER BY sv.data_date
    """
    df = query(query_str, (start_date, end_date))
    df['data_date'] = pd.to_datetime(df['data_date'])
    df['total_stored_amount'] = pd.to_numeric(df['total_stored_amount'], errors='coerce').fillna(0) / 10
    return df


@st.cache_data
def get_valid_stores() -> list:
    df = query("""
        SELECT store_name
        FROM stores
        WHERE store_name LIKE '%店%'
          AND store_name != '临河街店'
        ORDER BY store_name
    """)
    return df['store_name'].tolist()


@st.cache_data
def load_product_data_from_db(start_date: str, end_date: str, stores: list = None):
    store_condition = ""
    params = [start_date, end_date]
    if stores:
        placeholders = ', '.join(['?'] * len(stores))
        store_condition = f"AND s.store_name IN ({placeholders})"
        params.extend(stores)
    query_str = f"""
        SELECT ps.data_date, s.store_name, ps.product_name,
               ps.category as original_category, ps.big_category,
               ps.quantity, ps.sales_amount
        FROM product_sales_summary ps
        JOIN stores s ON ps.store_id = s.id
        WHERE ps.data_date BETWEEN ? AND ?
          AND s.store_name NOT IN ('临河街店', '总部')
          {store_condition}
        ORDER BY ps.data_date, s.store_name
    """
    df = query(query_str, params)
    df['data_date'] = pd.to_datetime(df['data_date'])
    df['sales_amount'] = pd.to_numeric(df['sales_amount'], errors='coerce').fillna(0) / 10
    return df


def render(revenue_df: pd.DataFrame, stored_df: pd.DataFrame, product_df: pd.DataFrame,
           start_date_str: str, end_date_str: str):
    """渲染基础经营数据标签页"""
    st.header("📈 基础经营数据")
    
    # 收入趋势
    st.header("💰 收入/储值趋势")
    
    if not revenue_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            daily_revenue = revenue_df.groupby('data_date').agg({
                'revenue': 'sum'
            }).reset_index()
            daily_revenue.columns = ['data_date', 'total_revenue']
            daily_revenue['data_date_str'] = daily_revenue['data_date'].dt.strftime('%Y-%m-%d')
            
            fig_line = px.line(
                daily_revenue, x='data_date_str', y='total_revenue',
                title="每日收入趋势",
                labels={'data_date_str': '日期', 'total_revenue': '收入 (元)'},
                markers=True
            )
            fig_line.update_traces(line=dict(color='#0074D9', width=3), marker=dict(size=8))
            fig_line.update_layout(template="plotly_white", height=400)
            plot_chart(fig_line)
        
        with col2:
            if not stored_df.empty:
                daily_stored = stored_df.groupby('data_date').agg({
                    'total_stored_amount': 'sum'
                }).reset_index()
                daily_stored['data_date_str'] = daily_stored['data_date'].dt.strftime('%Y-%m-%d')
                
                fig_stored = px.line(
                    daily_stored, x='data_date_str', y='total_stored_amount',
                    title="每日储值金额",
                    labels={'data_date_str': '日期', 'total_stored_amount': '储值金额 (元)'},
                    markers=True
                )
                fig_stored.update_traces(line=dict(color='#FF4136', width=3), marker=dict(size=8))
                fig_stored.update_layout(template="plotly_white", height=400)
                plot_chart(fig_stored)
                
                total_stored = daily_stored['total_stored_amount'].sum()
                total_count = stored_df['total_stored_count'].sum()
                st.metric("总储值金额", f"¥{total_stored:,.2f}")
                st.metric("总储值笔数", f"{int(total_count):,} 笔")
    
    # 商品分类销售趋势
    st.header("🍺 重点商品分类销售趋势")
    
    if not product_df.empty:
        selected_categories = st.multiselect(
            "选择要查看的分类（可多选）",
            options=BIG_CATEGORIES,
            default=BIG_CATEGORIES
        )
        
        if selected_categories:
            filtered_df = product_df[product_df['big_category'].isin(selected_categories)]
            
            amount_col = 'sales_amount'
            qty_col = 'quantity'
            
            st.subheader("📈 每日销售量趋势")
            daily_cat = filtered_df.groupby(['data_date', 'big_category']).agg({
                qty_col: 'sum', amount_col: 'sum'
            }).reset_index()
            daily_cat.columns = ['data_date', 'big_category', 'total_qty', 'total_amount']
            daily_cat = daily_cat[daily_cat['big_category'] != '其他']
            daily_cat['data_date_str'] = daily_cat['data_date'].dt.strftime('%Y-%m-%d')
            
            fig_line_qty = px.line(
                daily_cat, x='data_date_str', y='total_qty', color='big_category',
                title="各分类每日销售量趋势",
                labels={'data_date_str': '日期', 'total_qty': '销售量 (件)', 'big_category': '分类'},
                markers=True
            )
            fig_line_qty.update_layout(
                template="plotly_white", height=400,
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                xaxis=dict(type='category')
            )
            plot_chart(fig_line_qty)
            
            st.divider()
            
            # 通辽店标杆分析
            st.subheader("🏆 通辽店标杆分析（作为对照）")
            tongliao_df = product_df[product_df['store_name'] == '通辽店']
            if not tongliao_df.empty:
                tongliao_cat = tongliao_df.groupby('big_category').agg({
                    'quantity': 'sum', 'sales_amount': 'sum'
                }).reset_index()
                tongliao_cat.columns = ['big_category', 'total_qty', 'total_amount']
                tongliao_cat = tongliao_cat.sort_values('total_amount', ascending=False)
                
                date_range_str = f"{start_date_str} 至 {end_date_str}"
                
                plot_pie(
                    px.pie(tongliao_cat, values='total_amount', names='big_category',
                           title=f'通辽店各分类销售额占比 ({date_range_str})', hole=0.4
                    ).update_layout(template="plotly_white", height=400)
                )
                
                with st.expander("📋 通辽店各分类明细"):
                    st.dataframe(tongliao_cat, width='stretch', hide_index=True)
            else:
                st.info("暂无通辽店数据")
            
            st.divider()
            
            # 总计统计
            st.subheader(f"📊 总计统计 ({start_date_str} ~ {end_date_str})")
            cat_summary = filtered_df.groupby('big_category').agg({
                qty_col: 'sum', amount_col: 'sum'
            }).reset_index()
            cat_summary.columns = ['big_category', 'total_qty', 'total_amount']
            cat_summary = cat_summary.sort_values('total_amount', ascending=False)
            
            col_pie1, col_pie2 = st.columns(2)
            with col_pie1:
                plot_pie(
                    px.pie(cat_summary, values='total_amount', names='big_category',
                           title=f'各分类销售额占比 ({start_date_str} ~ {end_date_str})', hole=0.4
                    ).update_layout(template="plotly_white", height=400)
                )
            with col_pie2:
                plot_pie(
                    px.pie(cat_summary, values='total_qty', names='big_category',
                           title=f'各分类销售量占比 ({start_date_str} ~ {end_date_str})', hole=0.4
                    ).update_layout(template="plotly_white", height=400)
                )
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                fig_bar_amount = px.bar(
                    cat_summary, x='big_category', y='total_amount', color='big_category',
                    title=f"各分类销售额总计 ({start_date_str} ~ {end_date_str})",
                    labels={'big_category': '分类', 'total_amount': '销售额 (元)'},
                    text='total_amount'
                )
                fig_bar_amount.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside')
                fig_bar_amount.update_layout(template="plotly_white", height=400, showlegend=False, bargap=0.15)
                plot_chart(fig_bar_amount)
            
            with col2:
                fig_bar_qty = px.bar(
                    cat_summary, x='big_category', y='total_qty', color='big_category',
                    title=f"各分类销售量总计 ({start_date_str} ~ {end_date_str})",
                    labels={'big_category': '分类', 'total_qty': '销售量 (件)'},
                    text='total_qty'
                )
                fig_bar_qty.update_traces(texttemplate='%{text:,.0f}件', textposition='outside')
                fig_bar_qty.update_layout(template="plotly_white", height=400, showlegend=False, bargap=0.15)
                plot_chart(fig_bar_qty)
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 分类销售额排名")
                cat_summary_sorted = cat_summary.sort_values('total_amount', ascending=False)
                for _, row in cat_summary_sorted.iterrows():
                    st.metric(f"{row['big_category']}", f"¥{row['total_amount']:,.2f}", delta=f"{int(row['total_qty'])} 件")
            
            with col_b:
                st.subheader("📊 分类销售量排名")
                cat_summary_qty = cat_summary.sort_values('total_qty', ascending=False)
                for _, row in cat_summary_qty.iterrows():
                    st.metric(f"{row['big_category']}", f"{int(row['total_qty']):,} 件", delta=f"¥{row['total_amount']:,.2f}")
        else:
            st.info("请从上方选择要查看的分类")
    else:
        st.warning("⚠️ 未找到商品销售数据")
    
    # 最新数据表格
    st.header("📋 最新数据")
    st.subheader("门店日收入明细")
    
    display_df = revenue_df.sort_values(['data_date', 'revenue'], ascending=[False, False]).head(10)
    display_df['revenue'] = display_df['revenue'].apply(lambda x: f"¥{x:,.2f}")
    display_df['efficiency'] = display_df['efficiency'].apply(lambda x: f"¥{x:,.2f}" if pd.notna(x) else "-")
    display_df['日期'] = display_df['data_date'].dt.strftime('%Y-%m-%d')
    display_df['星期'] = display_df['data_date'].dt.day_name('zh_CN')
    
    st.dataframe(
        display_df[['日期', '星期', 'store_name', 'revenue', 'customers', 'efficiency']],
        width='stretch', hide_index=True
    )
