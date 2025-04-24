import sys
sys.path.append(".")
sys.path.append("..")

from parser.WordParser import DocxParser

def main():
    """示例：如何使用WordParser解析Word文档"""
    # 文档路径
    word_file_path = "/Users/evan/Desktop/rest/wzy/cv/Resume_RachelWang_fin.docx"
    
    try:
        # 创建DocxParser实例
        parser = DocxParser(word_file_path)
        
        # 读取文档内容
        parser.read_content()
        
        # 提取文本
        text = parser.extract_text()
        
        # 打印提取的文本
        print("从Word文档中提取的文本：")
        print("-" * 50)
        print(text)
        print("-" * 50)
        
        # 可以在这里继续处理提取的文本
        # 例如：存储到数据库，进行文本分析等
        
    except Exception as e:
        print(f"处理Word文档时出错: {str(e)}")


if __name__ == "__main__":
    main() 