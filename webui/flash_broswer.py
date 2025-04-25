"""
@File   : flash_browser.py
@Time   : 2025/04/15 16:19
@Author : Wind.FlashC
@Desc   : None
"""

import sys
sys.path.append("..")

import json
import time
from datetime import datetime
import streamlit as st
from components.sidebar import FlashSidebar
from components.faq import truncate_markdown_table
from core.api_deepseek import LLMCaller
# from core.flash_agent import FlashAgentPlanner
from utils.tool_util import TOOLS, TOOLS_DESC
from manus.manus_deep_search_agent import DeepSearch
from manus.llm import OpenAILLM
from utils.aigc_api import openai_stream_generate
from openai import OpenAI
from services.config import OPENAI_API_KEY
from collections import defaultdict
import threading
import io
import queue
from contextlib import redirect_stdout


# Streamlit UI
# 设置initial_sidebar_state 为 "collapsed"，默认折叠侧边栏提高初始加载速度
st.set_page_config(page_title="ManusRAG", page_icon="⚡", layout="wide")
st.title("⚡ ManusRAG")
st.caption("🚀 Powered by Evan ZUO")

# >>> 侧边栏设置
Flashsidebar = FlashSidebar()
Flashsidebar.sidebar()

with st.expander("高级功能"):
    deep_search_flag = st.checkbox("DeepSearch Mode")
    max_iterations = st.number_input(
        label="Max Iterations",
        min_value=1, max_value=15, value=3,
        help="设置 DeepSearch 最大迭代次数"
    )

# >>> 公共参数提取
system_prompt = Flashsidebar.system_prompt
selected_model = Flashsidebar.selected_model
temperature = Flashsidebar.temperature
max_tokens = Flashsidebar.max_tokens


@st.cache_resource
def get_model_caller(model_name):
    return LLMCaller(api_key="", model=model_name)


@st.cache_resource(show_spinner=False)
def get_deep_search_agent(model_name, max_iter):
    """获取DeepSearch代理，使用指定的模型和最大迭代次数"""
    llm = OpenAILLM(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return DeepSearch(llm=llm, max_iter=max_iter)


caller = get_model_caller(selected_model)
# deep_search_agent的实例化会在调用时进行，以确保使用最新的参数


def stream(text: str, delay: float = 0.01):
    for char in text:
        yield char
        time.sleep(delay)


def format_retrieved_docs(retrieved_docs):
    """格式化检索到的文档，按文档分组并排序"""
    if not retrieved_docs:
        return []
    
    # 将检索结果转换为更易于处理的格式
    formatted_results = []
    for i, doc in enumerate(retrieved_docs):
        formatted_results.append({
            "文档": f"文档 #{i+1}",
            "内容": doc,
            "相关度": 1.0  # 由于没有相关度信息，默认设为1.0
        })
    
    # 按文档分组
    grouped_results = defaultdict(list)
    for result in formatted_results:
        grouped_results[result["文档"]].append(result)
    
    # 返回分组后的结果
    return grouped_results


class ThreadSafeStringIO(io.StringIO):
    """线程安全的StringIO，用于在多线程环境中捕获输出"""
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        self.output_queue = queue.Queue()
    
    def write(self, s):
        with self.lock:
            result = super().write(s)
            if s.strip():  # 只加入非空白字符
                # 确保每个输出都有换行符
                if not s.endswith('\n'):
                    s = s + '\n'
                self.output_queue.put(s)
            return result


def flash_deep_search_workflow(question: str):
    """DeepSearch工作流，实时流式显示DeepSearch的查询过程"""
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("human"):
        st.write(question)

    # 创建用于流式输出的聊天消息
    with st.chat_message("ai"):
        # 创建一个用于显示状态的占位符
        status_placeholder = st.empty()
        # 创建一个用于显示过程的占位符
        process_placeholder = st.empty()
        # 创建一个用于显示最终答案的占位符
        message_placeholder = st.empty()
        # 创建一个用于显示召回结果的占位符
        retrieval_placeholder = st.empty()
        
        # 显示初始状态
        status_placeholder.write("🔍 正在深度搜索中...")
        process_content = ""
        
        # 创建线程安全的StringIO用于捕获输出
        output_stream = ThreadSafeStringIO()
        
        # 获取DeepSearch实例
        deep_search_agent = get_deep_search_agent(selected_model, max_iterations)
        
        # 存储最终结果的变量
        final_results = {"answer": "", "docs": []}
        
        # 定义执行查询的函数
        def run_query():
            with redirect_stdout(output_stream):
                final_answer, retrieved_docs = deep_search_agent.query(query=question)
                final_results["answer"] = final_answer
                final_results["docs"] = retrieved_docs
        
        # 在后台线程中执行查询
        query_thread = threading.Thread(target=run_query)
        query_thread.start()
        
        # 显示过程中的输出
        try:
            # 显示正在处理的消息
            process_content += f"使用模型: {selected_model}, 最大迭代次数: {max_iterations}\n\n"
            process_placeholder.code(process_content)
            
            # 不断从队列中获取输出并显示
            while query_thread.is_alive() or not output_stream.output_queue.empty():
                try:
                    new_output = output_stream.output_queue.get(block=True, timeout=0.1)
                    process_content += new_output
                    process_placeholder.code(process_content)
                except queue.Empty:
                    pass
                
                # 给UI一些时间来更新
                time.sleep(0.01)
            
            # 显示过程完成
            process_content += "\n处理完成！\n"
            process_placeholder.code(process_content)
            
            # 等待线程完成
            query_thread.join()
            
            # 更新状态
            status_placeholder.write("🔍 检索完成！正在生成最终答案...")
            
            # 添加最终答案的分隔符
            process_content += "\n" + "=" * 40 + "\n✅ 最终答案:\n" + "=" * 40 + "\n\n"
            process_placeholder.code(process_content)
            
            # 流式显示最终答案
            response = ""
            for char in final_results["answer"]:
                response += char
                message_placeholder.markdown(response + "▌")  # 模拟光标
                time.sleep(0.005)  # 减少延迟，加快显示速度
            
            # 最终显示完整答案
            message_placeholder.markdown(response)
            
            # 更新状态
            status_placeholder.write("✅ 回答完成！可查看下方检索结果")
            
            # 格式化检索到的文档
            grouped_results = format_retrieved_docs(final_results["docs"])
            
            # 使用expander显示检索详细结果（放在答案下方）
            with retrieval_placeholder.container():
                with st.expander("📚 查看召回详细结果", expanded=False):
                    if grouped_results:
                        sorted_docs = list(grouped_results.keys())
                        for doc_idx, doc in enumerate(sorted_docs):
                            results_for_doc = grouped_results[doc]
                            st.markdown(f"### 📄 {doc}")
                            for i, result in enumerate(results_for_doc):
                                st.markdown(f"**片段 {i+1}**")
                                st.markdown(f"```\n{result['内容']}\n```")
                            if doc_idx < len(sorted_docs) - 1:
                                st.markdown("---")
                    else:
                        st.info("未检索到相关文档")
            
            # 将完整响应添加到会话历史
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            error_msg = f"处理中发生错误: {str(e)}"
            process_placeholder.error(error_msg)
            message_placeholder.error("生成回答失败，请重试")
            st.session_state.messages.append({"role": "assistant", "content": f"错误: {error_msg}"})


def flash_llm_chat(question: str):
    """普通对话模式，使用OpenAI API直接流式输出"""
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # 创建用于流式输出的聊天消息
    with st.chat_message("assistant"):
        # 创建消息历史
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加历史消息(最多保留5轮对话)
        history_messages = []
        for msg in st.session_state.messages[-10:]:  # 限制历史消息数量
            if msg["role"] != "system":  # 跳过系统消息
                history_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加历史消息
        messages.extend(history_messages)
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # 创建流式文本生成占位符
        placeholder = st.empty()
        full_response = ""
        
        try:
            # 直接使用OpenAI API进行流式生成
            stream = client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # 处理流式响应
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # 实时更新UI
                    placeholder.markdown(full_response + "▌")  # 模拟光标
            
            # 显示完整响应
            placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"生成回答时出错: {str(e)}")
            full_response = f"很抱歉，生成回答时出现错误: {str(e)}"
            placeholder.markdown(full_response)

    # 将完整响应添加到会话历史
    st.session_state.messages.append({"role": "assistant", "content": full_response})


# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": system_prompt}]

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# 用户输入
if question := st.chat_input("输入您的问题..."):
    # 添加用户消息到历史
    if deep_search_flag:
        flash_deep_search_workflow(question)
    else:
        flash_llm_chat(question)
