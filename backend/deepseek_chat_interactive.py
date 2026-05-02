import os
from datetime import datetime
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()


class DeepSeekChatBot:
    def __init__(self):
        self.API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

        if not self.API_KEY:
            raise ValueError("缺少 DeepSeek API 凭证，请配置 .env 文件")

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.API_KEY,
            base_url=self.BASE_URL
        )
        
        # 初始化对话历史
        self.conversation_history = []
        
    def add_to_history(self, role, content):
        """添加消息到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
    def save_conversation(self):
        """保存对话历史到文件"""
        if not os.path.exists('chat_logs'):
            os.makedirs('chat_logs')
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'chat_logs/deepseek_conversation_{timestamp}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in self.conversation_history:
                f.write(f"{msg['role']}: {msg['content']}\n")
        
        return filename
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        print("\n对话历史已清空!")
    
    def chat(self, user_input):
        """处理用户输入并返回响应"""
        print(f"DeepSeek 收到用户输入: {user_input}")
        
        try:
            # 准备消息列表
            messages = [
                {"role": "system", "content": "你是一个有帮助的助手。"},
                *self.conversation_history,
                {"role": "user", "content": user_input}
            ]
            
            # 调用 DeepSeek API
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            
            # 获取响应内容
            assistant_response = response.choices[0].message.content
            
            # 更新对话历史
            self.add_to_history("user", user_input)
            self.add_to_history("assistant", assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_message = f"错误: {str(e)}"
            print(f"DeepSeek 发生错误: {error_message}")
            return error_message 