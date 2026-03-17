"""Evaluation harness: run labeled payments and report accuracy/consistency."""
import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from temporalio.client import Client
from config import TEMPORAL_HOST, TASK_QUEUE
from observability.logging import configure_logging
from schemas.payment import Payment
from schemas.risk_decision import Decision
from workflows.investigate import InvestigatePaymentWorkflow

# Labeled payments with expected decisions — one per seeded recipient
LABELED_PAYMENTS = [
    {
        "payment": {
            "payment_id": "eval_techflow_001",
            "sender": {"name": "Evaluator Corp", "account_id": "EVAL001", "bank": "Test Bank"},
            "recipient": {"name": "TechFlow Solutions", "account_id": "GB82WEST12345698765433", "bank": "Westpac"},
            "amount": 8500.0,
            "currency": "GBP",
            "reference": "Software licence renewal",
            "timestamp": "2024-11-15T12:00:00Z",
        },
        "expected": Decision.APPROVE,
        "label": "safe_established",
    },
    {
        "payment": {
            "payment_id": "eval_greenenergy_001",
            "sender": {"name": "Evaluator Corp", "account_id": "EVAL001", "bank": "Test Bank"},
            "recipient": {"name": "Green Energy Partners", "account_id": "GB82WEST12345698765500", "bank": "Westpac"},
            "amount": 12000.0,
            "currency": "GBP",
            "reference": "Consulting services",
            "timestamp": "2024-11-15T10:00:00Z",
        },
        "expected": Decision.APPROVE,
        "label": "safe_new_company",
    },
    {
        "payment": {
            "payment_id": "eval_acme_001",
            "sender": {"name": "Evaluator Corp", "account_id": "EVAL001", "bank": "Test Bank"},
            "recipient": {"name": "Acme Consulting Ltd", "account_id": "GB29NWBK60161331926819", "bank": "NatWest"},
            "amount": 45000.0,
            "currency": "GBP",
            "reference": "Advisory services Q4",
            "timestamp": "2024-11-15T09:00:00Z",
        },
        "expected": Decision.REVIEW,
        "label": "ambiguous_old_media_hit",
    },
    {
        "payment": {
            "payment_id": "eval_nova_001",
            "sender": {"name": "Evaluator Corp", "account_id": "EVAL001", "bank": "Test Bank"},
            "recipient": {"name": "Nova Import Export", "account_id": "GB29NWBK60161388888888", "bank": "NatWest"},
            "amount": 250000.0,
            "currency": "GBP",
            "reference": "Goods shipment",
            "timestamp": "2024-11-15T08:00:00Z",
        },
        "expected": Decision.REVIEW,
        "label": "risky_pep_connection",
    },
    {
        "payment": {
            "payment_id": "eval_fastcash_001",
            "sender": {"name": "Evaluator Corp", "account_id": "EVAL001", "bank": "Test Bank"},
            "recipient": {"name": "FastCash Holdings", "account_id": "GB29NWBK60161399999999", "bank": "NatWest"},
            "amount": 95000.0,
            "currency": "GBP",
            "reference": "Urgent transfer",
            "timestamp": "2024-11-15T11:00:00Z",
        },
        "expected": Decision.REJECT,
        "label": "sanctioned_recipient",
    },
]


async def run_evaluation(runs_per_payment: int = 3):
    configure_logging()
    client = await Client.connect(TEMPORAL_HOST)

    results_summary = []

    for labeled in LABELED_PAYMENTS:
        payment = Payment.model_validate(labeled["payment"])
        expected = labeled["expected"]
        decisions = []

        for run_idx in range(runs_per_payment):
            wf_id = f"{payment.payment_id}_eval_run_{run_idx}"
            result = await client.execute_workflow(
                InvestigatePaymentWorkflow.run,
                payment,
                id=wf_id,
                task_queue=TASK_QUEUE,
            )
            decisions.append(result.decision)

        correct = sum(1 for d in decisions if d == expected)
        consistent = len(set(decisions)) == 1

        results_summary.append({
            "payment_id": payment.payment_id,
            "label": labeled["label"],
            "expected": expected,
            "decisions": decisions,
            "accuracy": correct / runs_per_payment,
            "consistent": consistent,
        })

    # Aggregate metrics
    total = len(results_summary)
    pct_correct = sum(r["accuracy"] for r in results_summary) / total * 100
    pct_consistent = sum(1 for r in results_summary if r["consistent"]) / total * 100

    print(f"\n{'='*60}")
    print("EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"Payments evaluated: {total}")
    print(f"Runs per payment:   {runs_per_payment}")
    print(f"Accuracy:           {pct_correct:.1f}%")
    print(f"Consistency:        {pct_consistent:.1f}%")
    print(f"\nPer-payment breakdown:")
    for r in results_summary:
        status = "PASS" if r["accuracy"] == 1.0 else "FAIL"
        print(f"  [{status}] {r['payment_id']} ({r['label']}): expected={r['expected']}, got={r['decisions']}, consistent={r['consistent']}")

    print(f"\nFull JSON results:")
    print(json.dumps(results_summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run_evaluation())
