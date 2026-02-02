import asyncio

from pydantic import ValidationError
from app.workflow.graph import compiled_graph
from app.models.graph import GraphState
from app.utils.helpers import format_workflow_output, save_json_output


async def main():
    file_name = "Invoice_1_Baseline.pdf"
    # file_name = "Invoice_2_Scanned.pdf"
    # file_name = "Invoice_3_Different_Format.pdf"
    # file_name = "Invoice_4_Price_Trap.pdf"
    # file_name = "Invoice_5_Missing_PO.pdf"

    try:
        initial_state = GraphState(file_name=file_name)

        print(f"--- Starting Workflow for: {file_name} ---")
        result = await compiled_graph.ainvoke(initial_state)
        print("--- Workflow Completed Successfully ---")

        formatted_json = format_workflow_output(result)

        print("\n## FINAL SYSTEM OUTPUT")
        print(formatted_json)
        save_json_output(formatted_json, file_name)

    except ValidationError as e:
        print(f"[Schema Error]: State validation failed.")
        for error in e.errors():
            print(f"  - Field {error['loc']}: {error['msg']}")

    except FileNotFoundError as e:
        print(f"[File Error]: Could not locate the document. {e}")

    except TypeError as e:
        print(f"[Type Error]: An operation was performed on an incompatible type. {e}")

    except ValueError as e:
        print(f"[Value Error]: Received an inappropriate value. {e}")

    except RuntimeError as e:
        print(f"[Runtime Error]: An error occurred during runtime execution. {e}")

    except Exception as e:
        print(f"[Unexpected Error]: {type(e).__name__} - {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
