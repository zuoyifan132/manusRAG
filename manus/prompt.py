SUB_QUERY_PROMPT = """To answer this question more comprehensively, please break down the original question into up to four sub-questions. Return as list of str.
If this is a very simple question and no decomposition is necessary, then keep the only one original question in the list.
Remember the generated sub-questions should be suitable for the local RAG system, the sub-questions must contain subject since pronoun like "it", "they", "them", etc do not provide any information.
Original Question: {original_query}
<EXAMPLE>
Example input:
"Explain deep learning"
Example output:
[
    "What is deep learning?",
    "What is the difference between deep learning and machine learning?",
    "What is the history of deep learning?"
]
</EXAMPLE>
State in the language of the original question.
Provide your response in list of str format:
"""


RERANK_PROMPT = """Based on the query questions and the retrieved chunk, to determine whether the chunk is helpful in answering any of the query question, you can only return "YES" or "NO", without any other information.
Query Questions: {query}
Retrieved Chunk: {retrieved_chunk}
State in the language of the original question.
Is the chunk helpful in answering the any of the questions?
"""


REFLECT_PROMPT = """Determine whether additional search queries are needed based on the original query, previous sub queries, and all retrieved document chunks. If further research is required, provide a Python list of up to 3 search queries. If no further research is required, return an empty list.
If the original query is to write a report, then you prefer to generate some further queries, instead return an empty list.
Remember the generated queries should be suitable for the local RAG system, the queries must contain subject since pronoun like "it", "they", "them", etc do not provide any information.
Original Query: {question}
Previous Sub Queries: {mini_questions}
Related Chunks: 
{mini_chunk_str}
State in the language of the original question.
Respond exclusively in valid List of str format without any other text."""


SUMMARY_PROMPT = """You are a AI content analysis expert, good at summarizing content. Please summarize a specific and detailed answer or report based on the previous queries and the retrieved document chunks.
Original Query: {question}
Previous Sub Queries: {mini_questions}
Related Chunks: 
{mini_chunk_str}
State in the language of the original question.
"""


SYSTEM_PROMPT = "You are a helper assistant"
