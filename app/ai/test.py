from app.models.test import DocumentIntelligenceAgentOutput
from app.ai.prompts import INVOICE_VALIDATION_PROMPT
from app.llm.builder import LLMProviderFactory


async def validate_invoice(invoice_str: str) -> DocumentIntelligenceAgentOutput:

    # Prepare the input for the prompt
    prompt_load = {
        "INVOICE_DETAILS": invoice_str,
        "INVOICE_FORMAT": DocumentIntelligenceAgentOutput.model_json_schema(),
    }

    # Format the prompt using the template
    prompt = INVOICE_VALIDATION_PROMPT.format(**prompt_load)

    # Invoke the LLM with the formatted prompt
    llm = LLMProviderFactory.groq()

    return await llm.invoke(prompt, DocumentIntelligenceAgentOutput)
    # print(DocumentIntelligenceAgentOutput.model_json_schema())
    # return  "Hello"
