"""Submit InvestigatePaymentWorkflow and print result."""
import argparse
import asyncio
import json
import sys
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from config import TEMPORAL_HOST, TASK_QUEUE
from observability.logging import configure_logging
from schemas.payment import Payment
from workflows.investigate import InvestigatePaymentWorkflow


async def run(payment_file: str):
    configure_logging()
    with open(payment_file) as f:
        data = json.load(f)

    # Support both single payment (dict) and list
    if isinstance(data, list):
        payments = [Payment.model_validate(p) for p in data]
    else:
        payments = [Payment.model_validate(data)]

    client = await Client.connect(TEMPORAL_HOST, data_converter=pydantic_data_converter)

    for payment in payments:
        result = await client.execute_workflow(
            InvestigatePaymentWorkflow.run,
            payment,
            id=payment.payment_id,
            task_queue=TASK_QUEUE,
        )
        print(result.model_dump_json(indent=2))


def main():
    parser = argparse.ArgumentParser(description="Run beneficiary risk assessment")
    parser.add_argument("--payment-file", required=True, help="Path to payment JSON file")
    args = parser.parse_args()
    asyncio.run(run(args.payment_file))


if __name__ == "__main__":
    main()
