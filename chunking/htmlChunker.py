import sys

sys.path.append(".")
sys.path.append("..")

from typing import List, Dict, Tuple, Any, Optional
from chunking.baseChunker import BaseChunker, Document


class HTMLChunker(BaseChunker):
    """A chunker that splits HTML content into structured Documents based on headers."""

    def __init__(
        self,
        html_headers_to_split_on: List[Tuple[str, str]],
        return_each_element: bool = False
    ):
        """Initialize the HTMLChunker with splitting options."""
        super().__init__()
        self.html_headers_to_split_on = sorted(html_headers_to_split_on, key=lambda x: int(x[0][1:]))
        self.header_mapping = dict(self.html_headers_to_split_on)
        self.header_tags = [tag for tag, _ in self.html_headers_to_split_on]
        self.return_each_element = return_each_element

    def chunk(self, text: str, title: str = "", **kwargs) -> List[Document]:
        """
        Split the HTML text into a list of Document objects based on specified headers.

        Args:
            text (str): The HTML text to be chunked
            title (str): The title of the document (optional)
            **kwargs: Additional arguments (not used in this implementation)

        Returns:
            List[Document]: A list of Document objects with chunk and metadata
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("Please install BeautifulSoup via `pip install bs4`.")

        # Parse HTML content
        soup = BeautifulSoup(text, "html.parser")
        body = soup.body if soup.body else soup

        # Internal state for chunking
        active_headers: Dict[str, Tuple[str, int, int]] = {}  # {header_name: (text, level, depth)}
        current_chunk: List[str] = []

        def finalize_chunk() -> Optional[Document]:
            """Finalize the current chunk into a Document."""
            if not current_chunk:
                return None
            final_text = "  \n".join(line for line in current_chunk if line.strip())
            current_chunk.clear()
            if not final_text.strip():
                return None
            final_meta = {}
            if title:
                final_meta["title"] = title
            final_meta.update({k: v[0] for k, v in active_headers.items()})
            return Document(chunk=final_text, metadata=final_meta)

        # Result list
        documents: List[Document] = []

        # DFS traversal using a stack
        stack = [body]
        while stack:
            node = stack.pop()
            children = list(node.children)
            from bs4.element import Tag

            for child in reversed(children):
                if isinstance(child, Tag):
                    stack.append(child)

            tag = getattr(node, "name", None)
            if not tag:
                continue

            text_elements = [str(child).strip() for child in node.find_all(string=True, recursive=False)]
            node_text = " ".join(elem for elem in text_elements if elem)
            if not node_text:
                continue

            dom_depth = len(list(node.parents))

            # Handle header tags
            if tag in self.header_tags:
                if not self.return_each_element:
                    doc = finalize_chunk()
                    if doc:
                        documents.append(doc)

                # Determine header level (e.g., h1 -> 1)
                level = int(tag[1:]) if tag[1:].isdigit() else 9999

                # Remove headers at or below this level
                headers_to_remove = [k for k, (_, lvl, _) in active_headers.items() if lvl >= level]
                for key in headers_to_remove:
                    del active_headers[key]

                # Update active headers
                header_name = self.header_mapping[tag]
                active_headers[header_name] = (node_text, level, dom_depth)

                # Add header as a Document
                header_meta = {}
                if title:
                    header_meta["title"] = title
                header_meta.update({k: v[0] for k, v in active_headers.items()})
                documents.append(Document(chunk=node_text, metadata=header_meta))

            # Handle non-header content
            else:
                # Remove headers out of scope (deeper than current depth)
                headers_out_of_scope = [k for k, (_, _, d) in active_headers.items() if dom_depth < d]
                for key in headers_out_of_scope:
                    del active_headers[key]

                if self.return_each_element:
                    meta = {}
                    if title:
                        meta["title"] = title
                    meta.update({k: v[0] for k, v in active_headers.items()})
                    documents.append(Document(chunk=node_text, metadata=meta))
                else:
                    current_chunk.append(node_text)

        # Finalize any remaining chunk
        if not self.return_each_element:
            doc = finalize_chunk()
            if doc:
                documents.append(doc)

        return documents
    
    
# Example usage:
if __name__ == "__main__":
    html_content = """
<html>
  <head>
    <title>Complex HTML Example</title>
  </head>
  <body>
    <h1>Chapter 1: Introduction to Data Science</h1>
    <p>This chapter introduces the fundamentals of data science.</p>
    <h2>Section 1.1: What is Data Science?</h2>
    <p>Data science combines statistics, programming, and domain knowledge.</p>
    <ul>
      <li>Statistics: Understanding data distributions.</li>
      <li>Programming: Tools like Python and R.</li>
      <li>Domain Knowledge: Context-specific insights.</li>
    </ul>
    <h3>Subsection 1.1.1: History</h3>
    <p>Data science evolved from traditional statistics in the late 20th century.</p>
    <h3>Subsection 1.1.2: Modern Tools</h3>
    <p>Today, we use tools like TensorFlow and Pandas.</p>
    <table>
      <tr>
        <th>Tool</th>
        <th>Purpose</th>
      </tr>
      <tr>
        <td>TensorFlow</td>
        <td>Machine Learning</td>
      </tr>
      <tr>
        <td>Pandas</td>
        <td>Data Manipulation</td>
      </tr>
    </table>

    <h2>Section 1.2: Applications</h2>
    <p>Data science is applied in various fields.</p>
    <h3>Subsection 1.2.1: Healthcare</h3>
    <p>Predictive models help in diagnosing diseases.</p>
    <h3>Subsection 1.2.2: Finance</h3>
    <p>Algorithms detect fraudulent transactions.</p>

    <h1>Chapter 2: Machine Learning Basics</h1>
    <p>An overview of machine learning concepts.</p>
    <h2>Section 2.1: Supervised Learning</h2>
    <p>Supervised learning uses labeled data.</p>
    <div>
      <h3>Subsection 2.1.1: Regression</h3>
      <p>Regression predicts continuous outcomes.</p>
      <h3>Subsection 2.1.2: Classification</h3>
      <p>Classification predicts discrete categories.</p>
    </div>
    <h2>Section 2.2: Unsupervised Learning</h2>
    <p>Unsupervised learning finds patterns without labels.</p>
  </body>
</html>
    """

    html_headers_to_split_on = [
        ("h1", "Chapter"),
        ("h2", "Section"),
        ("h3", "Subsection")
    ]
    chunker = HTMLChunker(html_headers_to_split_on=html_headers_to_split_on, return_each_element=False)
    docs = chunker.chunk(html_content, title="Complex HTML Example")

    for doc in docs:
        print(f"Content: {doc.chunk}")
        print(f"Metadata: {doc.metadata}")
        print("---")