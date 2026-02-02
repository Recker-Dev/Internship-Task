import asyncio
from app.workflow.graph import compiled_graph
from app.models.graph import GraphState
from pprint import pprint


async def main():
    result = await compiled_graph.ainvoke(
        GraphState(file_name="Invoice_5_Missing_PO.pdf")
    )

    pprint(result["resolution_agent_state"])


if __name__ == "__main__":
    asyncio.run(main())
