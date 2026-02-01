from langgraph.graph import StateGraph, END, START
from app.models.graph import GraphState
from app.pdf_data_extraction.extract import process_file
from app.ai.document_extraction import validate_invoice
from app.ai.matching import match_invoice_with_db


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
    conf = result.extraction_confidence
    print("\n[Extraction Confidence Scores]")
    print(f"  Overall confidence: {conf.overall:.2%}")
    if conf.invoice_number is not None:
        print(f"  Invoice number confidence: {conf.invoice_number:.2%}")
    if conf.po_number is not None:
        print(f"  PO reference confidence: {conf.po_number:.2%}")
    if conf.line_items_avg is not None:
        print(f"  Line items average confidence: {conf.line_items_avg:.2%}")
    if conf.totals is not None:
        print(f"  Totals confidence: {conf.totals:.2%}")

    print("\n[Agent Reasoning]")
    print(f"  {result.agent_reasoning}\n")
    print("=" * 60 + "\n")

    # Assuming the response is what you want
    return {
        "extracted_invoice_results": result.extracted_data,
        "document_intelligence_agent_state": result,
    }


async def matching_agent_node(state: GraphState):
    print("\n" + "=" * 60)
    print("---DOCUMENT MATCHING AGENT NODE---")

    invoice = state.extracted_invoice_results
    if invoice is None:
        raise ValueError("No extracted invoice data.")

    result = await match_invoice_with_db(invoice)

    # --- LOG CONFIDENCE SCORES & REASONING ---
    print("\n[Matching Confidence Scores]")
    if result.match_method is not None:
        print(f"  Match Method Used: {result.match_method}")
    if result.matched_po is not None:
        print(f"  Matched PO: {result.matched_po}")
    if result.po_match_confidence is not None:
        print(f"  Po Match Found confidence: {result.po_match_confidence:.2%}")
    if result.supplier_match is not None:
        print(f"  Supplier match status: {result.supplier_match}")
    if result.date_variance_days is not None:
        print(f"  Date variance of: {result.date_variance_days} days")
    if result.match_rate is not None:
        print(f"  Line items match confidence: {result.match_rate:.2%}")

    if result.alternative_matches:
        print(f"""Alternate Matches Found:""")
        for match in result.alternative_matches:
            print(f"  Po Match Found: {match.po_number}")
            print(f"  Po Match Found confidence: {match.confidence:.2%}")
            print(f"  Match Method Used: {match.match_method}")

    print("\n[Agent Reasoning]")
    print(f"  {result.agent_reasoning}\n")
    print("=" * 60 + "\n")

    return {"matching_agent_state": result}


# Create the graph
graph = StateGraph(GraphState)

# Build the Nodes
graph.add_node(
    "Document Extraction and Validation Node",
    document_extraction_and_validation_agent_node,
)
graph.add_node("Document Matching Node", matching_agent_node)

# Connect the Edges
graph.add_edge(START, "Document Extraction and Validation Node")
graph.add_edge("Document Extraction and Validation Node", "Document Matching Node")
graph.add_edge("Document Matching Node", END)


compiled_graph = graph.compile()
