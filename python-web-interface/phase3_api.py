from fastapi import FastAPI
import uuid

app = FastAPI(title="Phase3 API - Intelligence")


@app.get("/status")
async def status():
    return {"status": "ok", "component": "phase3", "version": "1.0"}


@app.post("/rule-compiler/compile")
async def compile_rule(body: dict):
    """Return a simple, syntactically-valid JSON-Logic example based on input."""
    compiled = {
        "rule_id": str(uuid.uuid4()),
        "regulation_type": body.get("regulation_type", "AML"),
        "jurisdiction": body.get("jurisdiction", "EU"),
        "json_logic": {
            "and": [
                {">=": [{"var": "transaction_amount"}, 15000]},
                {"in": [{"var": "customer_type"}, ["PEP", "HighRisk"]]}
            ]
        }
    }
    return {"compiled": compiled}
