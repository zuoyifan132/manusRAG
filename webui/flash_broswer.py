"""
@File   : flash_browser.py
@Time   : 2025/04/15 16:19
@Author : Wind.FlashC
@Desc   : None
"""

import os
import sys
sys.path.append("..")

import json
import time
from datetime import datetime
import streamlit as st
from components.sidebar import FlashSidebar
from components.faq import truncate_markdown_table
from core.api_deepseek import LLMCaller
from core.flash_agent import FlashAgentPlanner
# from core.flash_rag import flash_rag_pipeline
from utils.tool_util import TOOLS, TOOLS_DESC


# Streamlit UI
# 设置initial_sidebar_state 为 "collapsed"，默认折叠侧边栏提高初始加载速度
st.set_page_config(page_title="Flash-Browser", page_icon="⚡", layout="wide")
st.title("⚡ Flash-Browser")
st.caption("🚀 Powered by FlashC Group")

# >>> 侧边栏设置
Flashsidebar = FlashSidebar()
Flashsidebar.sidebar()

# >>> 聊天窗口设置
uploaded_file = st.file_uploader(
    label="Upload a pdf, docx, or txt file",
    type=["pdf", "docx", "txt"],
    help="Scanned documents are not supported yet!",
    label_visibility="collapsed"
)
if uploaded_file:
    # 激活文档解析模式
    try:
        file = flash_rag_pipeline(uploaded_file)
    except:
        pass

with st.expander("高级功能"):
    agent_flag = st.checkbox("Flash Agent Mode")
    max_iterations = st.number_input(
        label="Max Iterations",
        min_value=1, max_value=15, value=15,
        help="设置 Agent 最大迭代次数"
    )

# >>> 公共参数提取
system_prompt = Flashsidebar.system_prompt
selected_model = Flashsidebar.selected_model
temperature = Flashsidebar.temperature
max_tokens = Flashsidebar.max_tokens


@st.cache_resource
def get_model_caller(model_name):
    return LLMCaller(api_key="", model=model_name)


@st.cache_resource
def get_flash_agent_planner():
    """"""
    return FlashAgentPlanner()


caller = get_model_caller(selected_model)
flash_agent_planner = get_flash_agent_planner()


def stream(text: str, delay: float = 0.01):
    for char in text:
        yield char
        time.sleep(delay)


def flash_agent_workflow(question: str):
    """"""
    if not question:
        return

    num_iteration = 0   # 用于记录Agent规划迭代次数
    is_cmd_exist = True  # 用于记录当前是否存在工具调用
    resp = {"content": "", "cmdInfo": []}   # 用于记录最终答案

    # 初始化会话历史记录
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []

    #
    body = {
        "appName": "admin",
        "userId": "0",
        "sessionId": "0",
        "token": "0",
        "current": {
            "user": {
                "query": "",
                "info": {
                    "model": "DeepSeek-V3",
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "toolDesc": TOOLS_DESC,
                }
            },
            "response": []
        },
        "history": st.session_state.agent_history.copy()
    }

    # 问题
    body["current"]["user"]["query"] = question

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("human"):
        st.write(question)

    # Agent 规划
    chat_content = ""
    with st.chat_message("ai"):

        content = f"🤖 正在规划中 ..."
        chat_content += content
        st.write_stream(stream(content))

        while is_cmd_exist and num_iteration < max_iterations:
            # 执行agent规划服务
            resp = flash_agent_planner.plan(body)
            # 更新是否存在工具调用信号
            is_cmd_exist = bool(len(resp["cmdInfo"]) > 0)
            content = resp["content"]
            chat_content += content
            

            if is_cmd_exist:
                st.write_stream(stream(content)) 
                # 提取工具调用信息
                tool_names = [cmd_info["name"] for cmd_info in resp["cmdInfo"]]
                cmd_info_list = [{"name": cmd_info["name"], "args": cmd_info["args"]} for cmd_info in resp["cmdInfo"]]

                content = f"🔧 调用工具: {'、'.join(tool_names)}"
                chat_content += content
                st.write_stream(stream(content))
                content = f"🔧 调用参数: {json.dumps(cmd_info_list, indent=4, ensure_ascii=False)}"
                chat_content += content
                st.write_stream(stream(content))

                # 执行工具调用
                for idx, cmd_info in enumerate(cmd_info_list):
                    tool_name, tool_args = cmd_info["name"], cmd_info["args"]
                    try:
                        tool_res = TOOLS[tool_name](**tool_args)
                        content = f"✅ 工具调用成功"
                        chat_content += content
                        st.write_stream(stream(content))

                        # 在UI中使用折叠区域显示完整结果
                        with st.expander(f"查看工具 '{tool_name}' 返回结果", expanded=False):
                            st.markdown(tool_res)
                        
                        # 为chat_content添加可能截断的结果
                        is_table, truncated_res = truncate_markdown_table(tool_res, head_rows=15, tail_rows=5, truncation_message='... 表格中间行已省略，这里不做完整展示 ...')
                        if is_table and truncated_res != tool_res:
                            content = f"Observation: {truncated_res}"
                        else:
                            content = f"Observation: {tool_res}"
                        chat_content += content


                    except Exception as exc:
                        tool_res = "工具执行失败"
                        content = f"\n❌ 工具执行失败: {str(exc)}"
                        chat_content += content
                        st.write(content)
                    # 更新工具调用结果
                    resp["cmdInfo"][idx]["res"] = tool_res

            # 更新用户输入，准备下一轮规划
            body["current"]["response"].append(resp)

            # 更新Agent规划迭代次数
            num_iteration += 1

        if num_iteration >= max_iterations:
            content = "-" * 3
            chat_content += content
            st.write(content)
            content = f"❗❗ 达到最大迭代次数!"
            chat_content += content
            st.write_stream(stream(content))
            body["current"]["response"].append({"content": "达到最大迭代次数！强制进行总结！", "cmdInfo": []})
            resp = flash_agent_planner.plan(body)

        content = "-" * 3
        chat_content += content
        st.write(content)

        content = resp["content"]
        chat_content += content
        st.write_stream(stream(content))

        content = "-" * 3
        chat_content += content
        st.write(content)

    # 将完整响应添加到会话历史
    st.session_state.messages.append({"role": "assistant", "content": chat_content})
    
    current_copy = body['current'].copy()
    body['history'].append(current_copy)
    st.session_state.agent_history = body['history']  # 更新session_state中的历史


def flash_llm_chat(question: str):
    """"""
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    # 创建占位符用于流式输出
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # 调用流式生成函数并流式显示结果
        try:
            # 流式生成并显示
            caller.model = selected_model
            for response_chunk in caller.chat_stream(
                messages=st.session_state.messages,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                full_response += response_chunk
                message_placeholder.markdown(full_response + "▌")  # 模拟光标

            # 完成后显示完整响应
            message_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"生成回答时出错: {str(e)}")
            full_response = f"很抱歉，生成回答时出现错误: {str(e)}"
            message_placeholder.markdown(full_response)

    # 将完整响应添加到会话历史
    st.session_state.messages.append({"role": "assistant", "content": full_response})


# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": system_prompt}]

# 显示历史消息
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


# 用户输入
if question := st.chat_input("输入您的问题..."):
    # 添加用户消息到历史
    if not agent_flag:
        flash_llm_chat(question)
    else:
        flash_agent_workflow(question)
