from abc import ABC, abstractmethod


class BaseParser(ABC):
    def __init__(self, path):
        self.path = path
        self.content = None

    @abstractmethod
    def read_content(self):
        """Read content from the source file and store it in self.content."""
        pass

    @abstractmethod
    def extract_text(self):
        """Extract text from self.content."""
        pass
