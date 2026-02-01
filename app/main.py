import asyncio
from app.workflow.graph import compiled_graph
from app.models.graph import GraphState
from pprint import pprint


async def main():
    result = await compiled_graph.ainvoke(
        GraphState(file_name="Invoice_4_Price_Trap.pdf")
    )

    pprint(result["discrepancies"])


if __name__ == "__main__":
    asyncio.run(main())
