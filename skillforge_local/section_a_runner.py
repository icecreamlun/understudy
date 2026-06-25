from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

from skillforge_local.contracts import SkillCandidate, parse_event
from skillforge_local.episode_builder import build_episodes
from skillforge_local.io_jsonl import read_jsonl, write_jsonl
from skillforge_local.pattern_detector import detect_skill_candidates


def run_section_a(
    events_path: Path,
    episodes_path: Path,
    candidates_path: Path,
) -> None:
    events = [parse_event(record) for record in read_jsonl(events_path)]
    episodes = build_episodes(events)
    candidates = detect_skill_candidates(episodes)

    write_jsonl(episodes_path, [asdict(episode) for episode in episodes])
    write_jsonl(
        candidates_path, [_candidate_record(candidate) for candidate in candidates]
    )


def _candidate_record(candidate: SkillCandidate) -> dict[str, Any]:
    return {key: value for key, value in asdict(candidate).items() if value is not None}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section A workflow detection.")
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--episodes", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    args = parser.parse_args()

    run_section_a(args.events, args.episodes, args.candidates)


if __name__ == "__main__":
    main()
