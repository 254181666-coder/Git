
#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")

for store in ['晨宇']:
    for platform in ['美团']:
        file_path = GROUP_BUY_DIR / f"{store}{platform}.xlsx"
        if file_path.exists():
            df = pd.read_excel(file_path)
            print(f"\n=== {store}{platform} ===")
            print(f"列: {df.columns}")
            print(f"\n前3行:")
            print(df.head(3))
            
            if '消费金额' in df.columns:
                print(f"\n消费金额样例:")
                print(df['消费金额'].head(10).tolist())
