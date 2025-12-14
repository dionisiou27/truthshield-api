#!/usr/bin/env python3
"""
Bandit Replay CLI
Replay historical logs through bandit to validate learning before going online.

Usage:
    python bench/replay.py run --logs demo_data/ml/guardian_responses.jsonl
    python bench/replay.py report --output bench/reports/
    python bench/replay.py verify --expected bench/expected_outcomes.json

"Bevor ihr online lernt: Bandit 'spielt' historische Logs durch
und ihr checkt, ob Updates logisch sind."
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import copy

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.learning.bandit import (
    GuardianBandit, BanditContext, ToneVariant, SourceMixStrategy,
    BetaDistribution
)


@dataclass
class ReplayEvent:
    """A single replay event from logs."""
    response_id: str
    timestamp: str
    claim_type: List[str]
    risk_level: str
    tone_variant: str
    source_mix: str
    reward: Optional[float] = None
    metrics: Optional[Dict] = None


@dataclass
class ReplayResult:
    """Result of replaying a log file."""
    total_events: int = 0
    events_with_reward: int = 0
    events_skipped: int = 0

    # Bandit state changes
    initial_state: Dict = field(default_factory=dict)
    final_state: Dict = field(default_factory=dict)

    # Arm statistics
    arm_updates: Dict[str, int] = field(default_factory=dict)
    arm_rewards: Dict[str, List[float]] = field(default_factory=dict)

    # Sanity checks
    logical_updates: int = 0      # Updates that make sense
    suspicious_updates: int = 0   # Updates that seem wrong

    # Timeline
    reward_timeline: List[Tuple[str, float]] = field(default_factory=list)


class BanditReplay:
    """
    Replays historical logs through a fresh bandit instance.

    This allows you to:
    1. See how bandit would have learned from historical data
    2. Check if arm updates are logical
    3. Identify potential issues before online deployment
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.bandit = GuardianBandit()  # Fresh bandit
        self.result = ReplayResult()

    def load_logs(self, log_path: Path) -> List[ReplayEvent]:
        """Load events from JSONL log file."""
        events = []

        with open(log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())

                    # Handle different log formats
                    if 'response_id' in data:
                        event = ReplayEvent(
                            response_id=data.get('response_id', f'line_{line_num}'),
                            timestamp=data.get('timestamp', ''),
                            claim_type=data.get('claim_type', []),
                            risk_level=data.get('risk_level', 'medium'),
                            tone_variant=data.get('tone_variant', 'boundary_firm'),
                            source_mix=data.get('source_mix', 'balanced'),
                            reward=data.get('reward'),
                            metrics=data.get('metrics'),
                        )
                        events.append(event)

                except json.JSONDecodeError as e:
                    if self.verbose:
                        print(f"Warning: Skipping line {line_num}: {e}")

        print(f"Loaded {len(events)} events from {log_path}")
        return events

    def replay(self, events: List[ReplayEvent]) -> ReplayResult:
        """
        Replay events through bandit.

        Returns:
            ReplayResult with analysis
        """
        # Capture initial state
        self.result.initial_state = self._capture_state()
        self.result.total_events = len(events)

        for event in events:
            self._process_event(event)

        # Capture final state
        self.result.final_state = self._capture_state()

        return self.result

    def _process_event(self, event: ReplayEvent):
        """Process a single replay event."""
        # Skip if no reward
        if event.reward is None:
            self.result.events_skipped += 1
            return

        self.result.events_with_reward += 1

        # Create context
        context = BanditContext(
            claim_type=event.claim_type[0] if event.claim_type else 'unknown',
            risk_level=event.risk_level,
        )

        # Make decision (simulated)
        decision = self.bandit.make_decision(context)

        # Calculate what the reward would have been
        if event.metrics:
            reward = self.bandit.calculate_reward(event.metrics)
        else:
            reward = event.reward

        # Update bandit with actual reward
        self.bandit.update(decision.decision_id, {'reward': reward})

        # Track arm updates
        tone_key = event.tone_variant
        source_key = event.source_mix

        self.result.arm_updates[tone_key] = self.result.arm_updates.get(tone_key, 0) + 1
        self.result.arm_updates[source_key] = self.result.arm_updates.get(source_key, 0) + 1

        if tone_key not in self.result.arm_rewards:
            self.result.arm_rewards[tone_key] = []
        self.result.arm_rewards[tone_key].append(reward)

        if source_key not in self.result.arm_rewards:
            self.result.arm_rewards[source_key] = []
        self.result.arm_rewards[source_key].append(reward)

        # Track timeline
        self.result.reward_timeline.append((event.response_id[:8], reward))

        # Sanity check
        if self._is_logical_update(event, reward):
            self.result.logical_updates += 1
        else:
            self.result.suspicious_updates += 1
            if self.verbose:
                print(f"Suspicious: {event.response_id[:8]} reward={reward:.2f}")

    def _is_logical_update(self, event: ReplayEvent, reward: float) -> bool:
        """
        Check if an update is logical.

        Suspicious cases:
        - Very high reward but got reported
        - Very low reward but high engagement
        """
        if event.metrics:
            reports = event.metrics.get('reports', 0)
            likes = event.metrics.get('likes', 0)

            # High reward but got reported
            if reward > 0.7 and reports > 0:
                return False

            # Low reward but many likes
            if reward < 0.3 and likes > 100:
                return False

        return True

    def _capture_state(self) -> Dict:
        """Capture current bandit state."""
        return {
            'tone_arms': {
                arm.value: {
                    'alpha': dist.alpha,
                    'beta': dist.beta,
                    'mean': dist.mean()
                }
                for arm, dist in self.bandit.tone_arms.items()
            },
            'source_arms': {
                arm.value: {
                    'alpha': dist.alpha,
                    'beta': dist.beta,
                    'mean': dist.mean()
                }
                for arm, dist in self.bandit.source_arms.items()
            }
        }

    def generate_report(self) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 60,
            "BANDIT REPLAY REPORT",
            "=" * 60,
            "",
            f"Total events: {self.result.total_events}",
            f"Events with reward: {self.result.events_with_reward}",
            f"Events skipped: {self.result.events_skipped}",
            "",
            "SANITY CHECK:",
            f"  Logical updates: {self.result.logical_updates}",
            f"  Suspicious updates: {self.result.suspicious_updates}",
            f"  Suspicious rate: {self.result.suspicious_updates / max(1, self.result.events_with_reward) * 100:.1f}%",
            "",
            "ARM UPDATES:",
        ]

        for arm, count in sorted(self.result.arm_updates.items()):
            rewards = self.result.arm_rewards.get(arm, [])
            avg_reward = sum(rewards) / len(rewards) if rewards else 0
            lines.append(f"  {arm}: {count} updates, avg_reward={avg_reward:.3f}")

        lines.extend([
            "",
            "STATE CHANGE:",
            "",
            "Tone Arms (before -> after):",
        ])

        for arm in ['boundary_strict', 'boundary_firm', 'boundary_educational']:
            before = self.result.initial_state.get('tone_arms', {}).get(arm, {})
            after = self.result.final_state.get('tone_arms', {}).get(arm, {})
            lines.append(
                f"  {arm}: mean {before.get('mean', 0):.3f} -> {after.get('mean', 0):.3f}"
            )

        lines.extend([
            "",
            "Source Arms (before -> after):",
        ])

        for arm in ['institution_heavy', 'balanced', 'factcheck_heavy']:
            before = self.result.initial_state.get('source_arms', {}).get(arm, {})
            after = self.result.final_state.get('source_arms', {}).get(arm, {})
            lines.append(
                f"  {arm}: mean {before.get('mean', 0):.3f} -> {after.get('mean', 0):.3f}"
            )

        lines.extend([
            "",
            "=" * 60,
        ])

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Bandit Replay CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Run command
    run_parser = subparsers.add_parser('run', help='Replay logs through bandit')
    run_parser.add_argument('--logs', type=str, required=True, help='Path to JSONL log file')
    run_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate replay report')
    report_parser.add_argument('--logs', type=str, required=True, help='Path to JSONL log file')
    report_parser.add_argument('--output', type=str, help='Output directory for report')

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify against expected outcomes')
    verify_parser.add_argument('--logs', type=str, required=True, help='Path to JSONL log file')
    verify_parser.add_argument('--expected', type=str, required=True, help='Expected outcomes JSON')

    args = parser.parse_args()

    if args.command == 'run':
        replay = BanditReplay(verbose=args.verbose)
        events = replay.load_logs(Path(args.logs))
        result = replay.replay(events)
        print(replay.generate_report())

    elif args.command == 'report':
        replay = BanditReplay(verbose=True)
        events = replay.load_logs(Path(args.logs))
        result = replay.replay(events)
        report = replay.generate_report()

        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            report_path = output_dir / f"replay_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_path, 'w') as f:
                f.write(report)
            print(f"Report saved to {report_path}")
        else:
            print(report)

    elif args.command == 'verify':
        replay = BanditReplay()
        events = replay.load_logs(Path(args.logs))
        result = replay.replay(events)

        # Load expected outcomes
        with open(args.expected) as f:
            expected = json.load(f)

        # Compare
        passed = True
        for arm, expected_mean in expected.get('expected_means', {}).items():
            actual = result.final_state.get('tone_arms', {}).get(arm, {}).get('mean')
            if actual is None:
                actual = result.final_state.get('source_arms', {}).get(arm, {}).get('mean', 0)

            diff = abs(actual - expected_mean)
            status = "PASS" if diff < 0.1 else "FAIL"
            print(f"{arm}: expected={expected_mean:.3f}, actual={actual:.3f} [{status}]")
            if status == "FAIL":
                passed = False

        sys.exit(0 if passed else 1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
