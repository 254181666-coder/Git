from datetime import date, timedelta
from calendar import monthrange


def parse_money(value):
    if value is None:
        return 0.0
    try:
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return 0.0
        text = text.replace(",", "").replace("￥", "").replace("¥", "")
        return float(text)
    except:
        return 0.0


def first_existing(row, columns):
    for col in columns:
        if col in row and row[col] is not None:
            value = row[col]
            try:
                import pandas as pd
                if pd.isna(value):
                    continue
            except:
                pass
            return value
    return None


def normalize_header_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    text = text.replace("\n", "").replace("\r", "")
    text = text.replace(" ", "").replace("\u3000", "")
    return text


def load_salary_draft_dataframe(contents):
    import pandas as pd
    import io

    raw = pd.read_excel(io.BytesIO(contents), sheet_name=0, header=None)
    header_row = None
    for i in range(min(12, len(raw))):
        labels = [normalize_header_text(v) for v in raw.iloc[i].tolist()]
        if any(v in ["姓名", "姓名"] or "姓名" in v for v in labels) and any(v in ["实发工资", "实际发放", "实发"] for v in labels):
            header_row = i
            break
    if header_row is None:
        return pd.read_excel(io.BytesIO(contents))

    sub_header_row = header_row + 1 if header_row + 1 < len(raw) else None
    header_values = raw.iloc[header_row].tolist()
    sub_values = raw.iloc[sub_header_row].tolist() if sub_header_row is not None else [None] * len(header_values)
    columns = []
    seen = {}
    last_group = ""
    for idx, value in enumerate(header_values):
        header = normalize_header_text(value)
        sub = normalize_header_text(sub_values[idx]) if idx < len(sub_values) else ""
        if header:
            last_group = header
        final = header or sub
        if sub and header in ["奖励补助", "考勤扣款", "店面费用扣款", "五险一金扣款"]:
            final = f"{header}_{sub}"
        elif sub and not header and last_group in ["奖励补助", "考勤扣款", "店面费用扣款", "五险一金扣款"]:
            final = f"{last_group}_{sub}"
        elif sub and not header:
            final = sub
        if not final:
            final = f"未命名{idx + 1}"
        seen[final] = seen.get(final, 0) + 1
        if seen[final] > 1:
            final = f"{final}_{seen[final]}"
        columns.append(final)

    start_row = header_row + 2
    df = raw.iloc[start_row:].copy()
    df.columns = columns
    df = df.dropna(how='all')
    return df


def month_range_func(year, month):
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])
