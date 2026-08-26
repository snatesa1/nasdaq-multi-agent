import asyncio
import logging
from app.orchestrator import HierarchicalOrchestrator

logging.basicConfig(level=logging.INFO)

async def test():
    orch = HierarchicalOrchestrator()
    res = await orch.run_full_analysis()
    print("Test Complete. Selected Holy Grail Assets:", res["tier3"])

if __name__ == "__main__":
    asyncio.run(test())
