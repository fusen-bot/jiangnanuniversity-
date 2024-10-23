import os
from datetime import datetime
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

class SparkChatBot:
    def __init__(self):
        # 配置参数
        self.SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
        self.SPARKAI_APP_ID = 'e3557ce1'
        self.SPARKAI_API_SECRET = 'YTBlNTg3YTY2ZGE2M2ZiNDRiOGYzZDVh'
        self.SPARKAI_API_KEY = '8b0e84adca1de90625c2529506e003da'
        self.SPARKAI_DOMAIN = 'generalv3.5'
        
        # 初始化对话历史
        self.conversation_history = []
        
        # 初始化客户端
        self.spark = ChatSparkLLM(
            spark_api_url=self.SPARKAI_URL,
            spark_app_id=self.SPARKAI_APP_ID,
            spark_api_key=self.SPARKAI_API_KEY,
            spark_api_secret=self.SPARKAI_API_SECRET,
            spark_llm_domain=self.SPARKAI_DOMAIN,
            streaming=True
        )
    
    def add_to_history(self, role, content):
        """添加消息到对话历史"""
        self.conversation_history.append(ChatMessage(role=role, content=content))
        
    def save_conversation(self):
        """保存对话历史到文件"""
        if not os.path.exists('chat_logs'):
            os.makedirs('chat_logs')
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'chat_logs/conversation_{timestamp}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in self.conversation_history:
                f.write(f"{msg.role}: {msg.content}\n")
        
        return filename
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        print("\n对话历史已清空!")
    
    def chat(self, user_input):
        """处理用户输入并返回响应"""
        print(f"SparkChatBot 收到用户输入: {user_input}")
        self.add_to_history("user", user_input)
        
        try:
            print("开始生成响应...")
            response_chunks = []
            for chunk in self.spark.generate(
                [self.conversation_history],
                streaming=True
            ):
                if isinstance(chunk, tuple) and chunk[0] == 'generations':
                    content = chunk[1][0][0].text
                    response_chunks.append(content)
                    print(f"收到响应片段: {content}")
            
            full_response = ''.join(response_chunks)
            print(f"完整响应: {full_response}")
            self.add_to_history("assistant", full_response)
            return full_response
        except Exception as e:
            error_message = f"错误: {str(e)}"
            print(f"SparkChatBot 发生错误: {error_message}")
            return error_message

def main():
    try:
        chatbot = SparkChatBot()
        chatbot.chat()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断。再见!")
    except Exception as e:
        print(f"\n程序发生错误: {str(e)}")

if __name__ == "__main__":
    main()
