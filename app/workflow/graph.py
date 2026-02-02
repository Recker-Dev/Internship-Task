from langgraph.graph import StateGraph, END, START
from app.models.graph import GraphState
from app.pdf_data_extraction.extract import process_file
from app.ai.document_extraction import validate_invoice
from app.ai.matching import match_invoice_with_db
from app.ai.validation import validate_invoice_with_po
from app.ai.resolution import resolve_invoice_findings
from app.audit.document_extraction_trail import log_document_intelligence_agent_results
from app.audit.matching_trail import log_matching_agent_results
from app.audit.audit_validation_trail import log_validation_agent_results
from app.audit.resolution_trail import log_resolution_agent_results
from app.models.discrepancies_models.DocumentIntelligenceDiscrepancies import (
    CreditNoteDiscrepancy,
    CurrencyMismatchDiscrepancy,
    LowExtractionConfidenceDiscrepancy,
)
from app.models.discrepancies_models.MatchingDiscrepancies import (
    MultiplePOCandidatesDiscrepancy,
    POReferenceDiscrepancy,
    PartialDeliveryDiscrepancy,
)


# Create nodes (functions)
async def document_extraction_and_validation_node(
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
        "last_node_triggered": "document_intelligence_node",
    }


async def matching_node(state: GraphState):
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
        "last_node_triggered": "po_matching_node",
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
        "last_node_triggered": "audit_and_validation_node",
    }


async def resolution_node(state: GraphState):
    print("\n" + "=" * 60)
    print("---RESOLUTION AGENT NODE---")
    if state.early_exit:
        print("Early Exit Triggered -> Resolving Based on accumulated data yet.")

    result = await resolve_invoice_findings(
        state.document_intelligence_agent_state,
        state.matching_agent_state,
        state.audit_validation_agent_state,
    )

    # --- LOG CONFIDENCE SCORES & REASONING ---
    log_resolution_agent_results(result)

    return {
        "resolution_agent_state": result,
        "last_node_triggered": "resolution_node",
    }


def should_continue(state: GraphState) -> bool:
    ## Early Exit
    if len(state.discrepancies) >= 3:
        return False

    ## Check what was the last node and carry checks accordingly
    if state.last_node_triggered == "document_intelligence_node":

        ## Check for discrepancies triggered by document_intelligence_node
        if len(state.discrepancies) > 0:
            for d in state.discrepancies:
                if isinstance(d, CreditNoteDiscrepancy) or isinstance(
                    d, CurrencyMismatchDiscrepancy
                ):
                    state.early_exit = True
                    return False
                if isinstance(d, LowExtractionConfidenceDiscrepancy):
                    for entry in d.fields:
                        if entry.recommended_action == "escalate_to_human":
                            state.early_exit = True
                            return False

    elif state.last_node_triggered == "po_matching_node":
        ## Check a valid PO Number exist for validation agent
        if not state.matching_agent_state:
            print("Early Exit Triggered: Matching Agent did not populate it's state.")
            state.early_exit = True
            return False
        else:
            if not state.matching_agent_state.matched_po:
                print(
                    "Early Exit Triggered: Matching Agent did not pass a valid PO Number in  it's state."
                )
                state.early_exit = True
                return False

        ## Check for discrepancies triggered by po_matching_node
        if len(state.discrepancies) > 0:
            for d in state.discrepancies:
                if (
                    isinstance(d, POReferenceDiscrepancy)
                    or isinstance(d, MultiplePOCandidatesDiscrepancy)
                    or isinstance(d, PartialDeliveryDiscrepancy)
                ):
                    if d.recommended_action == "escalate_to_human":
                        return False

    return True


# Create the graph
graph = StateGraph(GraphState)

# Build the Nodes
graph.add_node(
    "Document Intelligence Agent",
    document_extraction_and_validation_node,
)
graph.add_node("Po Matching Agent", matching_node)
graph.add_node("Audit and Validation Agent", auditing_validation_node)
graph.add_node("Resolution Agent", resolution_node)

# Connect the Edges
graph.add_edge(START, "Document Intelligence Agent")
graph.add_conditional_edges(
    "Document Intelligence Agent",
    should_continue,
    {True: "Po Matching Agent", False: "Resolution Agent"},
)
graph.add_conditional_edges(
    "Po Matching Agent",
    should_continue,
    {True: "Audit and Validation Agent", False: "Resolution Agent"},
)
graph.add_edge("Audit and Validation Agent", "Resolution Agent")
graph.add_edge("Resolution Agent", END)


compiled_graph = graph.compile()
