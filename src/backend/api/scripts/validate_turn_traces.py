from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass
class TraceValidationSummary:
    sampled_turns: int
    turns_with_trace: int
    turns_with_tools: int
    tools_with_trace: int
    turns_with_a2a: int
    a2a_with_trace: int

    @property
    def turn_coverage_pct(self) -> float:
        return (self.turns_with_trace / self.sampled_turns * 100) if self.sampled_turns else 0.0

    @property
    def tool_coverage_pct(self) -> float:
        return (
            (self.tools_with_trace / self.turns_with_tools * 100) if self.turns_with_tools else 0.0
        )

    @property
    def a2a_coverage_pct(self) -> float:
        return (self.a2a_with_trace / self.turns_with_a2a * 100) if self.turns_with_a2a else 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate turn/tool/A2A trace coverage")
    parser.add_argument("--sampled-turns", type=int, required=True)
    parser.add_argument("--turns-with-trace", type=int, required=True)
    parser.add_argument("--turns-with-tools", type=int, required=True)
    parser.add_argument("--tools-with-trace", type=int, required=True)
    parser.add_argument("--turns-with-a2a", type=int, required=True)
    parser.add_argument("--a2a-with-trace", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = TraceValidationSummary(
        sampled_turns=args.sampled_turns,
        turns_with_trace=args.turns_with_trace,
        turns_with_tools=args.turns_with_tools,
        tools_with_trace=args.tools_with_trace,
        turns_with_a2a=args.turns_with_a2a,
        a2a_with_trace=args.a2a_with_trace,
    )

    output = asdict(summary)
    output["turn_coverage_pct"] = round(summary.turn_coverage_pct, 2)
    output["tool_coverage_pct"] = round(summary.tool_coverage_pct, 2)
    output["a2a_coverage_pct"] = round(summary.a2a_coverage_pct, 2)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
