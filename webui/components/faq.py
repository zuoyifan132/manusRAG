import base64
import os
import textwrap

import streamlit as st


def clear_chat_history(system_prompt: str = "") -> None:
    """"""
    st.session_state["messages"] = [{"role": "system", "content": system_prompt}]
    if "agent_history" in st.session_state:
        st.session_state.agent_history = []
    st.rerun()


def get_pdf_download_link(file_path: str, link_text: str) -> str:
    """"""
    try:
        with open(file_path, "rb") as fp:
            pdf_data = fp.read()
            b64 = base64.b64encode(pdf_data).decode('utf-8')
            href = f'<a href="data:application/pdf;base64,{b64}" download="{os.path.basename(file_path)}">{link_text}</a>'
            return href
    except FileNotFoundError:
        return f'<span style="color:red;">文件未找到: {file_path}</span>'
    except Exception as exc:
        return f'<span style="color:red;">加载错误: {str(exc)}</span>'

# def truncate_markdown_table(markdown_text, max_rows=20, truncation_message="*... (表格已截断，点击上方展开查看完整表格) ...*"):
#     """
#     截取Markdown表格的前N行
    
#     参数:
#         markdown_text (str): 原始Markdown文本
#         max_rows (int): 保留的最大行数（包括表头和分隔符）
#         truncation_message (str): 截断提示信息
        
#     返回:
#         tuple: (是否为表格, 处理后的文本)
#     """
#     # 检查是否为空文本
#     if not markdown_text or not isinstance(markdown_text, str):
#         return False, markdown_text
    
#     # 分割成行
#     lines = markdown_text.split('\n')
    
#     # 检测是否为Markdown表格
#     # 表格标志：1. 包含|符号 2. 有表头分隔符（包含 -|- 或类似格式）
#     has_pipe = any('|' in line for line in lines)
#     has_separator = any(
#         line.strip().startswith('|') and 
#         all(cell.strip() == '' or all(c == '-' or c == ':' or c == ' ' for c in cell.strip()) 
#             for cell in line.strip('|').split('|'))
#         for line in lines
#     )
    
#     is_table = has_pipe and has_separator
    
#     # 如果不是表格或行数不超过限制，直接返回原文本
#     if not is_table or len(lines) <= max_rows:
#         return is_table, markdown_text
    
#     # 保留前N行（确保包含表头和分隔符）
#     truncated_lines = lines[:max_rows]
    
#     # 添加截断提示
#     truncated_lines.append(truncation_message)
    
#     # 组合回文本
#     truncated_text = '\n'.join(truncated_lines)
    
#     return True, truncated_text


def truncate_markdown_table(markdown_text, head_rows=15, tail_rows=5, 
                           truncation_message="*... 中间行已省略 ...*"):
    """
    截取Markdown表格的前N行和后M行，中间省略
    
    参数:
        markdown_text (str): 原始Markdown文本
        head_rows (int): 保留的头部行数
        tail_rows (int): 保留的尾部行数
        truncation_message (str): 截断提示信息
        
    返回:
        tuple: (是否为表格, 处理后的文本)
    """
    # 检查是否为空文本
    if not markdown_text or not isinstance(markdown_text, str):
        return False, markdown_text
    
    # 分割成行
    lines = markdown_text.split('\n')
    
    # 检测是否为Markdown表格
    has_pipe = any('|' in line for line in lines)
    
    # 寻找表头分隔符（通常是第二行，包含 -|-）
    header_separator_indices = [
        i for i, line in enumerate(lines) 
        if '|' in line and 
        all(cell.strip() == '' or all(c == '-' or c == ':' or c == ' ' for c in cell.strip()) 
            for cell in line.strip('|').split('|'))
    ]
    
    has_separator = len(header_separator_indices) > 0
    is_table = has_pipe and has_separator
    
    # 如果不是表格或行数不超过 head_rows + tail_rows，直接返回原文本
    if not is_table or len(lines) <= (head_rows + tail_rows):
        return is_table, markdown_text
    
    # 获取第一行的结构（用于构建省略行）
    if lines and '|' in lines[0]:
        first_row = lines[0]
        # 计算表格列数
        cols = len(first_row.split('|')) - 1 - first_row.count('||')
        # 创建与表格结构一致的省略行
        if first_row.startswith('|') and first_row.endswith('|'):
            ellipsis_row = '|' + '|'.join([' ' + truncation_message + ' ' if i == cols//2 else ' ... ' 
                                         for i in range(cols)]) + '|'
        else:
            ellipsis_row = ' | '.join([truncation_message if i == cols//2 else '...' 
                                     for i in range(cols)])
    else:
        # 创建简单的省略行
        ellipsis_row = truncation_message
    
    # 保留前head_rows行和后tail_rows行
    head_lines = lines[:head_rows]
    tail_lines = lines[-tail_rows:] if len(lines) > tail_rows else []
    
    # 组合结果
    truncated_lines = head_lines + [ellipsis_row] + tail_lines
    truncated_text = '\n'.join(truncated_lines)
    
    return is_table, truncated_text

def faq():
    """"""
    st.markdown(textwrap.dedent("""
        # FAQ
        ## How does FlashBrowser work?
        xxx
    """))
