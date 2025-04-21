from PyPDF2 import PdfReader
from parser.baseParser import BaseParser
from utils.minerU_api import mineru_file_parse_api


class PDFParser(BaseParser):
    def __init__(self, pdf_path):
        super().__init__(pdf_path)

    def read_content(self):
        """Implement reading logic for PDF content. This method is intended to be overridden."""
        raise NotImplementedError("Subclasses must implement read_content for specific PDF libraries.")

    def extract_text(self):
        """Implement PDF text extraction logic. This method is intended to be overridden."""
        raise NotImplementedError("Subclasses must implement extract_text for specific PDF libraries.")


class PyPDF2Parser(PDFParser):
    def __init__(self, pdf_path):
        super().__init__(pdf_path)

    def read_content(self):
        """Read the PDF file using PyPDF2 and store the reader object in self.content."""
        self.content = PdfReader(self.path)

    def extract_text(self):
        """Extract text from the PDF reader stored in self.content."""
        if self.content is None:
            raise ValueError("Content is not loaded. Call read_content() first.")

        full_text = ""
        for page in self.content.pages:
            page_text = page.extract_text()
            full_text += page_text if page_text else ""  # Ensure text extraction handles possible None values.
            full_text += "\n"

        return full_text


class minerUParser(PDFParser):
    def __init__(self, pdf_path):
        super().__init__(pdf_path)

    def read_content(self):
        """Read the PDF file using PyPDF2 and store the reader object in self.content."""
        self.content = mineru_file_parse_api(self.path).get("md_content", "")

    def extract_text(self):
        """Extract text from the PDF reader stored in self.content."""
        if not self.content:
            raise ValueError("Content is not loaded. Call read_content() first.")
        return self.content


# 示例用法：
if __name__ == "__main__":
    pdf_parser = PDFParser("example.pdf")
    pdf_parser.read_content()  # 读取内容至 content
    text = pdf_parser.extract_text()  # 提取文本
    print(text)