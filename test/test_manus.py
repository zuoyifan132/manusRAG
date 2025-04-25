import sys
sys.path.append("..")

from manus.manus_deep_search_agent import DeepSearch


if __name__ == "__main__":
    # original_query="帮我找找今年中国最大的AI公司都与哪些公司合作，合作的这些公司中抽取2个，给我他们的公司介绍，最后用markdown表格展示一下"

    # original_query = "阿里巴巴、腾讯和拼多多的共同股东有哪些？"

    original_query = "请问Rachel的电话是多少"

    deep_search_agent = DeepSearch()

    final_answer, retrieved_docs = deep_search_agent.query(query=original_query)

    print("Final answer: ", final_answer)
