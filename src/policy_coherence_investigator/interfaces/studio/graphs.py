"""Case-specific graph builders for local LangSmith Studio exploration.

These entry points expose only agent-visible case data. They deliberately never load the
hidden evaluation oracle; ``evals.run_case`` remains responsible for post-run evaluation.
"""

from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from policy_coherence_investigator.case_data import load_case
from policy_coherence_investigator.infrastructure import build_chat_model
from policy_coherence_investigator.retrieval import load_policy_corpus
from policy_coherence_investigator.workflows import build_bounded_investigation_graph

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def build_studio_case_graph(
    case_id: str,
    *,
    model: BaseChatModel | None = None,
) -> CompiledStateGraph:
    """Build a zero-input graph for inspecting one synthetic case in Studio."""
    case = load_case(case_id)
    corpus_directory = REPOSITORY_ROOT / "evals" / "corpora" / case.case.corpus_id
    corpus = load_policy_corpus(corpus_directory)
    return build_bounded_investigation_graph(
        model or build_chat_model(),
        corpus,
        initial_case=case,
    )
