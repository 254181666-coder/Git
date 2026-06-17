import openai
import os
from dotenv import load_dotenv

load_dotenv()

class ChatBot:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL')
        )
        self.product_info = ""
        self.conversation_history = []

    def set_product_info(self, info):
        self.product_info = info

    def chat(self, user_message):
        system_prompt = f"""你是一个专业的直播带货主播。请根据以下商品信息回答观众问题：

商品信息：
{self.product_info}

要求：
1. 回答要热情、专业
2. 重点突出商品优势
3. 保持口语化，适合直播场景"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        return assistant_message
