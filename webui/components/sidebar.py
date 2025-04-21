import glob
import os
from pathlib import Path

import streamlit as st

from components.faq import clear_chat_history, faq, get_pdf_download_link

ABS_PATH = Path(__file__).absolute()
PROJECT_PATH = ABS_PATH.parent.parent


class FlashSidebar:

    def __init__(self) -> None:
        self.available_models = ["deepseek-chat", "gpt-4o-mini", "gpt-4o"]
        self.selected_model = "deepseek-chat"
        self.abs_path = os.path.dirname(os.path.abspath(__file__))
        self.fkey = ""
        self.database_folder = PROJECT_PATH / "databases"
        self.articles_l = [path.split("databases")[-1].replace("\\", "")
                           for path in glob.glob(f"{self.database_folder}/*.pdf")]

        # 初始化session state用于存储下载链接
        if "download_links" not in st.session_state:
            st.session_state.download_links = {}

    def sidebar(self):
        # >>> 侧边栏设置
        with st.sidebar:

            if st.button("清除历史", key="clear_history"):
                clear_chat_history()

            self.fkey = st.text_input("FKey", key="flashc_api_key", type="password")

            # Model selection
            self.selected_model = st.selectbox("Select Model", self.available_models, index=0)

            # 多选下拉列表
            selected_articles = st.multiselect(
                "选择要下载的文章",
                options=self.articles_l
            )
            # 只有选择了文章并点击按钮时才生成下载链接
            if st.button("Download", key=self.articles_l) and selected_articles:
                st.markdown("#### 下载链接")
                for title in selected_articles:
                    file_path = PROJECT_PATH / "databases" / title
                    # 避免使用缓存，只在按钮点击时生成
                    download_link = get_pdf_download_link(file_path, title)
                    st.markdown(download_link, unsafe_allow_html=True)

            self.system_prompt = st.text_area(
                "System Prompt",
                value="You are a helpful assistant.",
                height=68,  # 最低68
                help="设置AI助手的角色和任务"
            )

            self.temperature = st.slider(
                "Temperature",
                min_value=0.0, max_value=1.0, value=0.4, step=0.1,
                help="控制生成文本的随机性，值越高随机性越大"
            )

            self.max_tokens = st.number_input(
                "Max Tokens",
                min_value=1, max_value=64000, value=16384,
                help="设置生成文本的最大长度"
            )


class RagSidebar:
    """用于Flash RAG页面的侧边栏"""
    
    def __init__(self) -> None:
        self.available_models = ["Default Model", "GPT-3.5", "GPT-4"]
        self.selected_model = "Default Model"
        self.temperature = 0.7
        self.system_prompt = "你是一个知识库助手，根据检索到的内容回答问题。"
    
    def sidebar(self):
        """渲染侧边栏内容"""
        with st.sidebar:
            st.title("⚙️ 控制面板")
            
            # 清除历史按钮
            if st.button("🗑️ 清除历史", use_container_width=True, key="rag_clear_history"):
                # 使用专门为RAG设计的清除历史函数
                self.clear_rag_history()
            
            st.markdown("---")
            
            # 模型选择
            st.subheader("模型设置")
            self.selected_model = st.selectbox("选择模型", self.available_models, index=0)
            
            # 温度滑块
            self.temperature = st.slider("Temperature", 
                                      min_value=0.0, 
                                      max_value=1.0, 
                                      value=0.7, 
                                      step=0.1,
                                      help="控制生成文本的随机性，值越高随机性越大")
            
            # 系统提示词
            st.subheader("系统提示词")
            self.system_prompt = st.text_area("System Prompt", 
                                           value=self.system_prompt,
                                           height=100)
            
            st.markdown("---")
            st.caption("Flash RAG v1.0")
    
    def clear_rag_history(self):
        """清除RAG相关的会话状态"""
        st.session_state.rag_messages = []
        st.session_state.rag_retrieval_results = []
        st.session_state.rag_processing_query = False
        st.rerun()


