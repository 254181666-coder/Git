"""
快速验证脚本 - 验证通义千问API和FFmpeg是否可用
运行: python3 scripts/quick_verify.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def verify_openai():
    """验证通义千问API"""
    print("\n=== 验证 通义千问API ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 未配置 OPENAI_API_KEY")
        print("请在 backend/.env 中配置")
        return False
        
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        
        print("正在测试API调用...")
        # 使用通义千问模型
        response = client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是专业的直播带货主播"},
                {"role": "user", "content": "介绍一下这款产品的优势"}
            ],
            max_tokens=100
        )
        
        print(f"✅ 通义千问API 正常")
        print(f"测试回复: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ 通义千问API 失败: {str(e)}")
        return False

def verify_ffmpeg():
    """验证FFmpeg是否安装"""
    print("\n=== 验证 FFmpeg ===")
    
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ FFmpeg 已安装")
            print(f"版本: {result.stdout.split()[2]}")
            return True
        else:
            print("❌ FFmpeg 未安装")
            print("安装命令: brew install ffmpeg (Mac)")
            return False
            
    except FileNotFoundError:
        print("❌ FFmpeg 未安装")
        print("安装命令: brew install ffmpeg (Mac)")
        return False
    except Exception as e:
        print(f"❌ FFmpeg 验证失败: {str(e)}")
        return False

def verify_backend():
    """验证后端服务"""
    print("\n=== 验证后端服务 ===")
    
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            print("✅ 后端服务运行正常")
            return True
        else:
            print("❌ 后端服务异常")
            return False
    except:
        print("❌ 后端服务未启动")
        print("启动命令: cd backend && python3 main.py")
        return False

if __name__ == "__main__":
    print("\n🔍 播助手 Pro - 技术验证")
    print("=" * 50)
    
    results = {
        "通义千问API": verify_openai(),
        "FFmpeg": verify_ffmpeg(),
        "后端服务": verify_backend()
    }
    
    print("\n" + "=" * 50)
    print("验证结果汇总:")
    for name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name}: {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n通过: {passed}/{total}")
    
    if passed >= 2:
        print("\n🎉 基础验证通过，可以开始测试推流功能")
    else:
        print("\n⚠️ 请先修复失败的项目再验证")