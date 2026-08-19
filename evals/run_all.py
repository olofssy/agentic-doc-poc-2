"""Sequential explicit runner for every policy-coherence evaluation case."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from dotenv import load_dotenv

from policy_coherence_investigator.case_data import discover_case_ids
from policy_coherence_investigator.investigation import Architecture

from .run_case import CaseRunReport, print_case_report, run_case


@dataclass(frozen=True)
class CaseExecutionFailure:
    """A failed invocation, distinct from a completed evaluation failure."""

    case_id: str
    error_type: str
    message: str


@dataclass(frozen=True)
class EvaluationSuiteReport:
    """All sequential case outcomes, including execution failures."""

    case_reports: tuple[CaseRunReport, ...]
    execution_failures: tuple[CaseExecutionFailure, ...]

    @property
    def passed(self) -> bool:
        return not self.execution_failures and all(report.passed for report in self.case_reports)


def run_all_cases(
    case_ids: Sequence[str],
    *,
    architecture: Architecture = Architecture.BOUNDED,
    provider: str | None = None,
) -> EvaluationSuiteReport:
    """Run all requested cases without letting one provider failure stop the suite."""

    reports: list[CaseRunReport] = []
    failures: list[CaseExecutionFailure] = []
    for case_id in case_ids:
        try:
            reports.append(run_case(case_id, architecture=architecture, provider=provider))
        except Exception as error:
            failures.append(
                CaseExecutionFailure(
                    case_id=case_id,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )
    return EvaluationSuiteReport(tuple(reports), tuple(failures))


def main(argv: Sequence[str] | None = None) -> int:
    """Run every case with compact per-case lines and a one-line suite summary."""

    parser = argparse.ArgumentParser(description="Run every policy-coherence evaluation case.")
    parser.add_argument("--provider", choices=("openai", "anthropic"))
    parser.add_argument(
        "--architecture",
        type=Architecture,
        choices=tuple(Architecture),
        default=Architecture.BOUNDED,
    )
    args = parser.parse_args(argv)

    load_dotenv()
    suite = run_all_cases(
        discover_case_ids(),
        architecture=args.architecture,
        provider=args.provider,
    )
    for report in suite.case_reports:
        print_case_report(report)
    for failure in suite.execution_failures:
        print(f"{failure.case_id}: ERROR | {failure.error_type}: {failure.message}")
    passed_count = sum(report.passed for report in suite.case_reports)
    print(
        f"suite: {'PASS' if suite.passed else 'FAIL'} | "
        f"passed={passed_count}/{len(suite.case_reports)} | errors={len(suite.execution_failures)}"
    )
    return 0 if suite.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
