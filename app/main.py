import asyncio
from app.workflow.graph import compiled_graph


async def main():
    result = await compiled_graph.ainvoke(
        {
            "file_name": "Invoice_1_Baseline.pdf",
            "document_intelligence_agent_state": None,
        }
    )

    print(result)

if __name__ == "__main__":
    asyncio.run(main())
