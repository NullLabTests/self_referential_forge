# EMERGENCE_BACKLOG

## Active
- [x] Single-file mutation loop working (benchmarks/benchmark_runner.py)
- [ ] Randomize file target selection — unlock multi-file evolution
- [ ] Cross-file recombination operator — swap functions between files
- [ ] Self-target orchestator.py — evolve the evolution loop itself
- [ ] Population diversity scoring — prevent monoculture

## High Novelty
- [ ] Operator genealogy tracking — trace which operators produce which descendants
- [ ] Self-discovery of new operators via `_evolve_operator` meta-mutation
- [ ] Fitness landscape visualization in dashboard
- [ ] Recursive self-improvement: forge modifies its own mutation rate adaptation
- [ ] Cross-file function transplant: move a function from one file to another
- [ ] Emergent behavior detection: log when unexpected state transitions occur
- [ ] Chimera components: combine source from two different champions into one file

## Icebox
- [ ] Neural network-guided operator selection (replace weighted random)
- [ ] Automated rollback when fitness drops below threshold
- [ ] Self-modification of safety policy (tier adjustments based on track record)
- [ ] Archive diffs instead of full snapshots
- [ ] Docker sandbox for full isolation
- [ ] Parallel population islands with migration
