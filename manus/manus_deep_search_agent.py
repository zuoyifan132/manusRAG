from abc import ABC
import logging
from typing import Any, List, Tuple
import asyncio

from manus.base_agent import describe_class, RAGAgent
from manus.llm import LLM, OpenAILLM
from manus.retrieval import (
    flash_rag_searcher
)
from manus.prompt import (
    SUB_QUERY_PROMPT,
    RERANK_PROMPT,
    SYSTEM_PROMPT,
    REFLECT_PROMPT,
    SUMMARY_PROMPT
)


@describe_class("Agent for handling general queries and generating reports.")
class DeepSearch(RAGAgent):
    def __init__(
        self,
        llm: LLM = None,
        max_iter: int = 3,
    ):
        self.llm = llm if llm is not None else OpenAILLM()
        self.max_iter = max_iter

    def _format_list(self, items: List, prefix: str = "") -> str:
        """Format a list of items for display."""
        return "\n".join(f"{prefix}{i+1}. {item}" for i, item in enumerate(items))
    
    def _format_chunks(self, chunks: List) -> str:
        """Format chunks for display."""
        return "\n".join(f"CHUNK {i+1}:\n{chunk}\n" for i, chunk in enumerate(chunks))
    
    def _print_separator(self, title: str = None):
        """Print a separator line with optional title."""
        if title:
            print(f"\n{'='*20} {title} {'='*20}")
        else:
            print(f"\n{'-'*50}")

    def _generate_sub_queries(self, original_query: str) -> List[str]:
        """Generate sub-queries from the original query."""
        self._print_separator("GENERATING SUB-QUERIES")
        print(f"Original query: {original_query}")
        
        user_prompt = SUB_QUERY_PROMPT.format(original_query=original_query)
        response = self.llm.chat(
            system_prompt=SYSTEM_PROMPT, 
            user_prompt=user_prompt
        )
        sub_queries = self.llm.list_literal_eval(response.content)

        if not sub_queries:
            logging.warning(f"generate empty sub_queries for {original_query}")
            print("WARNING: No sub-queries generated!")
        else:
            print("\nGenerated sub-queries:")
            print(self._format_list(sub_queries, "  "))
            
        return sub_queries

    async def _search_chunks(self, query: str, sub_queries: List[str]) -> List:
        """Search for relevant chunks in the source"""
        self._print_separator(f"SEARCHING CHUNKS FOR: {query}")
        all_results = []
        
        print("Retrieving from RAG...")
        rag_retrievals = flash_rag_searcher(query)[1]
        print(f"Found RAG results: {rag_retrievals}")

        all_results.extend(rag_retrievals)
        print(f"Total results before filtering: {len(all_results)}")
            
        # Filter relevant results
        filtered_results = []
        print("\nReranking results...")
        
        # TODO: parallel rerank
        for i, result in enumerate(all_results):
            print(f"  Processing result {i+1}/{len(all_results)}...")
            user_prompt = RERANK_PROMPT.format(
                query=[query] + sub_queries,
                retrieved_chunk=result
            )
            response = self.llm.chat(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            if response.content.startswith("YES"):
                filtered_results.append(result)
                print(f"  ✓ Accepted result {i+1}")
            else:
                print(f"  ✗ Rejected result {i+1}")
        
        print(f"\nFiltered results: {len(filtered_results)}/{len(all_results)}")
        if filtered_results:
            print("\nFiltered chunks preview:")
            print(self._format_chunks(filtered_results[:3]))
            if len(filtered_results) > 3:
                print(f"... and {len(filtered_results)-3} more chunks")
                
        return filtered_results
    
    def _generate_gap_queries(
            self, 
            original_query: str, 
            sub_queries: List[str], 
            chunks: List
        ) -> List[str]:
            """Generate additional queries based on gaps in retrieved information."""
            self._print_separator("GENERATING GAP QUERIES")
            print(f"Original query: {original_query}")
            print(f"Sub-queries so far: {len(sub_queries)}")
            print(f"Retrieved chunks: {len(chunks)}")
            
            chunk_texts = [chunk for chunk in chunks]
            user_prompt = REFLECT_PROMPT.format(
                question=original_query,
                mini_questions=sub_queries,
                mini_chunk_str=self._format_chunks(chunk_texts)
            )
            response = self.llm.chat(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            gap_queries = self.llm.list_literal_eval(response.content)

            if not gap_queries:
                logging.warning(f"generate empty gap_queries for original_query: {original_query} and sub_queries: {sub_queries}")
                print("No gap queries identified - retrieval complete!")
            else:
                print("\nIdentified gap queries:")
                print(self._format_list(gap_queries, "  "))

            return gap_queries

    async def async_retrieve(self, original_query: str) -> List:
        """Asynchronously retrieve relevant documents."""
        self._print_separator("STARTING RETRIEVAL PROCESS")
        print(f"Original query: {original_query}")
        print(f"Maximum iterations: {self.max_iter}")
        
        all_results = []
        all_sub_queries = []
        
        # Initial sub-queries
        sub_queries = self._generate_sub_queries(original_query)
        if not sub_queries:
            print("No sub-queries generated. Aborting retrieval.")
            return []
            
        all_sub_queries.extend(sub_queries)
        current_queries = sub_queries

        # Iterative retrieval
        for iteration in range(self.max_iter):
            self._print_separator(f"ITERATION {iteration+1}/{self.max_iter}")
            print(f"Current queries to process: {len(current_queries)}")
            
            # Parallel search
            search_tasks = [
                self._search_chunks(query, current_queries)
                for query in current_queries
            ]
            search_results = await asyncio.gather(*search_tasks)
            
            # Combine results
            current_results = []
            for result in search_results:
                current_results.extend(result)
                
            print(f"New results this iteration: {len(current_results)}")
            all_results.extend(current_results)
            
            # Deduplicate
            before_dedup = len(all_results)
            all_results = self._deduplicate_results(all_results)
            print(f"Results after deduplication: {len(all_results)} (removed {before_dedup - len(all_results)} duplicates)")

            # Check for gaps
            current_queries = self._generate_gap_queries(
                original_query, 
                all_sub_queries, 
                all_results
            )
            if not current_queries:
                print("No gap queries generated. Ending retrieval process.")
                break
                
            all_sub_queries.extend(current_queries)
            print(f"Total sub-queries so far: {len(all_sub_queries)}")

        self._print_separator("RETRIEVAL COMPLETE")
        print(f"Total chunks retrieved: {len(all_results)}")
        print(f"Total queries generated: {len(all_sub_queries)}")
        
        return all_results, all_sub_queries

    def retrieve(self, query: str, **kwargs) -> List:
        """Synchronous wrapper for retrieval."""
        return asyncio.run(self.async_retrieve(query))

    def query(self, query: str, **kwargs) -> Tuple[str, List]:
        """Generate answer and return with retrieved documents."""
        self._print_separator("PROCESSING QUERY")
        print(f"Query: {query}")
        
        retrieved_docs, sub_queries = self.retrieve(query)
        
        self._print_separator("GENERATING FINAL RESPONSE")
        print(f"Retrieved {len(retrieved_docs)} documents")
        print(f"Generated {len(sub_queries)} sub-queries")
        
        user_prompt = SUMMARY_PROMPT.format(
            question=query,
            mini_questions=sub_queries,
            mini_chunk_str=retrieved_docs
        )
        print("Generating summary...")
        response = self.llm.chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        self._print_separator("RESPONSE READY")
        print("Summary generated successfully")
        
        return response.content, retrieved_docs

    def _deduplicate_results(self, results: List) -> List:
        """Remove duplicate results (implementation depends on your needs)."""
        seen = set()
        unique_results = []
        for result in results:
            if result not in seen:
                seen.add(result)
                unique_results.append(result)
        return unique_results
    

if __name__ == "__main__":
    # Test the DeepSearch with a sample query
    print("\nTesting DeepSearch with a sample query:")
    agent = DeepSearch()
    response, docs = agent.query("请问什么是RAG，RAG的原理是什么？以及跟openmanus有什么联系，什么区别")
    
    print("\nFINAL RESPONSE:")
    print(response)
