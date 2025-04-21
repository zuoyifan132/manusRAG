from parser.baseParser import BaseParser


class MarkdownParser(BaseParser):
    def __init__(self, markdown_path):
        super().__init__(path=markdown_path)
        self.markdown_path = markdown_path


class NaiveMarkdownParser(MarkdownParser):
    def __init__(self, markdown_path):
        super().__init__(markdown_path=markdown_path)
    
    def read_content(self):
        """Read content from the markdown file."""
        try:
            with open(self.markdown_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
        except Exception as e:
            raise Exception(f"Failed to read markdown file: {str(e)}")
    
    def extract_text(self):
        """
        Extract text from the markdown content.
        
        This is a naive implementation that simply returns the raw markdown text.
        More sophisticated implementations could parse the markdown and extract 
        only the text content, removing markdown syntax.
        """
        if self.content is None:
            raise Exception("Content not loaded. Call read_content() first.")
        
        return self.content 