import streamlit as st
import os
import uuid
from pathlib import Path

# 创建上传目录
def create_upload_dir():
    upload_dir = Path("uploaded_files")
    upload_dir.mkdir(exist_ok=True)
    return upload_dir

# 初始化会话状态
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
    
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

def delete_files(files_to_delete):
    for file_info in files_to_delete:
        try:
            os.remove(file_info['path'])
            st.session_state.uploaded_files = [
                f for f in st.session_state.uploaded_files if f['id'] != file_info['id']
            ]
        except Exception as e:
            st.error(f"删除失败: {e}")
    
    st.session_state.uploader_key += 1
    return len(files_to_delete)

def main():
    st.title("文件上传与管理")
    upload_dir = create_upload_dir()
    
    uploaded_files = st.file_uploader(
        "选择要上传的文件",
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if not any(f['name'] == uploaded_file.name for f in st.session_state.uploaded_files):
                file_id = str(uuid.uuid4())
                file_path = os.path.join(upload_dir, uploaded_file.name)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.session_state.uploaded_files.append({
                    'id': file_id,
                    'name': uploaded_file.name,
                    'path': file_path,
                    'size': uploaded_file.size
                })
    
    if st.session_state.uploaded_files:
        st.subheader("已上传的文件")
        
        files_to_delete = []
        for file_info in st.session_state.uploaded_files:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.checkbox("", key=f"del_{file_info['id']}"):
                    files_to_delete.append(file_info)
            with col2:
                st.write(file_info['name'])
        
        if files_to_delete and st.button("删除选中的文件"):
            deleted_count = delete_files(files_to_delete)
            st.success(f"成功删除 {deleted_count} 个文件")
            st.rerun()
    else:
        st.info("尚未上传任何文件")

if __name__ == "__main__":
    main()
