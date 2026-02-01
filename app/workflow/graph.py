from langgraph.graph import StateGraph, END, START
from app.models.graph import GraphState
from app.pdf_data_extraction.extract import process_file
from app.ai.document_extraction import validate_invoice
from app.ai.matching import match_invoice_with_db
from app.ai.validation import validate_invoice_with_po
from app.audit.document_extraction_trail import log_document_intelligence_agent_results
from app.audit.matching_trail import log_matching_agent_results
from app.audit.audit_validation_trail import log_validation_agent_results


# Create nodes (functions)
async def document_extraction_and_validation_agent_node(
    state: GraphState,
):
    print("\n" + "=" * 60)
    print("---DOCUMENT EXTRACTION AND VALIDATION NODE---")

    file_name = state.file_name

    # Extract the text from the given file
    extracted_text = process_file(file_name)

    # Validate the invoice results
    result = await validate_invoice(extracted_text)

    # --- LOG CONFIDENCE SCORES & REASONING ---
    log_document_intelligence_agent_results(result)

    # Assuming the response is what you want
    return {
        "extracted_invoice_results": result.extracted_data,
        "document_intelligence_agent_state": result,
        "discrepancies": result.discrepancies or [],
    }


async def matching_agent_node(state: GraphState):
    print("\n" + "=" * 60)
    print("---DOCUMENT MATCHING AGENT NODE---")

    invoice = state.extracted_invoice_results
    if invoice is None:
        raise ValueError("No extracted invoice data.")

    result = await match_invoice_with_db(invoice)

    # --- LOG CONFIDENCE SCORES & REASONING ---
    log_matching_agent_results(result)

    return {
        "matching_agent_state": result,
        "discrepancies": result.discrepancies or [],
    }


async def auditing_validation_node(state: GraphState):
    print("\n" + "=" * 60)
    print("---AUDITING AND VALIDATION AGENT NODE---")

    invoice = state.extracted_invoice_results
    if invoice is None:
        raise ValueError("No extracted invoice data.")

    matched_po_number = None
    matching_agent_state = state.matching_agent_state
    if matching_agent_state is None:
        raise ValueError("Matching Agent did not populate the state.")
    matched_po_number = matching_agent_state.matched_po
    if matched_po_number is None:
        raise ValueError("No Matching PO Number.")

    result = await validate_invoice_with_po(invoice, matched_po_number)

    # --- LOG CONFIDENCE SCORES & REASONING ---
    log_validation_agent_results(result)

    return {
        "audit_validation_agent_state": result,
        "discrepancies": result.discrepancies or [],
    }


# Create the graph
graph = StateGraph(GraphState)

# Build the Nodes
graph.add_node(
    "Document Extraction and Validation Node",
    document_extraction_and_validation_agent_node,
)
graph.add_node("Document Matching Node", matching_agent_node)
graph.add_node("Audit and Validation Node", auditing_validation_node)

# Connect the Edges
graph.add_edge(START, "Document Extraction and Validation Node")
graph.add_edge("Document Extraction and Validation Node", "Document Matching Node")
graph.add_edge("Document Matching Node", "Audit and Validation Node")
graph.add_edge("Audit and Validation Node", END)


compiled_graph = graph.compile()
