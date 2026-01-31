from typing import Protocol, Type, TypeVar
from pydantic import BaseModel
from ollama import chat
from langchain_google_genai import ChatGoogleGenerativeAI
from groq import Groq
from app.core.config import (
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    OLLAMA_MODEL,
    GOOGLE_MODEL,
    GROQ_MODEL,
)

T = TypeVar("T", bound=BaseModel)


### HELPER FUNCTION FOR VALIDATION ###
def parse_structured_output(raw: object, output_model: Type[T]) -> T:
    if not isinstance(raw, str):
        raise TypeError(f"Expected JSON string, got {type(raw)}")

    return output_model.model_validate_json(raw)


### Pythonic Protocol for a common invoke method for all llms ###
class StructuredLLM(Protocol):
    async def invoke(
        self,
        prompt: str,
        output_model: Type[T],
    ) -> T: ...


### Ollama Implementation
class OllamaStructuredLLM:
    def __init__(self, model: str):
        self.model = model

    async def invoke(
        self,
        prompt: str,
        output_model: Type[T],
    ) -> T:
        response = chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format=output_model.model_json_schema(),
        )

        return parse_structured_output(response.message.content, output_model)


### Google Implementation
class GoogleStructuredLLM:
    def __init__(self, api_key: str, model: str):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=api_key,
            temperature=0,
            response_mime_type="application/json",
        )

    async def invoke(
        self,
        prompt: str,
        output_model: Type[T],
    ) -> T:
        response = self.llm.invoke(prompt)

        return parse_structured_output(response.content, output_model)


### Groq Implementation
class GroqStructuredLLM:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = Groq(api_key=api_key)
        self.model = model

    async def invoke(
        self,
        prompt: str,
        output_model: Type[T],
    ) -> T:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output_generation",
                    "schema": output_model.model_json_schema(),
                },
            },
        )

        content = completion.choices[0].message.content
        return parse_structured_output(content, output_model)


class LLMProviderFactory:
    @staticmethod
    def ollama() -> StructuredLLM:
        return OllamaStructuredLLM(model=OLLAMA_MODEL)

    @staticmethod
    def google() -> StructuredLLM:
        return GoogleStructuredLLM(
            model=GOOGLE_MODEL,
            api_key=GOOGLE_API_KEY,
        )

    @staticmethod
    def groq() -> StructuredLLM:
        return GroqStructuredLLM(api_key=GROQ_API_KEY, model=GROQ_MODEL)