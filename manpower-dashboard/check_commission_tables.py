"""检查提成表数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

print("=== product_commission:")
pc_df = query("SELECT * FROM product_commission LIMIT 5")
print("列:", pc_df.columns.tolist())
print("\n前5条:", pc_df)

print("\n\n=== stored_commission:")
sc_df = query("SELECT * FROM stored_commission LIMIT 5")
print("列:", sc_df.columns.tolist())
print("\n前5条:", sc_df)

print("\n\n=== 检查各表有多少条:")
print("product_commission:", query("SELECT COUNT(*) as c FROM product_commission").iloc[0,0])
print("stored_commission:", query("SELECT COUNT(*) as c FROM stored_commission").iloc[0,0])
