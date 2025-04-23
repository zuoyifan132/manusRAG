from pathlib import Path
import streamlit as st
import pandas as pd
from core import flash_rag
from collections import defaultdict
import datetime
import time
import json
import os
import uuid
import tempfile
import shutil
from loguru import logger

from components.sidebar import RagSidebar

ABS_PATH = Path(__file__).absolute()
PROJECT_PATH = ABS_PATH.parent.parent.parent

# 创建临时文件夹
TEMP_DIR = os.path.join(PROJECT_PATH, "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

# 默认配置文件路径
DEFAULT_SEARCH_CONFIG = os.environ.get(
    "SEARCH_CONFIG_PATH", 
    rf"{PROJECT_PATH}/examples/search_example_config.json"
)
DEFAULT_INGEST_CONFIG = os.environ.get(
    "INGEST_CONFIG_PATH", 
    rf"{PROJECT_PATH}/examples/ingest_data_example_config.json"
)

# 页面配置
st.set_page_config(page_title="Flash RAG 知识库检索", page_icon="🔍", layout="wide")
st.title("🔍 Flash RAG 知识库检索系统")

# 添加JavaScript来保持滚动位置
js_code = """
<script>
// 存储当前滚动位置
function saveScrollPos() {
    sessionStorage.setItem('scrollPos', window.scrollY);
}

// 恢复滚动位置
function restoreScrollPos() {
    const pos = sessionStorage.getItem('scrollPos');
    if (pos) {
        window.scrollTo(0, parseInt(pos));
    }
}

// 页面加载时尝试恢复位置
document.addEventListener('DOMContentLoaded', function() {
    restoreScrollPos();
    
    // 监听所有按钮点击
    document.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', saveScrollPos);
    });
    
    // 监听复选框变化
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', saveScrollPos);
    });
});
</script>
"""

st.markdown(js_code, unsafe_allow_html=True)

# 初始化会话状态
if "rag_messages" not in st.session_state:
    st.session_state.rag_messages = []
if "rag_retrieval_results" not in st.session_state:
    st.session_state.rag_retrieval_results = []
if "rag_processing_query" not in st.session_state:
    st.session_state.rag_processing_query = False
if "use_config_file" not in st.session_state:
    st.session_state.use_config_file = False
if "temp_files" not in st.session_state:
    st.session_state.temp_files = []
if "target_files" not in st.session_state:
    st.session_state.target_files = []
if "file_status" not in st.session_state:
    st.session_state.file_status = {}
if "processing_files" not in st.session_state:
    st.session_state.processing_files = False
if "ui_update_counter" not in st.session_state:
    st.session_state.ui_update_counter = 0
if "milvus_status" not in st.session_state:
    st.session_state.milvus_status = None

# 初始化侧边栏
rag_sidebar = RagSidebar()
rag_sidebar.sidebar()

# 清除聊天历史函数
def clear_chat_history():
    rag_sidebar.clear_rag_history()

# 处理用户查询
def process_query(query):
    if query and not st.session_state.rag_processing_query:
        st.session_state.rag_processing_query = True
        st.session_state.rag_messages.append({"role": "user", "content": query})
        st.session_state.ui_update_counter += 1
        # 添加rerun调用来强制刷新页面，立即处理查询
        st.rerun()

# 实际处理文件列表
@st.cache_resource
def update_file_list(target_files, temp_files, file_status, uploaded_files):
    """
    处理并更新文件列表，使用缓存以避免重复计算
    
    参数:
    uploaded_files - 上传的文件列表
    
    返回:
    (temp_files, target_files, file_status) 元组，包含处理后的文件列表、目标文件和状态
    """
    if not uploaded_files:
        return temp_files, target_files, file_status
    
    existing_temp_files = temp_files
    existing_target_files = target_files
    existing_file_status = file_status
    
    # 获取现有文件名与上传文件名
    current_file_names = {f.name for f in uploaded_files}
    existing_file_names = {f["文件名"] for f in existing_temp_files}
    selected_file_names = {f["文件名"] for f in existing_target_files}

    # 保存已知文件的状态
    preserved_status = {name: status for name, status in existing_file_status.items() if name in current_file_names}
    
    # 创建上传文件的字典，用于快速查找
    uploaded_files_dict = {f.name: f for f in uploaded_files}
    
    # 合并文件列表
    new_temp_files = []
    
    # 先添加原有文件（不在上传文件中的文件）
    for file in existing_temp_files:
        if file["文件名"] not in current_file_names:
            new_temp_files.append(file)
    
    # 添加所有上传的文件
    for file_name, file in uploaded_files_dict.items():
        new_temp_files.append({
            "文件名": file_name,
            "类型": file.type,
            "大小": f"{round(file.size / 1024, 2)} KB",
            "状态": preserved_status.get(file_name, "等待处理"),
            "文件对象": file
        })
    
    # 更新目标文件列表，保留之前选择的文件
    new_target_files = [f for f in existing_target_files if f["文件名"] not in current_file_names]
    
    # 在普通模式下，只添加那些之前已经被选中的文件
    for file in new_temp_files:
        if file["文件名"] in current_file_names and file["文件名"] in selected_file_names:
            if not any(t["文件名"] == file["文件名"] for t in new_target_files):
                new_target_files.append(file)
    
    # 生成新的文件状态
    new_file_status = existing_file_status.copy()
    
    # 更新上传文件的状态
    for f in new_temp_files:
        new_file_status[f["文件名"]] = f["状态"]
    
    return new_temp_files, new_target_files, new_file_status

# 应用update_file_list的结果到session_state
def apply_file_list_update(uploaded_files, action=None, selected_files=None):
    """
    应用文件列表更新结果到session_state
    
    参数:
    uploaded_files - 上传的文件列表
    action - 要执行的操作: 'select_all', 'deselect_all', 'delete_selected'
    selected_files - 当action为'delete_selected'时，要删除的文件列表
    """
    # 获取当前缓存的文件列表
    target_files = st.session_state.target_files
    temp_files = st.session_state.temp_files
    file_status = st.session_state.file_status
    
    # 处理删除操作 - 直接从列表中移除文件
    if action == 'delete_selected' and selected_files:
        # 获取要删除的文件名
        selected_file_names = {f["文件名"] for f in selected_files}
        temp_files = [f for f in temp_files if f["文件名"] not in selected_file_names]
        target_files = [f for f in target_files if f["文件名"] not in selected_file_names]
        # 从file_status中移除已删除文件的状态
        for file_name in selected_file_names:
            if file_name in file_status:
                del file_status[file_name]
    
    # 当有上传文件时，更新文件列表
    if uploaded_files:
        # 如果是新文件上传，先更新文件列表
        new_temp_files, new_target_files, new_file_status = update_file_list(
            target_files, 
            temp_files, 
            file_status,
            uploaded_files
        )
        temp_files = new_temp_files
        target_files = new_target_files
        file_status = new_file_status
    
    # 根据action执行相应操作
    if action == 'select_all':
        target_files = temp_files.copy()
            
    elif action == 'deselect_all':
        # 清空目标文件列表
        target_files = []
            
    # 更新session_state
    st.session_state.temp_files = temp_files
    st.session_state.target_files = target_files
    st.session_state.file_status = file_status
    
    # 如果是删除操作，则增加ui_update_counter以触发UI更新
    if action == 'delete_selected':
        st.session_state.ui_update_counter += 1

# 全选函数
def select_all_files():
    # 先更新UI counter以刷新file_uploader
    st.session_state.ui_update_counter += 1
    # 直接应用全选操作，不需要获取当前uploaded_files
    apply_file_list_update([], action='select_all')

# 取消全选函数
def deselect_all_files():
    # 先更新UI counter以刷新file_uploader
    st.session_state.ui_update_counter += 1
    # 直接应用取消全选操作，不需要获取当前uploaded_files
    apply_file_list_update([], action='deselect_all')

# 删除所选文件函数
def delete_selected_files():
    # 先更新UI counter以刷新file_uploader
    st.session_state.ui_update_counter += 1
    # 直接应用删除操作，不需要获取当前uploaded_files
    apply_file_list_update(
        [], 
        action='delete_selected', 
        selected_files=st.session_state.target_files
    )

# 切换文件选择状态函数
def toggle_file_selection(file_name, is_selected):
    # 获取当前缓存的文件列表
    target_files = st.session_state.target_files
    temp_files = st.session_state.temp_files
    
    if is_selected:
        # 找到要选择的文件并添加到目标列表
        for file in temp_files:
            if file["文件名"] == file_name and not any(t["文件名"] == file_name for t in target_files):
                target_files.append(file.copy())
                break
    else:
        # 从目标文件列表中移除文件
        target_files = [f for f in target_files if f["文件名"] != file_name]
    
    # 更新状态
    st.session_state.target_files = target_files
    
    # 更新UI counter以刷新file_uploader
    st.session_state.ui_update_counter += 1

# 处理单个文件
def process_single_file(file_info, config_path):
    file = file_info["文件对象"]
    try:
        for idx, f in enumerate(st.session_state.temp_files):
            if f["文件名"] == file_info["文件名"]:
                st.session_state.temp_files[idx]["状态"] = "处理中..."
                st.session_state.file_status[file_info["文件名"]] = "处理中..."
                break
        st.session_state.ui_update_counter += 1
        temp_file_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{file.name}")
        with open(temp_file_path, "wb") as f:
            f.write(file.getbuffer())
        result = flash_rag.ingest_data(file_path=temp_file_path, config=config_path)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        status = "处理成功" if result.get("status") == "success" else f"处理失败: {result.get('message', '未知错误')}"
        for idx, f in enumerate(st.session_state.temp_files):
            if f["文件名"] == file_info["文件名"]:
                st.session_state.temp_files[idx]["状态"] = status
                st.session_state.file_status[file_info["文件名"]] = status
                break
        return result.get("status") == "success"
    except Exception as e:
        error_msg = f"处理出错: {str(e)}"
        for idx, f in enumerate(st.session_state.temp_files):
            if f["文件名"] == file_info["文件名"]:
                st.session_state.temp_files[idx]["状态"] = error_msg
                st.session_state.file_status[file_info["文件名"]] = error_msg
                break
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return False

# 主要功能区域
with st.container():
    st.subheader("📚 上传知识库文件")
    col1, col2 = st.columns([3, 2])
    with col1:
        use_config = st.checkbox("使用配置文件", value=st.session_state.use_config_file, help="选择后将使用配置文件进行处理，否则使用上传文件")
        st.session_state.use_config_file = use_config

        if use_config:
            ingest_config_path = st.text_input("知识库摄入配置路径", value=DEFAULT_INGEST_CONFIG, help="请输入处理文件的配置文件路径")
            st.markdown("**上传文件覆盖配置中的文档路径**")
            # 使用ui_update_counter作为key的一部分，以确保每次更新时重新创建file_uploader
            config_uploader_key = f"config_file_uploader_{st.session_state.ui_update_counter}"
            uploaded_config_files = st.file_uploader(
                "选择或拖拽文件到这里", 
                accept_multiple_files=True, 
                type=["pdf", "docx", "txt", "md", "csv", "json"], 
                help="上传的文件将覆盖配置中的doc_path", 
                key=config_uploader_key
            )
            # 如果有文件上传，则处理并立即增加counter以清空上传缓存
            if uploaded_config_files:
                apply_file_list_update(uploaded_config_files)
                st.session_state.ui_update_counter += 1
                st.rerun()
        else:
            # 使用ui_update_counter作为key的一部分，以确保每次更新时重新创建file_uploader
            regular_uploader_key = f"regular_file_uploader_{st.session_state.ui_update_counter}"
            uploaded_files = st.file_uploader(
                "选择或拖拽文件到这里", 
                accept_multiple_files=True, 
                type=["pdf", "docx", "txt", "md", "csv", "json"], 
                help="支持多种文件格式", 
                key=regular_uploader_key
            )
            # 如果有文件上传，则处理并立即增加counter以清空上传缓存
            if uploaded_files:
                apply_file_list_update(uploaded_files)
                st.session_state.ui_update_counter += 1
                st.rerun()

        if st.session_state.temp_files:
            st.markdown('<div id="file_list_anchor"></div>', unsafe_allow_html=True)
            st.markdown("### 文件列表")
            # 确保is_selected反映当前的选择状态
            is_selected = {f["文件名"]: any(t["文件名"] == f["文件名"] for t in st.session_state.target_files) for f in st.session_state.temp_files}
            
            df = pd.DataFrame([
                {"选择": is_selected[f["文件名"]], "文件名": f["文件名"], "类型": f["类型"], "大小": f["大小"], "状态": f["状态"]}
                for f in st.session_state.temp_files
            ])

            # 使用唯一的key以避免在状态变化时过度重新渲染
            @st.cache_data
            def get_key():
                st.session_state.ui_update_counter += 1
                return f"file_editor_{st.session_state.ui_update_counter}"
            edited_df = st.data_editor(
                df,
                column_config={
                    "选择": st.column_config.CheckboxColumn("选择", help="选择要处理的文件", default=False),
                    "状态": st.column_config.Column("状态", help="文件处理状态", disabled=True)
                },
                disabled=["文件名", "类型", "大小", "状态"],
                use_container_width=True,
                hide_index=True,
                key=get_key()
            )
            
            # 处理勾选状态变化
            for i, row in edited_df.iterrows():
                file_name = row["文件名"]
                is_selected = row["选择"]
                # 判断是否已经被选择
                current_selected = any(f["文件名"] == file_name for f in st.session_state.target_files)
                if current_selected != is_selected:
                    toggle_file_selection(file_name, is_selected)
                    # 确保UI更新，但在勾选多个时可能会导致重新渲染
                    st.rerun()
                    # st.session_state.ui_update_counter += 1
        
        col1_1, col1_2, col1_3 = st.columns([1, 1, 2])
        with col1_1:
            st.button("全选", use_container_width=True, on_click=select_all_files)
        with col1_2:
            st.button("取消全选", use_container_width=True, on_click=deselect_all_files)
        with col1_3:
            st.button("删除所选文件", use_container_width=True, type="secondary", on_click=delete_selected_files)

        button_label = "使用配置文件处理所选文件" if use_config else "处理所选文件"

        has_selected = len(st.session_state.target_files) > 0
        if st.button(button_label, use_container_width=True, type="primary", disabled=st.session_state.processing_files or not has_selected):
            if has_selected:
                st.session_state.processing_files = True
                selected_files = st.session_state.target_files
                progress_bar = st.progress(0)
                status_text = st.empty()
                success_count = 0
                total_count = len(selected_files)

                for i, file_info in enumerate(selected_files):
                    status_text.text(f"正在处理 {i+1}/{total_count}: {file_info['文件名']}")
                    config_path = ingest_config_path if use_config else DEFAULT_INGEST_CONFIG
                    if process_single_file(file_info, config_path):
                        success_count += 1
                    progress_bar.progress((i + 1) / total_count)

                if success_count > 0:
                    st.success(f"成功处理 {success_count}/{total_count} 个文件！")
                if success_count < total_count:
                    st.warning(f"有 {total_count - success_count} 个文件处理失败")
                st.session_state.processing_files = False
                status_text.text("处理完成")
                time.sleep(0.5)
                st.session_state.ui_update_counter += 1

# 以下为原始代码中剩余部分，保持不变
with col2:
    col2_title, col2_button = st.columns([5, 1])
    with col2_title:
        st.subheader("🧠 知识库状态")
    
    with col2_button:
        st.markdown("""
        <style>
        div[data-testid="stButton"] button {
            background-color: #f0f2f6;
            color: #0f52ba;
            border-radius: 20px;
            border: 1px solid #e0e0e0;
            padding: 0.2rem 0.6rem;
            font-size: 0.8rem;
            transition: all 0.3s;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #0f52ba;
            color: white;
            border: 1px solid #0f52ba;
        }
        </style>
        """, unsafe_allow_html=True)
        
        refresh_button = st.button(
            "🔄", 
            help="刷新知识库状态", 
            key="refresh_kb_status", 
            type="primary"
        )
        
        if refresh_button:
            # 直接清除状态并刷新
            st.session_state.milvus_status = None
            st.session_state.ui_update_counter += 1

    try:
        # 获取知识库状态
        if st.session_state.milvus_status is None:
            st.session_state.milvus_status = flash_rag.get_milvus_status()
        
        milvus_status = st.session_state.milvus_status
        logger.info(f"milvus_status: {milvus_status}")

        st.markdown("""
        <div style="background-color: #f0f7ff; padding: 10px; border-radius: 10px; border-left: 5px solid #0f52ba;">
            <h4 style="margin: 0; color: #0f52ba;">📊 知识库统计信息</h4>
        </div>
        """, unsafe_allow_html=True)

        if milvus_status and milvus_status.get("status") == "ok":
            try:
                # 集合总数和总段落数并排放置
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    st.metric("集合总数", milvus_status.get("collection_count", 0))
                with col2_2:
                    st.metric("总段落数", milvus_status.get("total_entities", 0), delta_color="normal")
                
                collections_info = milvus_status.get("collections_info", [])
                if collections_info:
                    with st.expander("📊 查看详细集合信息", expanded=False):
                        try:
                            df = pd.DataFrame(collections_info)
                            if not df.empty:
                                # 只保留集合名称和段落数量
                                available_columns = ["name", "row_count"]
                                display_columns = ["集合名称", "段落数量"]
                                existing_columns = [col for col in available_columns if col in df.columns]
                                df = df[existing_columns]
                                column_mapping = {k: v for k, v in zip(available_columns, display_columns) if k in existing_columns}
                                df = df.rename(columns=column_mapping)
                                st.dataframe(df, use_container_width=True)
                            else:
                                st.info("暂无集合详细信息")
                        except Exception as e:
                            st.error(f"显示集合信息时出错: {str(e)}")
                            st.info("暂无可用的集合详细信息")
            except Exception as display_err:
                st.error(f"显示知识库状态时出错: {str(display_err)}")
                st.info("无法正确显示知识库状态信息")
        else:
            st.error("无法获取知识库状态，请稍后重试")
            try:
                stats = {
                    "集合总数": "0",
                    "总段落数": "0"
                }
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    st.metric("集合总数", stats["集合总数"])
                with col2_2:
                    st.metric("总段落数", stats["总段落数"])
            except Exception as e:
                st.error(f"显示默认状态时出错: {str(e)}")
    except Exception as overall_err:
        st.error(f"知识库状态组件加载失败: {str(overall_err)}")
        logger.error(f"知识库状态组件加载失败: {str(overall_err)}")
        st.warning("请刷新页面或联系系统管理员")

st.markdown("---")
with st.container():
    st.subheader("🔎 问题查询")
    
    use_search_config = st.checkbox(
        "使用搜索配置文件", 
        value=False, 
        help="选择后将使用配置文件进行搜索，否则使用默认搜索逻辑"
    )
    if use_search_config:
        search_config_path = st.text_input(
            "搜索配置路径", 
            value=DEFAULT_SEARCH_CONFIG,
            help="请输入搜索配置文件路径"
        )
    else:
        search_config_path = DEFAULT_SEARCH_CONFIG
    
    chat_container = st.container()
    with chat_container:
        for idx, message in enumerate(st.session_state.rag_messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)
                if message["role"] == "assistant" and idx//2 < len(st.session_state.rag_retrieval_results):
                    results = st.session_state.rag_retrieval_results[idx//2]
                    if results:
                        with st.expander("📚 查看召回详细结果", expanded=False):
                            grouped_results = defaultdict(list)
                            for result in results:
                                grouped_results[result["文档"]].append(result)
                            sorted_docs = sorted(
                                grouped_results.keys(),
                                key=lambda doc: max(r["相关度"] for r in grouped_results[doc]),
                                reverse=True
                            )
                            for doc_idx, doc in enumerate(sorted_docs):
                                results_for_doc = grouped_results[doc]
                                max_relevance = max(r["相关度"] for r in results_for_doc)
                                st.markdown(f"### 📄 文档 {doc_idx+1}: {doc}")
                                st.markdown(f"**最高相关度**: {max_relevance:.2f}")
                                for i, result in enumerate(sorted(results_for_doc, key=lambda x: x["相关度"], reverse=True)):
                                    st.markdown(f"**片段 {i+1}** (相关度: {result['相关度']:.2f})")
                                    st.markdown(f"```\n{result['内容']}\n```")
                                if doc_idx < len(sorted_docs) - 1:
                                    st.markdown("---")
        
        if st.session_state.rag_processing_query and len(st.session_state.rag_messages) > 0 and st.session_state.rag_messages[-1]["role"] == "user":
            user_query = st.session_state.rag_messages[-1]["content"]
            with st.chat_message("assistant"):
                status_placeholder = st.empty()
                status_placeholder.write("🔍 正在从知识库中检索相关信息...")
                with st.spinner("正在搜索相关信息并回答..."):
                    try:
                        results = flash_rag.search_data(user_query, config=search_config_path)
                        st.session_state.rag_retrieval_results.append(results)
                        status_placeholder.write("✅ 检索完成！")
                        with st.expander("📚 查看召回详细结果", expanded=False):
                            grouped_results = defaultdict(list)
                            for result in results:
                                grouped_results[result["文档"]].append(result)
                            sorted_docs = sorted(
                                grouped_results.keys(),
                                key=lambda doc: max(r["相关度"] for r in grouped_results[doc]),
                                reverse=True
                            )
                            for doc_idx, doc in enumerate(sorted_docs):
                                results_for_doc = grouped_results[doc]
                                max_relevance = max(r["相关度"] for r in results_for_doc)
                                st.markdown(f"### 📄 文档 {doc_idx+1}: {doc}")
                                st.markdown(f"**最高相关度**: {max_relevance:.2f}")
                                for i, result in enumerate(sorted(results_for_doc, key=lambda x: x["相关度"], reverse=True)):
                                    st.markdown(f"**片段 {i+1}** (相关度: {result['相关度']:.2f})")
                                    st.markdown(f"```\n{result['内容']}\n```")
                                if doc_idx < len(sorted_docs) - 1:
                                    st.markdown("---")
                        answer_status_placeholder = st.empty()
                        answer_status_placeholder.write("🤖 正在生成回答...")
                        message_placeholder = st.empty()
                        response = ""
                        context = ""
                        for doc in sorted_docs[:3]:
                            context += f"## {doc}\n"
                            results_for_doc = sorted(grouped_results[doc], key=lambda x: x["相关度"], reverse=True)
                            for i, result in enumerate(results_for_doc[:2]):
                                context += f"{result['内容']}\n\n"
                        try:
                            # 获取当前会话的对话历史
                            chat_history = []
                            if len(st.session_state.rag_messages) > 1:
                                # 获取历史消息（除了最后一条用户问题）
                                history_messages = st.session_state.rag_messages[:-1]
                                
                                # 限制历史对话的长度，保留最近的5轮对话（10条消息）
                                if len(history_messages) > 10:
                                    history_messages = history_messages[-10:]
                                
                                chat_history = history_messages
                            
                            # 使用带历史的回答函数
                            for token in flash_rag.aigc_answer_with_history(
                                user_query, 
                                context, 
                                history=chat_history,
                                config=search_config_path
                            ):
                                response += token
                                message_placeholder.markdown(response + "▌")
                            message_placeholder.markdown(response)
                            answer_status_placeholder.write("🤖 回答完成")
                        except Exception as e:
                            st.error(f"生成回答时出错: {str(e)}")
                            response = "很抱歉，生成回答时出现错误，请稍后再试。"
                            message_placeholder.markdown(response)
                        final_response = response
                        st.session_state.rag_messages.append({"role": "assistant", "content": final_response})
                        st.session_state.rag_processing_query = False
                    except Exception as e:
                        st.error(f"搜索时出错: {str(e)}")
                        st.session_state.rag_processing_query = False
    
    user_query = st.chat_input(placeholder="请输入您的问题，例如：什么是Flash RAG?")
    if user_query:
        process_query(user_query)

st.markdown("---")
st.caption("© 2024 Flash RAG 知识库检索系统")