"""LLM-powered auto-reply service for live streaming"""
import os
import json
import time
import asyncio
from typing import Optional, List, Dict
from openai import OpenAI


class AutoReplyService:
    """Auto-reply service using LLM (通义千问/OpenAI)"""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus"
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = base_url
        self.model = model
        
        if not self.api_key:
            raise ValueError("API key is required. Set DASHSCOPE_API_KEY env var.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        self.system_prompt = """你是一个直播带货助手。你的任务是：
1. 回答观众关于商品的问题
2. 与观众友好互动
3. 回复简洁、自然、有温度
4. 不要暴露你是AI助手

商品信息：
- 商品1: SNACK 1, 价格 $9.9
- 商品2: SNACK 2, 价格 $19.9

回复规则：
- 用中文回复
- 每次回复不超过50字
- 保持热情和专业的态度"""
        
        self.conversation_history: List[Dict] = []
        self.max_history = 20
    
    def ask(
        self,
        question: str,
        context: str = ""
    ) -> str:
        """Ask LLM a question and get reply"""
        try:
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add context if provided
            if context:
                messages.append({"role": "system", "content": f"当前直播上下文: {context}"})
            
            # Add conversation history
            messages.extend(self.conversation_history[-self.max_history:])
            
            # Add current question
            messages.append({"role": "user", "content": question})
            
            # Call API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.8
            )
            
            reply = response.choices[0].message.content.strip()
            
            # Update history
            self.conversation_history.append({"role": "user", "content": question})
            self.conversation_history.append({"role": "assistant", "content": reply})
            
            return reply
            
        except Exception as e:
            print(f"LLM Error: {e}")
            return "感谢您的留言！"
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("Conversation history cleared")


# Quick test
if __name__ == "__main__":
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("Error: Please set DASHSCOPE_API_KEY environment variable")
        print("Usage: export DASHSCOPE_API_KEY='your-api-key'")
        exit(1)
    
    service = AutoReplyService(api_key=api_key)
    
    # Test questions
    test_questions = [
        "这个多少钱？",
        "有什么优惠吗？",
        "质量怎么样？",
        "发什么快递？",
    ]
    
    print("=== LLM Auto-Reply Test ===\n")
    for q in test_questions:
        print(f"Q: {q}")
        reply = service.ask(q)
        print(f"A: {reply}\n")
        time.sleep(0.5)
