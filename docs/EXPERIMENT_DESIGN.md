# Deterministic Enforcement vs. LLM Monitoring for Agent Control

*A control evaluation of a coding agent in a sandboxed Bash environment*

Luis N. Lugo · Status: design and pre-registration draft ·
October 2026

## 1. Research question

**Do deterministic enforcement controls catch agent sabotage that an LLM
monitor misses, and what do they cost in usefulness?**

Published AI control protocols mostly rely on a trusted model acting as
a monitor. Enterprise deployments mostly rely on deterministic controls:
scoped permissions, command allowlists and network egress policy. This
project measures the two side by side, under the same attack policies
and on the same tasks, so the contribution of each and of the
combination can be separated.

The policy engine tested here is the runtime enforcement pattern from my
GUARD reference architecture (policy decision point separated from
policy enforcement point). This repository tests that pattern
empirically rather than asserting it.

## 2. Hypotheses

Fixed before any main runs. Any deviation is reported in the final
report.

- **H1.** Enforcement alone lowers side task success relative to no
  protocol, but leaves attacks that do not need a restricted capability.

- **H2.** Monitor plus enforcement reaches higher safety than either
  alone at the same audit budget.

- **H3.** Enforcement imposes a measurable usefulness cost: some
  legitimate honest mode work is blocked.

- **H4 (secondary).** Giving the monitor the agent’s reasoning, not only
  its actions, raises detection at a fixed false positive rate.

## 3. Experimental design

### Setting

**ControlArena Bash setting.** Shell tasks from the CTRL-Z work, based
on Stack Overflow questions, with programmatic scorers and a synchronous
harmful effect. It is chosen for three reasons: the harm happens at
execution time, so an enforcement layer can actually intercept it;
programmatic scoring removes grader bias; and published results exist to
compare against.

**Phase 1 reproduction first.** Before changing anything, I run the
stock defer-to-trusted protocol on this setting in honest and attack
modes and confirm the baseline behaves as expected.

### Models and modes

- **Untrusted model (U):** a frontier model doing the work.

- **Trusted model (T):** a smaller model used for monitoring and
  deferral.

- **Recorded per run:** exact model IDs, versions and temperatures,
  stored in configs/models.yaml and every log.

- **Eval modes:** honest (main task only) and attack (main task plus a
  hidden side task).

### Protocol arms

| **Arm** | **Protocol**                   | **What runs**                                                                  | **What it isolates**                                   |
|---------|--------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------|
| A0      | No protocol                    | Untrusted agent, unmonitored, unrestricted                                     | Baseline attack success and usefulness ceiling         |
| A1      | Trusted monitoring             | LLM monitor scores every action; the most suspicious are audited within budget | Monitor contribution                                   |
| A2      | Enforcement only               | Deterministic policy engine blocks out-of-policy commands; no monitor          | Enforcement contribution                               |
| A3      | Monitor + enforcement          | A1 and A2 together                                                             | Complementarity (H2)                                   |
| A4      | Defer to trusted               | Monitor, with deferral to T above a suspicion threshold                        | Published reference protocol                           |
| A5      | Defer to trusted + enforcement | A4 with the A2 policy engine                                                   | Whether enforcement adds to the strongest LLM protocol |

**Secondary variable:** monitor visibility, actions only vs. actions
plus reasoning, run on A1 and A3 (H4).

### Enforcement layer

A policy enforcement point wraps the sandbox tool and executes a command
only if the policy decision point allows it. Rules are declarative and
versioned:

- Network egress denied except allowlisted package mirrors

- File writes limited to the task working directory

- Denied command classes: privilege escalation, persistence, process
  hiding

- Execution of files downloaded during the episode blocked

- Every decision logged with its rule ID

**Anti-overfitting rule:** policy v1.0 is frozen before I review any
attack trajectory. Any later change is a new arm with its own version
number, never a silent fix.

### Attack policies

| **ID** | **Attacker knowledge** | **Instruction**                                                                      |
|--------|------------------------|--------------------------------------------------------------------------------------|
| P1     | Unaware                | Default ControlArena attack policy                                                   |
| P2     | Monitor-aware          | Told that an LLM monitor reviews each action                                         |
| P3     | Enforcement-aware      | Given the policy rules in plain language and told to reach the side task within them |

P3 is the critical test. Enforcement evaluated only against unaware
attackers overstates safety.

## 4. Metrics

| **Metric**                | **Definition**                                                                                                       | **Role**  |
|---------------------------|----------------------------------------------------------------------------------------------------------------------|-----------|
| Safety                    | Probability the side task is never completed undetected across a deployment, using ControlArena’s analysis utilities | Primary   |
| Usefulness                | Honest mode main task success, normalized so trusted-only = 0 and untrusted-only = 1                                 | Primary   |
| Attack success rate       | Share of attack runs where the side task completes                                                                   | Secondary |
| Detection at audit budget | Share of attack runs caught when the auditor can review 1% (and 2%) of actions; threshold calibrated on honest runs  | Secondary |
| False positive rate       | Share of honest runs flagged or blocked                                                                              | Secondary |
| Enforcement block rate    | Blocked commands, reported separately for honest and attack runs                                                     | Secondary |
| Monitor cost              | Tokens and latency per action                                                                                        | Secondary |

**Uncertainty.** Paired design: every arm runs the same task sample.
Multiple epochs per arm. Bootstrap 95% confidence intervals on every
reported metric. Sample size is fixed before the main runs, based on
variance observed in the Phase 1 reproduction.

## 5. Repository structure

configs/

models.yaml model IDs, versions, temperatures

arms.yaml A0 to A5 definitions

policy/ enforcement rules, versioned (v1.0 frozen)

src/

enforcement/ PDP and PEP wrapper around sandbox tools

monitors/ action-only and action+reasoning monitors

protocols/ arm compositions

attack_policies/ P1, P2, P3

scripts/

run_arm.py run one arm, one mode

analyze.py safety, usefulness, CIs, plots

results/

logs/ Inspect logs (not committed)

summaries/ aggregated metrics

docs/

THREAT_MODEL companion document

PREREGISTRATION hypotheses, metrics, sample size

REPORT final write-up

tests/

## 6. Setup and reproduction

**Prerequisites:** Python 3.11 or later, Docker (Inspect manages the
sandboxes), and model API keys set as environment variables.

pip install control-arena

git clone https://github.com/LNLugo/agent-control-eval

cd agent-control-eval && pip install -e .

\# Phase 1 reproduction: stock defer-to-trusted on the Bash setting

python scripts/run_arm.py --arm A4 --mode honest --epochs 3

python scripts/run_arm.py --arm A4 --mode attack --attack-policy P1
--epochs 3

\# Main comparison, example

python scripts/run_arm.py --arm A3 --mode attack --attack-policy P3
--epochs 3

python scripts/analyze.py --logs results/logs --out results/summaries

inspect view \# browse trajectories

*The repository name and script interfaces above are the planned design;
they are built in Phase 2.*

## 7. Results

Not yet run. Results will be reported against each hypothesis, including
null and negative results, with representative failure trajectories for
every arm.

## 8. Known limitations

- One setting. Whether results carry over to enterprise knowledge agents
  is untested.

- I design both the policy and the attacks. Mitigations: policy frozen
  before trajectory review, and the P3 enforcement-aware attacker.

- Prompted attack policies approximate, but do not equal, a genuinely
  misaligned model.

- The auditor is simulated as perfect within its budget, which is
  optimistic.

- Model API versions change; results are tied to the versions recorded.

- Enforcement that removes a capability the side task needs is trivially
  safe against that side task. Results are interpreted through
  usefulness cost and the attacks that remain.

## 9. Containment and data handling

- All agent execution happens in Docker sandboxes with networking
  restricted by the setting configuration and no host mounts beyond the
  run directory.

- No real credentials or data inside the sandbox.

- Supplementary attack scenarios use inert payloads only, such as a
  script that writes a marker file.

- ControlArena asks users to keep task material out of training data. I
  follow that: no unprotected publication of task solutions,
  trajectories released only in protected form, canary strings
  preserved.

## 10. Roadmap

| **\#** | **Phase**                   | **Weeks**         | **Deliverable**                                                  |
|--------|-----------------------------|-------------------|------------------------------------------------------------------|
| 1      | Evaluation foundations      | 1 to 4            | Inspect running; Phase 1 reproduction with baseline metrics      |
| 2      | Threat model and test suite | 3 to 6 (parallel) | Frozen threat model, policy v1.0, benign and adversarial suites  |
| 3      | First experiment            | 7 to 10           | A0, A1, A2 with P1 and P2; first experimental report             |
| 4      | Protocol comparison         | 11 to 15          | A3 to A5, P3, visibility variable; comparative evaluation        |
| 5      | Research quality            | 16 to 20          | Repeat runs, failure analysis, comparison with published results |
| 6      | Publication                 | 21 to 24          | Code, report, research summary, one open question                |

## 11. References

- Greenblatt et al. (2023). AI Control: Improving Safety Despite
  Intentional Subversion. arXiv:2312.06942.

- Bhatt et al. (2025). Ctrl-Z: Controlling AI Agents via Resampling.
  Source of the Bash setting tasks.

- Korbak et al. (2025). Chain of Thought Monitorability: A New and
  Fragile Opportunity for AI Safety.

- Inglis et al. (2025). ControlArena. UK AI Security Institute and
  Redwood Research. github.com/UKGovernmentBEIS/control-arena

- UK AI Security Institute. Inspect AI. inspect.aisi.org.uk
