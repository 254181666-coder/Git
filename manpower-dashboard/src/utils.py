"""
工具函数 + Plotly图表包装器
集中管理通用工具，消除重复代码
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
from io import BytesIO
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
from .config import (
    NAME_MAP, CARD_LEVEL_INTERVALS, 
    COLOR_YOY_2025, COLOR_YOY_2026, 
    COLOR_CATEGORY, COLOR_PERIOD
)

warnings.filterwarnings("ignore", category=DeprecationWarning, module="plotly")


def plot_chart(fig, use_container_width=True):
    """渲染图表，使用 st.plotly_chart 并消除废弃参数警告"""
    st.plotly_chart(fig, use_container_width=use_container_width)


def plot_pie(px_expr, use_container_width=True):
    """处理 px.pie() 内联图表"""
    st.plotly_chart(px_expr, use_container_width=use_container_width)


def normalize_store_name(name):
    """
    标准化门店名称
    规则：
    - 去除私人订制KTV、糖果华庭KTV前缀
    - 统一为"某某店"格式
    - 特殊映射：江南秀→松原一店，斯堡特→松原二店
    - 排除临河街店、总部
    """
    if pd.isna(name):
        return None
    name = str(name).strip()
    for p in ['私人订制KTV', '私人订制 KTV', '糖果华庭KTV', '糖果华庭 KTV', 'KTV']:
        name = name.replace(p, '')
    name = name.strip()
    if '临河街' in name or name == '总部' or name == '合计' or name == 'nan':
        return None
    if not name:
        return None
    if not name.endswith('店') and name not in ['松原一店', '松原二店']:
        name = name + '店'
    if name in NAME_MAP:
        name = NAME_MAP[name]
    return name


def simplify_store_name(name):
    """简化门店名称（兼容旧接口，内部调用normalize_store_name）"""
    return normalize_store_name(name)


def calculate_gini_coefficient(values):
    """计算基尼系数"""
    values = [v for v in values if v > 0]
    if len(values) < 2:
        return 0.0
    values = sorted(values)
    n = len(values)
    cumsum = sum(values)
    if cumsum == 0:
        return 0.0
    gini_sum = sum((2 * i + 1 - n) * v for i, v in enumerate(values))
    return gini_sum / (n * cumsum)


def format_number(num: float) -> str:
    """格式化数字显示"""
    if num >= 10000:
        return f"{num/10000:.2f}万"
    return f"{num:.2f}"


def format_currency(amount: float, decimal_places: int = 2) -> str:
    """格式化货币显示"""
    return f"¥{amount:,.{decimal_places}f}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """格式化百分比显示"""
    return f"{value:.{decimal_places}f}%"


# ============ 新增日期处理工具 ============

def sort_df_by_day_column(df: pd.DataFrame, day_col: str = '日期') -> pd.DataFrame:
    """
    按日期列排序（解决字符串排序问题）
    
    Args:
        df: 待排序的DataFrame
        day_col: 日期列名（格式为 '01', '02', ..., '31'）
        
    Returns:
        排序后的DataFrame
    """
    df = df.copy()
    df['_day_num'] = pd.to_numeric(df[day_col], errors='coerce')
    df = df.sort_values('_day_num').drop('_day_num', axis=1)
    return df


def get_date_display(df: pd.DataFrame, date_col: str = 'data_date', output_col: str = '日期', format_str: str = '%d') -> pd.DataFrame:
    """
    为DataFrame添加日期显示列
    
    Args:
        df: 原始DataFrame
        date_col: 日期列名
        output_col: 输出列名
        format_str: 日期格式字符串
        
    Returns:
        添加了日期显示列的DataFrame
    """
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    df[output_col] = df[date_col].dt.strftime(format_str)
    return df


# ============ 新增储值卡级处理工具 ============

def get_card_level(amount: float) -> Optional[str]:
    """
    根据金额获取对应的卡级
    
    Args:
        amount: 储值金额（注意：2025年用 stored_amount，2026年用 drink_principal）
        
    Returns:
        卡级名称或None
    """
    if not amount or amount <= 0:
        return None
    
    for min_val, max_val, name in CARD_LEVEL_INTERVALS:
        if min_val <= amount < max_val:
            return name
    
    return None


def aggregate_card_levels(df: pd.DataFrame, amount_col: str, count_col: str = None) -> Tuple[Dict[str, float], Dict[str, int]]:
    """
    聚合储值卡级数据
    
    Args:
        df: 储值数据DataFrame
        amount_col: 金额列名
        count_col: 次数列名（可选，默认逐行计数）
        
    Returns:
        (金额聚合字典, 数量聚合字典)
    """
    amount_by_level = {}
    count_by_level = {}
    
    for idx, row in df.iterrows():
        amount = row[amount_col]
        level = get_card_level(amount)
        
        if level:
            if level not in amount_by_level:
                amount_by_level[level] = 0
                count_by_level[level] = 0
            
            amount_by_level[level] += amount
            if count_col:
                count_by_level[level] += row[count_col]
            else:
                count_by_level[level] += 1
    
    return amount_by_level, count_by_level


# ============ 新增图表配置工具 ============

def get_yoy_color_map(prefix: str = '') -> Dict[str, str]:
    """
    获取同比分析的颜色映射
    
    Args:
        prefix: 列名前缀（如 'revenue_'）
        
    Returns:
        颜色映射字典
    """
    return {
        f'{prefix}2025': COLOR_YOY_2025,
        f'{prefix}2026': COLOR_YOY_2026,
        '2025年': COLOR_YOY_2025,
        '2026年': COLOR_YOY_2026,
        '2025': COLOR_YOY_2025,
        '2026': COLOR_YOY_2026
    }


def get_category_color_map() -> Dict[str, str]:
    """获取商品分类颜色映射"""
    return COLOR_CATEGORY


def get_period_color_map() -> Dict[str, str]:
    """获取时段颜色映射"""
    return COLOR_PERIOD


def update_chart_layout(fig, template: str = 'plotly_white', height: int = 350, 
                        show_legend: bool = True, legend_horizontal: bool = True):
    """
    统一更新图表布局
    
    Args:
        fig: Plotly图表对象
        template: 模板名称
        height: 图表高度
        show_legend: 是否显示图例
        legend_horizontal: 图例是否水平排列
    """
    layout_kwargs = {
        'template': template,
        'height': height
    }
    
    if show_legend and legend_horizontal:
        layout_kwargs['legend'] = dict(
            orientation="h", 
            yanchor="bottom", 
            y=-0.3, 
            xanchor="center", 
            x=0.5
        )
    elif not show_legend:
        layout_kwargs['showlegend'] = False
    
    fig.update_layout(**layout_kwargs)
    return fig


# ============ 新增数据导出工具 ============

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = 'Sheet1') -> bytes:
    """
    将DataFrame转换为Excel字节流
    
    Args:
        df: 要导出的DataFrame
        sheet_name: 工作表名称
        
    Returns:
        Excel文件的字节流
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output.getvalue()


def download_dataframe_button(df: pd.DataFrame, filename: str = 'data.xlsx', 
                               button_text: str = '📥 下载数据', key: str = None):
    """
    创建DataFrame下载按钮
    
    Args:
        df: 要下载的DataFrame
        filename: 下载的文件名
        button_text: 按钮文字
        key: Streamlit按钮的key
    """
    excel_data = to_excel_bytes(df)
    st.download_button(
        label=button_text,
        data=excel_data,
        file_name=filename,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key=key
    )


def to_csv_bytes(df: pd.DataFrame, encoding: str = 'utf-8-sig') -> bytes:
    """
    将DataFrame转换为CSV字节流
    
    Args:
        df: 要导出的DataFrame
        encoding: 编码格式
        
    Returns:
        CSV文件的字节流
    """
    return df.to_csv(index=False, encoding=encoding).encode(encoding)


def download_csv_button(df: pd.DataFrame, filename: str = 'data.csv',
                         button_text: str = '📥 下载CSV', key: str = None):
    """
    创建CSV下载按钮
    
    Args:
        df: 要下载的DataFrame
        filename: 下载的文件名
        button_text: 按钮文字
        key: Streamlit按钮的key
    """
    csv_data = to_csv_bytes(df)
    st.download_button(
        label=button_text,
        data=csv_data,
        file_name=filename,
        mime='text/csv',
        key=key
    )


# ============ 新增性能监控工具 ============

class PerformanceTimer:
    """简易性能计时器"""
    
    def __init__(self, name: str = 'Operation'):
        self.name = name
        self.start_time = None
    
    def start(self):
        self.start_time = datetime.now()
    
    def stop(self) -> float:
        if self.start_time is None:
            return 0.0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = self.stop()
        print(f"[{self.name}] Elapsed: {elapsed:.3f}s")
