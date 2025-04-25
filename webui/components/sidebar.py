import glob
import os
from pathlib import Path
import datetime
import json

import streamlit as st

from components.faq import clear_chat_history, faq, get_pdf_download_link

ABS_PATH = Path(__file__).absolute()
PROJECT_PATH = ABS_PATH.parent.parent


class FlashSidebar:

    def __init__(self) -> None:
        self.available_models = ["deepseek-chat", "gpt-4o-mini", "gpt-4o"]
        self.selected_model = "gpt-4o-mini"
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

            # Model selection
            self.selected_model = st.selectbox("Select Model", self.available_models, index=1)

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
        # 初始化历史记录
        if "chat_history_sessions" not in st.session_state:
            st.session_state.chat_history_sessions = []
        # 初始化当前会话ID
        if "current_session_id" not in st.session_state:
            st.session_state.current_session_id = None
    
    def sidebar(self):
        """渲染侧边栏内容"""
        with st.sidebar:
            st.title("⚙️ 控制面板")
            
            # 将清除历史按钮改为新对话按钮
            if st.button("🆕 新建对话", use_container_width=True, key="rag_new_chat"):
                # 保存当前对话，然后创建新对话
                self.new_chat()
            
            st.markdown("---")
            
            # 添加历史记录区域
            st.subheader("💬 历史对话")
            
            # 如果没有历史记录，显示提示信息
            if not st.session_state.chat_history_sessions:
                st.info("暂无历史对话记录")
            else:
                # 显示历史会话列表，按时间倒序排列
                for idx, session in enumerate(reversed(st.session_state.chat_history_sessions)):
                    session_time = session.get("timestamp", "未知时间")
                    formatted_time = session_time
                    if isinstance(session_time, datetime.datetime):
                        formatted_time = session_time.strftime("%Y-%m-%d %H:%M")
                    
                    # 获取会话的第一个问题作为标题
                    first_question = "未知问题"
                    if session.get("messages") and len(session["messages"]) > 0:
                        for msg in session["messages"]:
                            if msg["role"] == "user":
                                first_question = msg["content"]
                                # 截断过长的问题
                                if len(first_question) > 25:
                                    first_question = first_question[:22] + "..."
                                break
                    
                    # 创建一个可点击的按钮，用于还原到该对话
                    if st.button(
                        f"{first_question}\n📅 {formatted_time}",
                        key=f"history_session_{idx}",
                        use_container_width=True
                    ):
                        self.restore_session(session)
            
            st.markdown("---")
            st.caption("Flash RAG v1.0")
    
    def clear_rag_history(self):
        """清除RAG相关的会话状态"""
        # 保存当前会话到历史记录
        self.save_current_session()
        
        # 清除当前会话状态
        st.session_state.rag_messages = []
        st.session_state.rag_retrieval_results = []
        st.session_state.rag_processing_query = False
        st.rerun()
    
    def save_current_session(self):
        """保存当前会话到历史记录"""
        # 如果当前没有对话内容，不保存
        if not st.session_state.get("rag_messages") or len(st.session_state.rag_messages) == 0:
            return
        
        # 获取当前会话的唯一标识
        current_session_id = self._get_session_identifier(st.session_state.rag_messages)
        
        # 检查是否需要更新现有会话而不是创建新会话
        if "chat_history_sessions" in st.session_state:
            for idx, session in enumerate(st.session_state.chat_history_sessions):
                session_id = self._get_session_identifier(session.get("messages", []))
                if session_id == current_session_id:
                    # 更新现有会话
                    st.session_state.chat_history_sessions[idx]["messages"] = st.session_state.rag_messages.copy()
                    st.session_state.chat_history_sessions[idx]["retrieval_results"] = st.session_state.rag_retrieval_results.copy() if st.session_state.get("rag_retrieval_results") else []
                    return
        
        # 创建新会话记录
        session = {
            "timestamp": datetime.datetime.now(),
            "messages": st.session_state.rag_messages.copy(),
            "retrieval_results": st.session_state.rag_retrieval_results.copy() if st.session_state.get("rag_retrieval_results") else [],
            "session_id": current_session_id  # 添加会话ID
        }
        
        # 添加到历史记录
        if "chat_history_sessions" not in st.session_state:
            st.session_state.chat_history_sessions = []
        
        # 限制历史记录数量，最多保存20条
        if len(st.session_state.chat_history_sessions) >= 20:
            st.session_state.chat_history_sessions.pop(0)
        
        st.session_state.chat_history_sessions.append(session)
    
    def restore_session(self, session):
        """还原到指定的历史会话"""
        # 保存当前会话到历史记录前先检查是否需要保存
        current_messages = st.session_state.get("rag_messages", [])
        if current_messages and len(current_messages) > 0:
            # 先生成当前会话的唯一标识
            current_session_id = self._get_session_identifier(current_messages)
            target_session_id = self._get_session_identifier(session.get("messages", []))
            
            # 检查是否点击了与当前会话相同的会话
            if current_session_id == target_session_id:
                # 如果点击的就是当前会话，不需要任何操作
                return
                
            # 检查当前会话是否已经存在于历史记录中
            is_already_saved = False
            for existing_session in st.session_state.get("chat_history_sessions", []):
                if id(existing_session) == id(session):  # 跳过正要切换到的会话（使用id比较引用）
                    continue
                
                existing_session_id = self._get_session_identifier(existing_session.get("messages", []))
                if current_session_id == existing_session_id:
                    is_already_saved = True
                    break
            
            # 只有在当前会话尚未保存的情况下才保存
            if not is_already_saved:
                self.save_current_session()
        
        # 恢复历史会话
        st.session_state.rag_messages = session.get("messages", []).copy()
        st.session_state.rag_retrieval_results = session.get("retrieval_results", []).copy()
        st.session_state.rag_processing_query = False
        # 设置当前会话ID
        st.session_state.current_session_id = self._get_session_identifier(session.get("messages", []))
        
        # 刷新界面
        st.rerun()
    
    def _get_session_identifier(self, messages):
        """生成会话的唯一标识，用于比较两个会话是否相同"""
        if not messages:
            return ""
        
        # 只使用第一个用户问题作为会话标识
        first_user_message = None
        for msg in messages:
            if msg.get("role") == "user":
                first_user_message = msg
                break
        
        # 如果找到第一个用户问题，使用它作为标识符
        if first_user_message:
            return f"user:{first_user_message.get('content', '')}"
        
        # 如果没有用户消息，使用所有消息作为备选方案（兼容旧逻辑）
        message_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            message_parts.append(f"{role}:{content}")
        
        return "|".join(message_parts)

    def new_chat(self):
        """创建新对话，保存当前对话到历史记录"""
        # 检查当前会话是否已经被保存过
        current_messages = st.session_state.get("rag_messages", [])
        if current_messages and len(current_messages) > 0:
            # 生成当前会话的唯一标识
            current_session_id = self._get_session_identifier(current_messages)
            
            # 检查是否已存在于历史记录中
            is_already_saved = False
            for session in st.session_state.get("chat_history_sessions", []):
                session_id = self._get_session_identifier(session.get("messages", []))
                if session_id == current_session_id:
                    is_already_saved = True
                    break
            
            # 如果尚未保存，则保存当前会话
            if not is_already_saved:
                self.save_current_session()
        
        # 清除当前会话状态以开始新对话
        st.session_state.rag_messages = []
        st.session_state.rag_retrieval_results = []
        st.session_state.rag_processing_query = False
        st.session_state.current_session_id = None
        st.rerun()


