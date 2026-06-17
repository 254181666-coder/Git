from typing import List


def can_confirm_attendance(record, pos_rule=None):
    if record.result_morning == "正常" or record.result_afternoon == "正常":
        return True
    if record.result_morning in ["公休", "病假", "事假", "事假两小时"] or record.result_afternoon in ["公休", "病假", "事假", "事假两小时"]:
        return True
    if pos_rule and pos_rule.is_rotating_shift:
        return True
    if record.check_in_time or record.check_out_time:
        return True
    return False


def build_attendance_summary(records):
    summary = {
        "total": len(records),
        "normal": 0,
        "late": 0,
        "early": 0,
        "absent": 0,
        "missing": 0,
        "leave": 0,
        "pending": 0,
        "confirmed": 0,
    }
    for record in records:
        morning = record.result_morning or ""
        afternoon = record.result_afternoon or ""
        if record.status == "confirmed":
            summary["confirmed"] += 1
        else:
            summary["pending"] += 1
        if morning == "正常" and afternoon == "正常":
            summary["normal"] += 1
        if morning.startswith("迟到") or (record.late_minutes or 0) > 0:
            summary["late"] += 1
        if afternoon.startswith("早退") or (record.early_leave_minutes or 0) > 0:
            summary["early"] += 1
        if record.is_full_day_absent or morning == "旷工" or afternoon == "旷工":
            summary["absent"] += 1
        if "缺卡" in morning or "缺卡" in afternoon or morning == "待确认" or afternoon == "待确认":
            summary["missing"] += 1
        if morning in ["公休", "病假", "事假", "事假两小时"] or afternoon in ["公休", "病假", "事假", "事假两小时"]:
            summary["leave"] += 1
    return summary


def pick_standard_value(values):
    nums = [round(float(v or 0), 2) for v in values if float(v or 0) > 0]
    if not nums:
        return 0
    counts = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    max_count = max(counts.values())
    common_values = [value for value, count in counts.items() if count == max_count]
    if max_count > 1 or len(common_values) == 1:
        return common_values[0]
    nums.sort()
    mid = len(nums) // 2
    if len(nums) % 2:
        return nums[mid]
    return round((nums[mid - 1] + nums[mid]) / 2, 2)


def pick_standard_max(values):
    nums = [round(float(v or 0), 2) for v in values if float(v or 0) > 0]
    return max(nums) if nums else 0


def parse_time_to_hour(time_str):
    clean = time_str.replace('次日', '').strip()
    try:
        return int(clean.split(':')[0])
    except:
        return 0
