from abc import ABC, abstractmethod
import sys
import ast
import re
import requests
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI
import os

sys.path.append("..")
from services.config import OPENAI_API_KEY

@dataclass
class Response:
    """Container for language model responses."""
    content: str
    token: int

class LLM(ABC):
    """Abstract base class for language model interfaces."""
    
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> Response:
        """Generate a response using the language model."""
        pass
    
    def list_literal_eval(self, text: str) -> List[str]:
        """Extract a list of strings from model response text."""
        # First, try standard literal_eval to parse the text as a Python list
        try:
            list_match = re.search(r'\[(.*?)\]', text, re.DOTALL)
            if list_match:
                list_text = list_match.group(0)
                result = ast.literal_eval(list_text)
                if isinstance(result, list):
                    return result
        except (ValueError, SyntaxError):
            pass  # Continue to other methods if this fails
        
        # Try to extract items from numbered or bulleted lists
        lines = text.strip().split('\n')
        items = []
        
        # Pattern for numbered lists and bulleted lists
        NUMBERED_PATTERN = re.compile(r'^\s*\d+\.\s*(.+)$')
        BULLETED_PATTERN = re.compile(r'^\s*[•\-\*]\s*(.+)$')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for numbered list item
            match = NUMBERED_PATTERN.match(line)
            if match:
                items.append(match.group(1))
                continue
                
            # Check for bulleted list item
            match = BULLETED_PATTERN.match(line)
            if match:
                items.append(match.group(1))
                continue
                
            # Check for quoted items
            if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
                items.append(line[1:-1])
        
        # If we found list items using the patterns above
        if items:
            return items
        
        # Last resort: return single line as a single-item list
        if len(lines) == 1 and lines[0]:
            return [lines[0]]
        
        # If we've exhausted all options and found nothing, return empty list
        return []


class DeepSeekV3LLM(LLM):
    """Implementation of LLM using DeepSeek API through a custom endpoint."""
    def __init__(
        self, 
        temperature: float = 0.0, 
        max_tokens: int = 8124,
        stream: bool = False
    ):
        """Initialize DeepSeek LLM."""
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.url = "http://10.10.178.25:12239/aigateway/deepseek/chat/completions"
        self.pkey = "MDlGQTM0RUZFOUYxREY5Njk4MzQyQzcwNDQ1MkIxMDY="
        self.source = "Wind.AI.Insight"
    
    def chat(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        **kwargs
    ) -> Response:
        """Generate a response using DeepSeek API."""
        # Override instance defaults with any provided kwargs
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        stream = kwargs.get("stream", self.stream)
        
        # Prepare request parameters
        params = {
            "body": {
                "model": "deepseek-chat",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 1,
                "stream": stream,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            },
            "pkey": self.pkey,
            "source": self.source,
        }

        headers = {
            "content-type": "application/json",
            "wind.sessionid": "fc2f592799164bac8c384e85aafe63e5"
        }

        # Send POST request
        resp = requests.post(url=self.url, json=params, headers=headers, stream=stream)
        
        # Handle the response based on whether streaming is enabled
        if stream:
            # Combine streamed chunks into a complete response
            full_response = self._process_stream_response(resp)
        else:
            # Process the complete response directly
            resp_json = resp.json()
            full_response = resp_json.get("body", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens = resp_json.get("body", {}).get("usage", [{}]).get("completion_tokens", 0)
        
        return Response(
            content=full_response,
            token=tokens
        )
    
    def _process_stream_response(self, response) -> str:
        """Process a streaming response from the API."""
        combined_content = ""
        
        for line in response.iter_lines():
            if line:
                # Skip empty lines
                line_text = line.decode('utf-8')
                
                # Skip the "data: " prefix if present
                if line_text.startswith('data: '):
                    line_text = line_text[6:]
                
                # Skip "[DONE]" message
                if line_text == "[DONE]":
                    continue
                
                try:
                    # Parse the JSON from the line
                    data = json.loads(line_text)
                    
                    # Extract the content delta if available
                    content_delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    combined_content += content_delta
                except json.JSONDecodeError:
                    continue
        
        return combined_content


class OpenAILLM(LLM):
    """Implementation of LLM using OpenAI API."""
    def __init__(
        self, 
        api_key: Optional[str] = OPENAI_API_KEY,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0, 
        max_tokens: int = 4096,
        stream: bool = False
    ):
        """Initialize OpenAI LLM."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.client = OpenAI(api_key=self.api_key)
    
    def chat(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        **kwargs
    ) -> Response:
        """Generate a response using OpenAI API."""
        # Override instance defaults with any provided kwargs
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        stream = kwargs.get("stream", self.stream)
        
        try:
            # Create chat completion request
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
            
            if stream:
                # Process streaming response
                full_response = self._process_stream_response(response)
                # Note: For streaming responses, token count is not easily accessible
                tokens = 0
            else:
                # Extract response content
                full_response = response.choices[0].message.content
                tokens = response.usage.completion_tokens
            
            return Response(
                content=full_response,
                token=tokens
            )
            
        except Exception as e:
            # Handle exceptions gracefully
            print(f"OpenAI API request error: {str(e)}")
            return Response(content="", token=0)
    
    def _process_stream_response(self, stream) -> str:
        """Process a streaming response from the OpenAI API."""
        combined_content = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                combined_content += content
                # Uncomment to print streaming output
                # print(content, end="", flush=True)
        
        return combined_content


if __name__ == "__main__":
    deepseekv3 = DeepSeekV3LLM()

    SUB_QUERY_PROMPT = """To answer this question more comprehensively, please break down the original question into up to four sub-questions. Return as list of str.
If this is a very simple question and no decomposition is necessary, then keep the only one original question in the list.
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
Provide your response in list of str format:
"""

    user_prompt = SUB_QUERY_PROMPT.format(
        original_query="帮我找找今年中国最大的AI公司都与哪些公司合作，合作的这些公司中抽取2个，给我他们的公司介绍，最后用markdown表格展示一下"
    )

    response = deepseekv3.chat("You are a helper assistant", user_prompt=user_prompt)
    response_obj = deepseekv3.list_literal_eval(response.content)
    print(response_obj)