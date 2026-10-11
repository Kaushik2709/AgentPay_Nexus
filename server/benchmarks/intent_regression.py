"""Offline parser comparison: no model invocation and no commerce side effects."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from app.agents.purchase_intent import parse_purchase_intent, select_products
from app.commerce import paise


def evaluate(proposals=None):
    dataset=json.loads(Path(__file__).with_name("intent_cases.json").read_text())
    products=[SimpleNamespace(sku=p["sku"],name=p["name"],retail_price=p["price"],
        stock_quantity=5,description="",specifications="{}") for p in dataset["catalog"]]
    rows=[]
    for case in dataset["cases"]:
        intent=parse_purchase_intent(case["prompt"],case["cap"])
        selected=[p.sku for p in select_products(products,intent)]
        ambiguous=(intent["quantity_unsupported"] or intent["unresolved_clauses"] or
            set(intent["requested_families"]) & set(intent["excluded_families"]))
        actual={"selected_skus":selected,"budget_paise":paise(intent["effective_budget"]),
                "action":"CLARIFY" if ambiguous else "PROPOSE" if selected else "UNAVAILABLE"}
        row={"id":case["id"],"deterministic":actual,"passed":actual == case["expected"]}
        if proposals is not None:
            row["proposal_matches_expected"]=proposals.get(case["id"]) == case["expected"]
            row["proposal_matches_deterministic"]=proposals.get(case["id"]) == actual
        rows.append(row)
    return {"cases":len(rows),"deterministic_passed":sum(row["passed"] for row in rows),
            "llm_invoked":False,"proposal_comparison_supplied":proposals is not None,"results":rows}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--proposals",help="Optional offline JSON object mapping case IDs to model proposals")
    parser.add_argument("--output")
    args=parser.parse_args()
    proposals=json.loads(Path(args.proposals).read_text()) if args.proposals else None
    if proposals is not None and not isinstance(proposals,dict): parser.error("Proposals must be an object")
    result=evaluate(proposals)
    encoded=json.dumps(result,indent=2)+"\n"
    if args.output: Path(args.output).write_text(encoded)
    print(encoded)
    raise SystemExit(result["deterministic_passed"] != result["cases"])
