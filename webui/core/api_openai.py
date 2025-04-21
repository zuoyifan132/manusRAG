from openai import OpenAI


class LLMCaller(object):
    def __init__(self, api_key, **kwargs):
        self.api_key = api_key
        self.base_url = kwargs.get('base_url', None)
        self.model = kwargs.get('model', 'gpt-4o-mini')
        self.inited = False
        self._init()

    def _init(self):
        if not self.inited:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        self.inited = True

    def chat_stream(self, messages, **kwargs):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )

        collected_chunks = []
        collected_messages = ""
        for chunk in response:
            try:
                chunk_message = chunk.choices[0].delta.content
                collected_chunks.append(chunk_message)
                collected_messages += chunk_message
                yield chunk_message
            except:
                pass
