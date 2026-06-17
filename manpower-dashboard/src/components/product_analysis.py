
"""
🍺 商品销售分析标签页 (Tab2)
- 分类总览
- 重点分类销量趋势
- 门店对比
- 各分类Top10
- 全品类Top10
- 通辽店商品结构分析
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import plot_chart, plot_pie
from src.config import BIG_CATEGORIES


def render(product_df: pd.DataFrame):
    """渲染商品销售分析标签页"""
    st.header("🍺 商品销售分析")

    if not product_df.empty:
        # 过滤临河街店
        product_df = product_df[product_df['store_name'] != '临河街店']

        total_amount = product_df['sales_amount'].sum()
        total_qty = product_df['quantity'].sum()
        total_products = product_df['product_name'].nunique()
        store_count = product_df['store_name'].nunique()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("统计门店数", f"{store_count}")
        with col2:
            st.metric("总商品数", f"{total_products}")
        with col3:
            st.metric("总销售数量", f"{int(total_qty):,}")
        with col4:
            st.metric("总销售金额", f"¥{total_amount:,.2f}")

        st.divider()

        st.subheader("一、商品分类总览")
        category_stats = product_df.groupby('big_category').agg({
            'product_name': 'nunique', 'quantity': 'sum', 'sales_amount': 'sum'
        }).reset_index()
        category_stats.columns = ['分类', '商品数', '总数量', '总金额']
        category_stats['总金额'] = category_stats['总金额']
        category_stats['平均单价'] = category_stats['总金额'] / category_stats['总数量']
        category_stats['占比'] = category_stats['总金额'] / total_amount * 100
        category_stats['is_wine'] = (category_stats['分类'] == '酒水')
        category_stats = category_stats.sort_values(['is_wine', '总金额'], ascending=[False, False])
        category_stats = category_stats.drop('is_wine', axis=1)

        display_cat_stats = category_stats.copy()
        display_cat_stats['总金额'] = display_cat_stats['总金额'].apply(lambda x: f"¥{x:,.2f}")
        display_cat_stats['平均单价'] = display_cat_stats['平均单价'].apply(lambda x: f"¥{x:.2f}")
        display_cat_stats['占比'] = display_cat_stats['占比'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_cat_stats, width='stretch', hide_index=True)

        st.divider()

        st.subheader("二、重点分类销量趋势")
        trend_df = product_df.groupby(['data_date', 'big_category']).agg({
            'quantity': 'sum'
        }).reset_index()
        trend_df = trend_df[trend_df['big_category'] != '其他']

        fig_trend = px.line(trend_df,
                           x='data_date',
                           y='quantity',
                           color='big_category',
                           title='各分类销量趋势对比',
                           labels={'quantity': '销量', 'big_category': '分类', 'data_date': '日期'},
                           color_discrete_map={
                               '酒水': '#d62728', '下酒菜': '#1f77b4',
                               '干果': '#ff7f0e', '氛围': '#2ca02c',
                               '备品': '#9467bd', '日场': '#8c564b'},
                           markers=True)
        fig_trend.update_layout(template="plotly_white", xaxis_title="日期", yaxis_title="销量")
        st.plotly_chart(fig_trend, use_container_width=True)

        st.divider()

        st.subheader("三、重点分类销量对比")
        category_summary = product_df.groupby('big_category').agg({
            'quantity': 'sum', 'sales_amount': 'sum'
        }).reset_index()
        category_summary.columns = ['分类', '总销量', '总销售额']
        category_summary['总销售额'] = category_summary['总销售额']

        category_summary['排序'] = category_summary['分类'].apply(lambda x: BIG_CATEGORIES.index(x) if x in BIG_CATEGORIES else 999)
        category_summary = category_summary.sort_values(['排序', '总销售额'], ascending=[True, False]).drop('排序', axis=1)

        col_cat1, col_cat2 = st.columns(2)
        with col_cat1:
            fig_cat_bar = px.bar(category_summary, x='分类', y='总销量',
                               color='分类', title='各分类销量对比',
                               color_discrete_map={
                                   '酒水': '#d62728', '下酒菜': '#1f77b4',
                                   '干果': '#ff7f0e', '氛围': '#2ca02c',
                                   '备品': '#9467bd', '日场': '#8c564b',
                                   '其他': '#7f7f7f'})
            fig_cat_bar.update_layout(xaxis_title='', showlegend=False)
            plot_chart(fig_cat_bar)

        with col_cat2:
            category_show = category_summary.copy()
            category_show['总销售额'] = category_show['总销售额'].apply(lambda x: f"¥{x:,.2f}")
            category_show['总销量'] = category_show['总销量'].apply(lambda x: f"{int(x):,}")
            category_show = category_show.reindex(columns=['分类', '总销量', '总销售额'])
            st.dataframe(category_show, width='stretch', hide_index=True)

        st.divider()

        st.subheader("四、各门店分类销售对比")
        store_cat_summary = product_df.groupby(['store_name', 'big_category']).agg({
            'sales_amount': 'sum', 'quantity': 'sum'
        }).reset_index()
        store_cat_summary.columns = ['store_name', 'category', 'total_amount', 'total_qty']
        store_cat_summary['total_amount'] = store_cat_summary['total_amount']

        col_amt, col_qty = st.columns(2)
        with col_amt:
            st.write("##### 销售额对比")
            store_pivot = store_cat_summary.pivot(index='store_name', columns='category', values='total_amount').fillna(0)
            store_pivot['合计'] = store_pivot.sum(axis=1)
            store_pivot = store_pivot.sort_values('合计', ascending=False)

            ordered_cols = []
            for cat in BIG_CATEGORIES:
                if cat in store_pivot.columns:
                    ordered_cols.append(cat)
            ordered_cols.append('合计')
            store_pivot = store_pivot[ordered_cols]

            display_store_pivot = store_pivot.copy()
            for col in display_store_pivot.columns:
                display_store_pivot[col] = display_store_pivot[col].apply(lambda x: f"¥{x:,.0f}")
            st.dataframe(display_store_pivot, width='stretch')

        with col_qty:
            st.write("##### 销量对比")
            store_pivot_qty = store_cat_summary.pivot(index='store_name', columns='category', values='total_qty').fillna(0)
            store_pivot_qty['合计'] = store_pivot_qty.sum(axis=1)
            store_pivot_qty = store_pivot_qty.sort_values('合计', ascending=False)
            store_pivot_qty = store_pivot_qty[ordered_cols]

            display_store_qty = store_pivot_qty.copy()
            for col in display_store_qty.columns:
                display_store_qty[col] = display_store_qty[col].apply(lambda x: f"{int(x):,}")
            st.dataframe(display_store_qty, width='stretch')

        st.divider()

        st.subheader("五、各分类 Top10 商品")
        for cat in BIG_CATEGORIES:
            cat_df = product_df[product_df['big_category'] == cat].copy()
            if cat_df.empty:
                continue
            cat_agg = cat_df.groupby('product_name').agg({
                'quantity': 'sum', 'sales_amount': 'sum', 'store_name': 'nunique'
            }).reset_index()
            cat_agg.columns = ['商品名称', '销售数量', '总销售额', '销售门店数']
            cat_agg['总销售额'] = cat_agg['总销售额']
            cat_agg['平均单价'] = cat_agg['总销售额'] / cat_agg['销售数量']
            cat_agg = cat_agg.sort_values('总销售额', ascending=False).head(10)

            with st.expander(f"📌 {cat}类 Top10"):
                display_cat_agg = cat_agg.copy()
                display_cat_agg['总销售额'] = display_cat_agg['总销售额'].apply(lambda x: f"¥{x:,.2f}")
                display_cat_agg['平均单价'] = display_cat_agg['平均单价'].apply(lambda x: f"¥{x:.2f}")
                st.dataframe(display_cat_agg, width='stretch', hide_index=True)

        st.divider()

        st.subheader("六、全品类 Top10")
        all_top10 = product_df.groupby(['product_name', 'big_category']).agg({
            'quantity': 'sum', 'sales_amount': 'sum', 'store_name': 'nunique'
        }).reset_index()
        all_top10.columns = ['商品名称', '分类', '销售数量', '总销售额', '销售门店数']
        all_top10['总销售额'] = all_top10['总销售额']
        all_top10['平均单价'] = all_top10['总销售额'] / all_top10['销售数量']
        all_top10 = all_top10.sort_values('总销售额', ascending=False).head(10)

        display_all_top10 = all_top10.copy()
        display_all_top10['总销售额'] = display_all_top10['总销售额'].apply(lambda x: f"¥{x:,.2f}")
        display_all_top10['平均单价'] = display_all_top10['平均单价'].apply(lambda x: f"¥{x:.2f}")
        st.dataframe(display_all_top10, width='stretch', hide_index=True)

        st.divider()

        st.subheader("七、通辽店商品结构分析")
        tongliao_df = product_df[product_df['store_name'] == '通辽店'].copy()
        if not tongliao_df.empty:
            tongliao_total = tongliao_df['sales_amount'].sum()
            tongliao_qty = tongliao_df['quantity'].sum()
            tongliao_products = tongliao_df['product_name'].nunique()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总销售金额", f"¥{tongliao_total:,.2f}")
            with col2:
                st.metric("总销售数量", f"{int(tongliao_qty):,}")
            with col3:
                st.metric("商品种类", f"{tongliao_products}")

            st.divider()

            tongliao_cat = tongliao_df.groupby('big_category').agg({
                'quantity': 'sum', 'sales_amount': 'sum'
            }).reset_index()
            tongliao_cat.columns = ['分类', '销量', '销售额']
            tongliao_cat['销售额'] = tongliao_cat['销售额']
            tongliao_cat['占比'] = tongliao_cat['销售额'] / tongliao_total * 100
            tongliao_cat = tongliao_cat.sort_values('销售额', ascending=False)

            cat_col1, cat_col2 = st.columns(2)
            with cat_col1:
                st.write("##### 分类销售额占比")
                fig_pie = px.pie(tongliao_cat, values='销售额', names='分类', hole=0.4)
                fig_pie.update_layout(template="plotly_white", height=350,
                                     legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
                plot_chart(fig_pie)

            with cat_col2:
                st.write("##### 分类销售额排名")
                fig_bar = px.bar(tongliao_cat, x='分类', y='销售额',
                               text=[f"¥{v:,.0f}" for v in tongliao_cat['销售额']], color='分类')
                fig_bar.update_traces(textposition='outside')
                fig_bar.update_layout(template="plotly_white", height=350, showlegend=False, xaxis_title="")
                plot_chart(fig_bar)

            st.divider()

            st.write("##### 通辽店TOP5商品")
            top5_products = tongliao_df.groupby('product_name').agg({
                'quantity': 'sum', 'sales_amount': 'sum'
            }).reset_index()
            top5_products.columns = ['商品名称', '销量', '销售额']
            top5_products['销售额'] = top5_products['销售额']
            top5_products['平均单价'] = top5_products['销售额'] / top5_products['销量']
            top5_products = top5_products.sort_values('销售额', ascending=False).head(5)

            display_top5 = top5_products.copy()
            display_top5['销售额'] = display_top5['销售额'].apply(lambda x: f"¥{x:,.2f}")
            display_top5['平均单价'] = display_top5['平均单价'].apply(lambda x: f"¥{x:.2f}")
            st.dataframe(display_top5, width='stretch', hide_index=True)
        else:
            st.info("暂无通辽店数据")
    else:
        st.warning("⚠️ 未找到商品销售数据")
