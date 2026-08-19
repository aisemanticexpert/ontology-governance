# Junior Developer Exercise

1. Run `python scripts/govern.py` and confirm PASS.
2. Run `python scripts/watch.py` in terminal A.
3. Open `ontology/ins/policy.ttl`.
4. Add a new class under the policy namespace, save the file, and observe terminal A.
5. Open `reports/latest/change-report.md`.
6. If validation passes, create a PR. GitHub Actions runs the same gate.
7. A steward reviews semantic impact and approves.
8. A release operator runs `scripts/release.py` (or the enterprise release pipeline does the equivalent).
9. Never edit anything under `releases/`; those snapshots are immutable.
10. Never add `_v2` or a date to a class IRI. The stable term survives multiple ontology releases.
