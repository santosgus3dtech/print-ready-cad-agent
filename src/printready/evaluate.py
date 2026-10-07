import json

from .knowledge import search_knowledge
from .store import ROOT


def evaluate() -> dict:
    dataset = [json.loads(line) for line in (ROOT / "evals" / "dataset.jsonl").read_text().splitlines()]
    results = []
    for example in dataset:
        retrieved = [doc["id"] for doc in search_knowledge(example["query"], 3)]
        rank = retrieved.index(example["expected"]) + 1 if example["expected"] in retrieved else 0
        results.append({**example, "retrieved": retrieved, "rank": rank})
    return {
        "corpus": "illustrative-design-notes-v1",
        "questions": len(results),
        "recall_at_3": sum(row["rank"] > 0 for row in results) / len(results),
        "mrr_at_3": sum(1 / row["rank"] if row["rank"] else 0 for row in results) / len(results),
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
