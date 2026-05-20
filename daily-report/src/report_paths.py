"""
日报标准产物路径。
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.config import OUTPUT_DIR, PROJECT_ROOT

OUTPUT_PDF_DIR = PROJECT_ROOT / "data" / "output_pdf"


@dataclass(frozen=True)
class ReportArtifact:
    label: str
    path: Path
    required: bool = True


def daily_report_artifacts(target_date: str) -> List[ReportArtifact]:
    return [
        ReportArtifact("储值率分析图", OUTPUT_DIR / f"{target_date}储值率分析图.png"),
        ReportArtifact("收入分析综合图", OUTPUT_DIR / f"收入分析综合图_{target_date}.png"),
        ReportArtifact("商品销售分析报告", OUTPUT_PDF_DIR / f"商品销售分析报告_{target_date}.pdf"),
        ReportArtifact("同比对比分析报告", OUTPUT_PDF_DIR / f"同比对比分析报告_{target_date}.pdf"),
    ]


def daily_report_files(target_date: str) -> List[Path]:
    return [artifact.path for artifact in daily_report_artifacts(target_date)]
