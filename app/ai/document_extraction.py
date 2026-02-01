from app.models.document_extraction_model import DocumentIntelligenceAgentOutput
from app.llm.builder import LLMProviderFactory

INVOICE_VALIDATION_PROMPT = """
You are an invoice extraction agent.

Your task is to extract structured invoice data from the provided invoice text and return it in **valid JSON** that strictly matches the following data model:


Rules:
- Output **JSON only**. Do not include explanations or commentary.
- Use the exact field names shown above.
- Do not invent or infer missing values.
- If a field is not explicitly present, return an empty string for strings, an empty array for lists, or null for numbers.
- Extract all line items present on the invoice.
- Ensure numeric values are returned as numbers, not strings.
- Do not perform calculations unless values are explicitly stated.
- Preserve original wording for names and addresses.
- Also populate the field of document_quality and agent_reasoning.

Invoice Text:
{INVOICE_DETAILS}
"""


async def validate_invoice(invoice_str: str) -> DocumentIntelligenceAgentOutput:

    # Prepare the input for the prompt
    prompt_load = {
        "INVOICE_DETAILS": invoice_str,
    }

    # Format the prompt using the template
    prompt = INVOICE_VALIDATION_PROMPT.format(**prompt_load)

    # Invoke the LLM with the formatted prompt
    llm = LLMProviderFactory.groq()

    return await llm.invoke(prompt, DocumentIntelligenceAgentOutput)
