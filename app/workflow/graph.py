from langgraph.graph import StateGraph, END, START
from app.models.test import GraphState
from app.pdf_data_extraction.extract import process_file
from app.ai.test import validate_invoice


# Create nodes (functions)
async def document_intelligence_agent_node(state: GraphState) -> GraphState:
    print("\n" + "=" * 60)
    print("---DOCUMENT INTELLIGENCE AGENT NODE---")

    file_name = state["file_name"]

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
    if conf.po_reference is not None:
        print(f"  PO reference confidence: {conf.po_reference:.2%}")
    if conf.line_items_avg is not None:
        print(f"  Line items average confidence: {conf.line_items_avg:.2%}")
    if conf.totals is not None:
        print(f"  Totals confidence: {conf.totals:.2%}")

    print("\n[Agent Reasoning]")
    print(f"  {result.agent_reasoning}\n")
    print("=" * 60 + "\n")

    # Assuming the response is what you want
    return {**state, "document_intelligence_agent_state": result}


# Create the graph
graph = StateGraph(GraphState)

# Build the Nodes
graph.add_node("Document Intelligence Agent", document_intelligence_agent_node)

# Connect the Edges
graph.add_edge(START, "Document Intelligence Agent")
graph.add_edge("Document Intelligence Agent", END)


compiled_graph = graph.compile()
