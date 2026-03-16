"""Temporal worker entrypoint."""
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.contrib.pydantic import pydantic_data_converter
from config import TEMPORAL_HOST, TASK_QUEUE
from workflows.investigate import InvestigatePaymentWorkflow
from activities.planner import plan_investigation
from activities.company import run_company_agent
from activities.adverse_media import run_adverse_media_agent
from activities.payment_pattern import run_payment_pattern_agent
from activities.sanctions import run_sanctions_agent
from observability.logging import configure_logging


async def main():
    configure_logging()
    client = await Client.connect(TEMPORAL_HOST, data_converter=pydantic_data_converter)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[InvestigatePaymentWorkflow],
        activities=[
            plan_investigation,
            run_company_agent,
            run_adverse_media_agent,
            run_payment_pattern_agent,
            run_sanctions_agent,
        ],
    )
    print(f"Worker started. Listening on task queue '{TASK_QUEUE}'...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
