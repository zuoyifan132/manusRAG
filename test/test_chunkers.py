import sys
import unittest
sys.path.append(".")
sys.path.append("..")

from chunking.textChunker import PunctuationChunker, RecursiveChunker

class TestChunkers(unittest.TestCase):
    def setUp(self):
        """设置测试数据"""
        self.sample_text = """
        这是一个测试文本。它包含多个句子，每个句子都以标点符号结束。
        这是第二段。它也有多个句子！
        这是第三段？它包含不同的标点符号。
        """
        
        self.long_text = """
        这是一个较长的测试文本。它包含多个段落和句子。
        每个段落都有不同的内容。有些句子很长，有些很短。
        这个文本用于测试分块功能。我们希望看到它被正确地分割成多个块。
        测试不同的标点符号：句号。感叹号！问号？分号；逗号，
        这是另一个段落。它包含更多的内容。
        最后一段。测试结束。
        """

    def test_punctuation_chunker_basic(self):
        """测试 PunctuationChunker 的基本功能"""
        chunker = PunctuationChunker()
        document = chunker.chunk(
            text=self.sample_text,
            title="测试文档",
            min_chunk_size=20,
            max_chunk_size=50,
            overlap_chunk_size=5
        )
        
        # 验证返回的是 Document 对象
        self.assertIsNotNone(document)
        self.assertIsNotNone(document.chunks)
        self.assertIsNotNone(document.metadata)
        
        # 验证块的数量
        self.assertGreater(len(document.chunks), 0)
        
        # 验证每个块的大小
        for chunk in document.chunks:
            self.assertGreaterEqual(len(chunk), 20)
            self.assertLessEqual(len(chunk), 50)

    def test_punctuation_chunker_edge_cases(self):
        """测试 PunctuationChunker 的边缘情况"""
        chunker = PunctuationChunker()
        
        # 测试空文本
        document = chunker.chunk(
            text="",
            title="空文本测试",
            min_chunk_size=20,
            max_chunk_size=50,
            overlap_chunk_size=5
        )
        self.assertEqual(len(document.chunks), 0)
        
        # 测试短文本
        short_text = "这是一个短文本。"
        document = chunker.chunk(
            text=short_text,
            title="短文本测试",
            min_chunk_size=20,
            max_chunk_size=50,
            overlap_chunk_size=5
        )
        self.assertEqual(len(document.chunks), 1)
        self.assertEqual(document.chunks[0], short_text)

    def test_recursive_chunker_basic(self):
        """测试 RecursiveChunker 的基本功能"""
        chunker = RecursiveChunker(chunk_size=50)
        document = chunker.chunk(
            text=self.long_text,
            title="递归分块测试"
        )
        
        # 验证返回的是 Document 对象
        self.assertIsNotNone(document)
        self.assertIsNotNone(document.chunks)
        self.assertIsNotNone(document.metadata)
        
        # 验证块的数量
        self.assertGreater(len(document.chunks), 0)
        
        # 验证每个块的大小
        for chunk in document.chunks:
            self.assertLessEqual(len(chunk), 50)

    def test_recursive_chunker_custom_separators(self):
        """测试 RecursiveChunker 的自定义分隔符"""
        custom_separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " "]
        chunker = RecursiveChunker(
            chunk_size=50,
            separators=custom_separators
        )
        
        document = chunker.chunk(
            text=self.long_text,
            title="自定义分隔符测试"
        )
        
        # 验证返回的是 Document 对象
        self.assertIsNotNone(document)
        self.assertGreater(len(document.chunks), 0)

    def test_recursive_chunker_keep_separator(self):
        """测试 RecursiveChunker 的 keep_separator 参数"""
        # 测试保留分隔符
        chunker = RecursiveChunker(
            chunk_size=50,
            keep_separator=True
        )
        document = chunker.chunk(
            text=self.sample_text,
            title="保留分隔符测试"
        )
        
        # 验证分隔符被保留
        for chunk in document.chunks:
            self.assertTrue(any(sep in chunk for sep in ["。", "！", "？"]))

        # 测试不保留分隔符
        chunker = RecursiveChunker(
            chunk_size=50,
            keep_separator=False
        )
        document = chunker.chunk(
            text=self.sample_text,
            title="不保留分隔符测试"
        )
        
        # 验证分隔符被移除
        for chunk in document.chunks:
            self.assertFalse(any(sep in chunk for sep in ["。", "！", "？"]))

if __name__ == '__main__':
    unittest.main() 