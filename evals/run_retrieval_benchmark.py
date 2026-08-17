"""Print a compact, deterministic lexical retrieval baseline report."""

from .retrieval_benchmark import load_default_lexical_scores


def main() -> int:
    """Run the local retrieval benchmark without calling an LLM or embedding service."""

    scores = load_default_lexical_scores()
    for score in scores:
        retrieved_count = sum(
            rank is not None and rank <= score.top_k for rank in score.ranks.values()
        )
        print(
            f"{score.scenario_id}: recall={retrieved_count}/{len(score.required_references)} "
            f"at@{score.top_k}"
        )
        for reference in score.required_references:
            rank = score.ranks[(reference.document_id, reference.clause_id)]
            print(f"  {reference.document_id}/{reference.clause_id}: rank={rank or 'not-ranked'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
