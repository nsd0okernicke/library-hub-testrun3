# Quality Gate Audit — LibraryHub (run5)

**This run:** `library-hub-testrun3` @ `19c4f83` (branch `run1`) · 102 commits · audited 2026-09-03
**Prior runs:** `library-hub-testrun` @ `3857b00` (run3) · `library-hub-testrun2` @ `a3bd6ff` (run4)
**Scope:** the quality-gate system and pipeline mechanics, not the LibraryHub domain.

Every figure below was produced by re-running the toolchain against this repo, including a full-suite
run from a clean detached checkout and an independent reproduction of the architect's mutation score.

---

## Verdict

| | run3 | run4 | run5 | |
|---|---|---|---|---|
| **Code artifact** | 8.5 | 8.0 | **8.5 / 10** | Best artifact of the three. Real infrastructure is back. |
| **Quality-gate system** | 5.0 | 6.0 | **7.0 / 10** | The machinery is now real. It has still never been switched on. |

Three things happened this run that had not happened before:

1. **The full suite passes from a genuinely clean checkout** — I detached `19c4f83` into a fresh
   worktree and ran it there: **482 passed, 1 skipped, 0 failed** in 61 s, against two real Postgres
   containers.
2. **A quality claim was independently reproduced for the first time.** The architect's cat-6 handoff
   says "mutation 91.7%". I ran the committed `mutation-cat6.toml` myself in a scratch worktree:
   12 mutants, 1 survivor, **91.67% kill rate**. Exact match. Across run3 and run4 no mutation figure
   was checkable at all.
3. **The CI workflow contains real commands.** run4's twelve `echo "run lint gate"` stubs are gone,
   replaced by `ruff check`, `mypy catalog loans`, three pytest jobs, `lint-imports`, `interrogate`,
   `bandit`, `radon`, and a cosmic-ray job.

And one thing did not happen: **CI has still never run.** The remote is configured but empty.

```
$ git remote -v
origin  https://github.com/nsd0okernicke/library-hub-testrun3.git (fetch)

$ git ls-remote --heads origin
(nothing)

$ gh repo view nsd0okernicke/library-hub-testrun3 --json isEmpty
{"isEmpty": true}

$ gh run list          →  0 workflow runs
$ git branch -vv       →  main  29d4d8f [origin/main: gone] init
```

102 commits of work sit on local `run1`. Nothing has ever been pushed. You built the verifier and
did not plug it in — so for the third run running, every gate result in this repo is still the word
of the agent that ran it.

---

## Baseline Metrics — three runs side by side

| Gate | Command | run3 `3857b00` | run4 `a3bd6ff` | run5 `19c4f83` |
|---|---|---|---|---|
| Type check (bare) | `uv run mypy` | 0 issues / 50 files, strict | **command fails** | **command fails** |
| Type check (explicit) | `uv run mypy catalog loans` | — | 0 / 39, default mode | **0 / 55, strict** ▲ |
| Lint | `uv run ruff check .` | 0 findings | 0 findings | 0 findings |
| Format | `ruff format --check` | — | — | **125 files clean** ▲ new |
| Layering | `uv run lint-imports` | 2 forbidden, kept | 4 forbidden, kept | **2 `layers`, kept** ▲ kind |
| Complexity | `radon cc … -n C` | 0 above B | 0 above B | 0 above B |
| Maintainability | `radon mi … -n B` | all A | all A | all A |
| Doc coverage | `uv run interrogate` | 94.8% (min 80) | 96.4% (**min 90**) | 95.6% (min 80) ▼ |
| Coverage (full) | `pytest --cov` | 99.13% (**min 90 enforced**) | 98.90% (no min) | 98.79% (**no min**) ▼ |
| Coverage (as CI measures it) | unit + property only | — | — | **92.86%** |
| Dependency audit | `uv run pip-audit` | 0 vulns | 0 vulns | 0 vulns |
| SAST | `bandit -r catalog loans` | 1 medium (B104) | 0 findings | 0 findings |
| Unit | `pytest tests/unit -q` | 356 passed | 285 passed | 287 passed |
| Property | `pytest tests/property -q` | 61 passed | 44 passed | **5 collection ERRORS** ▼ |
| Property (`python -m pytest`) | CI's invocation | — | — | 55 passed, 1 skipped |
| Acceptance | `pytest tests/acceptance -q` | 150 pass, **2 FAILED** | 118 pass (in-memory, 1.6 s) | **140 pass (real PG, 52 s)** ▲ |
| Clean-checkout full run | detached worktree @ HEAD | not performed | 447 passed | **482 passed, 1 skipped** |
| Mutation | committed config | none | none | **committed + reproduced 91.67%** ▲▲ |
| Mutation score file | versioned | none | none | none |
| CI | `.github/workflows/` | absent | stub, never ran | **real, never ran** |

| | run3 | run4 | run5 |
|---|---|---|---|
| Source files | 49 | 39 | **55** |
| Infrastructure files | 23 | **12** | **23** |
| Statements | 919 | 818 | 916 |
| Tests | 569 (2 red) | 447 | **483 (0 red)** |
| Persistence | Postgres | `dict` | **Postgres ×2 containers** |

---

## What is now genuinely fixed

### ✅ Evidence integrity — solid for the second run

- Root tree clean, all 5 worktrees clean.
- 72 handoff messages, **zero** with a non-null `error` (run3 had two silent squash failures).
- 60 messages carry a `Commit:` line. I resolved every one: **60 real commits, 60 ancestors of HEAD,
  0 problems.**
- `reports/junit.xml` reports `tests="483" failures="0" skipped="1"`. I measured 482 passed + 1
  skipped. Exact match, and every test name in it exists at HEAD.

### ✅ Mutation is reproducible — the biggest single win

Three configs are committed (`mutation-catalog.toml`, `mutation-loans.toml`, `mutation-cat6.toml`),
and they are unusually well documented — the catalog one explains *why* `catalog/domain/ports.py` is
excluded and why the glob needs `**/*.py` rather than `*`. That is real engineering, not boilerplate.

I verified it end to end in a scratch worktree:

```
cosmic-ray init mutation-cat6.toml cat6.sqlite   →  total jobs: 12
cosmic-ray exec mutation-cat6.toml cat6.sqlite   →  complete: 12 (100.00%)
cr-rate cat6.sqlite                              →  8.33   (= 91.67% killed)
architect's cat-6 handoff                        →  "mutation 91.7%"
```

**A pipeline claim was checked against reality and held.** That is the thing the previous two audits
could not do once.

### ✅ Real infrastructure is back, and better than run3

`sqlalchemy[asyncio]`, `asyncpg` and `testcontainers` are dependencies again; 23 infrastructure files
against run4's 12. The acceptance conftest spins **two separate `postgres:16-alpine` containers** —
one per bounded context — which is the architecturally correct choice for two microservices and
better than run3's arrangement. Acceptance takes 52 s and proves something.

### ✅ mypy strict restored

`[tool.mypy] strict = true` is back after run4 dropped it entirely. 0 issues across 55 files.

### ✅ CI is real code

Twelve jobs with actual commands. `ruff format --check` is a new gate that did not exist in either
prior run.

---

## Deep findings

### 🔴 1. CRITICAL — The verifier exists and has never verified anything

This is now the third consecutive run in which no independent process has checked a single gate.
run3 had no CI. run4 had a CI file full of `echo`. run5 has a real CI file, a real GitHub repo, a
valid token with `workflow` scope — and an **empty remote with zero pushes and zero runs**.

The remaining distance is one `git push`. Until that happens, the improvement is architectural
rather than actual, and everything below stays true.

### 🔴 2. CRITICAL — The CI mutation job cannot run, by construction

```yaml
# .github/workflows/ci.yml:172
cosmic-ray init tests/mutation/catalog-domains.toml .kiln-mutation/catalog.sqlite
```

```
$ ls tests/mutation
ls: cannot access 'tests/mutation': No such file or directory
```

The committed configs are at the repo root as `mutation-catalog.toml` / `mutation-loans.toml`. CI
looks for `tests/mutation/catalog-domains.toml`. `cosmic-ray init` is not wrapped in `|| true`, so
the job fails immediately on the first push.

The origin of this mismatch is instructive, and I traced it: **run4's fixes were made in the run4
project, and only some of them propagated to the template that seeds new runs.** In
`library-hub-testrun2`, commit `b2f61d6 "finalized"` (2026-09-02 19:49, right after the run4 audit)
added `tests/mutation/catalog-domains.toml`, `tests/mutation/loans-domains.toml`,
`.mutation-scores.json`, the real `ci.yml`, and hardened two role files. Of those, **only `ci.yml`
reached run5.** The toml files it references did not; the scores file did not; the role hardening did
not. run5's mutation configs were written from scratch by the agents (commit `752cabd`, cat-3) at a
different path, and nothing reconciled the two.

**Gate to add:** whatever `ci.yml` references must exist — a trivial path-existence check in
`identity-checks` would catch this class permanently. And decide deliberately whether project fixes
flow back into `kiln/src/kiln/resources/` and `kiln/examples/library-hub/`, because right now some do
and some don't, silently.

### 🔴 3. CRITICAL — Mutation configs are pinned to one machine

```toml
test-command = "C:/projekte/agentic-coding/library-hub-testrun3/.venv/Scripts/python -m pytest tests/unit -x -q"
```

All three configs hardcode an absolute Windows path into this specific project directory. They are
reproducible on your laptop — I proved that — and nowhere else. On `ubuntu-latest` the CI mutation
job would fail even with the path issue in finding 2 fixed. A future run5-equivalent audit on another
checkout could not reproduce these scores.

**Gate to add:** `test-command = "python -m pytest tests/unit -x -q"`. The interpreter should come
from the environment, not the config.

### 🟠 4. HIGH — Four of twelve CI jobs can never fail

Even once CI runs, a third of it is decorative:

| Job | Why it cannot fail |
|---|---|
| `sast` | `bandit -r catalog loans -f sarif -o bandit.sarif \|\| true` |
| `complexity` | `radon cc … \|\| true` **and** `radon mi … \|\| true` |
| `baseline-check` | prints "No baseline file committed" and exits 0 |
| `identity-checks` | asserts a clean tree *immediately after `actions/checkout`* — a tautology |

The clean-tree assertion is the one worth dwelling on. It was written to catch run3's real defect
(gate results measured on a dirty worktree), but placed in CI it checks a tree git just created. It
can only ever pass. The check needs to run **where the agent works** — in the role worktree, at
handoff time — not on a runner that starts from a pristine clone.

`.kiln/test-baseline.txt` still does not exist, so the baseline-lock recommendation from run3 remains
unimplemented across three runs.

### 🟠 5. HIGH — The coverage floor has now been missing for three runs

run3 enforced `fail_under = 90`. run4 dropped it. run5 still has no `[tool.coverage]` section, and
CI's coverage job has no `--cov-fail-under`. Coverage is measured and uploaded as an artifact;
nothing fails on a drop.

Worse, **the number CI would report is not the number the handoffs quote.** CI's coverage job runs
`tests/unit/ tests/property/` only:

```
CI's invocation (unit + property):  92.86%
full suite (incl. acceptance):      98.79%
```

A 90% floor applied to CI's own command would leave under three points of headroom, not nine.

The root cause is worth naming: **`pyproject.toml` is agent-authored, and re-derived from scratch
every run** (run5's was written in commits `752cabd` and `9dc0ddd`). run4's human-added
`[tool.coverage.run] fail_under = 90` and `[tool.mypy] files = [...]` were never going to survive,
because the agents rewrite that file. Gate thresholds currently live in an artifact under no one's
control.

**Gate to add:** move thresholds somewhere the agents do not regenerate, or add a committed test that
asserts they are present. A five-line `test_gate_config.py` checking for `fail_under` and
`strict = true` would have caught both the run4 and run5 regressions.

### 🟠 6. HIGH — The escape hatches regressed to the permissive wording

After the run4 audit you hardened them in `library-hub-testrun2` (commit `b2f61d6`):

> "Acceptance is the primary spec-conformance gate. If infrastructure tests cannot run locally, note
> the gap in the handoff but **do not skip by default**."
> "Validate correctness by **running the acceptance suite** — all scenarios must pass before handoff."

run5 shipped with the old text, because the edit was made in the project copy and the framework
template still carries the original:

```
kiln/src/kiln/resources/project/roles/architect.md:56
  **Skip this step if container startup exceeds the provider's tool timeout.**
  … Validate step definitions by inspection instead.

library-hub-testrun3/kiln/project/roles/coder.md:62
  Skip running the full acceptance test suite if container startup exceeds the tool timeout.
```

`architect.md:35` — "**No relevant files → skip all gates, just hand off**" — is unchanged across all
three runs. There are still no skip records, no reason codes, and no skip budget.

This is the same propagation failure as finding 2, and it is the most important process lesson of
this run: **you fixed two things in run4 and both fixes evaporated, because the place you fixed them
is not the place new runs are born from.**

### 🟡 7. MEDIUM — A property test is dead and reports as a skip

```python
# tests/property/loans/application/test_return_book_properties.py:39
@given(_DATES, _STATUSES)                    # _STATUSES = st.sampled_from(list(LoanStatus))
async def test_a_non_active_return_is_refused_without_side_effects(requested_on, status):
    if status is LoanStatus.ACTIVE:
        pytest.skip("ACTIVE loans are returned, not refused")
```

`pytest.skip()` inside a Hypothesis `@given` aborts the **entire test** the first time ACTIVE is
generated — which is immediately, since `LoanStatus` has few members. The property never validates
anything. The correct construct is `hypothesis.assume(status is not LoanStatus.ACTIVE)`, and the
codebase uses `assume` correctly exactly once elsewhere
(`tests/property/catalog/domain/test_book_properties.py:50`).

It surfaces as the `1 skipped` in every run and nothing looks at it. No gate fails on skipped tests.

### 🟡 8. MEDIUM — A live mutation survivor above the threshold went unexamined

The survivor I reproduced is not equivalent:

```diff
--- catalog/application/increase_book_stock.py
-@dataclass(frozen=True)
+@dataclass(frozen=False)
 class IncreaseBookStockCommand:
```

Nothing asserts that the command object is immutable. This is precisely the survivor class the
architect *did* kill in earlier cycles — run4's cat-2 handoff reads "added `BookAvailability` freeze
test", and loan-4's reads "added `BookReturned` freeze test". Here the score was 91.7%, the gate
threshold is 80%, so the run passed and the survivor was neither killed nor documented.

**The mutation gate is a threshold, not a ratchet.** Anything above the line is invisible, so
identical defects get fixed or ignored depending on where the percentage lands.

### 🟡 9. MEDIUM — A missing `__init__.py` breaks the property suite in isolation

```
$ uv run pytest tests/property -q
ModuleNotFoundError: No module named 'tests'
5 errors in 1.03s
```

`tests/` has 18 `__init__.py` files across 19 package directories. The missing one is
`tests/property/catalog/application/__init__.py` — exactly the directory whose five modules fail to
import.

It is masked because `python -m pytest` (CI's form, and the agents' form) prepends the CWD to
`sys.path`, while bare `pytest` does not. So the same suite passes or dies depending on how it is
invoked, and nobody has noticed because everyone happens to invoke it the working way. The full-suite
run also masks it.

### 🟡 10. MEDIUM — The messaging seam is still unproven (unchanged across three runs)

The database seam is now genuinely tested — two real Postgres containers. The **event** seam is not.
`loans/infrastructure/events.py` still exports only `InMemoryEventPublisher`, the acceptance conftest
wires that stub, and `testcontainers[postgres,rabbitmq]` is a declared dependency with no RabbitMQ
container anywhere. `catalog/infrastructure/messaging/book_returned_consumer.py` is exercised only by
a unit test that calls it directly.

So `BookReturned` never crosses a broker in any test. Still no migration tooling either.

### 🟢 11. LOW — `nul` and the report stamp, both unchanged

- The Windows reserved-filename artefact is back (3.6 KB of `docker info` output this time) and still
  suppressed by an uncommitted line in `.git/info/exclude`, which does not survive a clone.
- `reports/` is still gitignored and `reports/junit.xml` still carries no commit SHA. The provenance
  chain works through `messages.db`, not through the artifacts themselves.

---

## Checklist across all three runs

| | Target | run3 | run4 | run5 |
|---|---|---|---|---|
| 1 | Acceptance green on HEAD | ❌ 2 red, 95 commits | ✅ | ✅ **482 pass, clean checkout, real PG** |
| 2 | Reports carry a SHA that is an ancestor of HEAD | ❌ | ⚠️ via handoffs | ⚠️ via handoffs (60/60 verified) |
| 3 | All worktrees clean | ❌ live mutant | ✅ | ✅ root clean too |
| 4 | CI present and passing on role branches | ❌ absent | ❌ stubbed | ⚠️ **real, never pushed** |
| 5 | Mutation config committed | ❌ | ❌ | ✅ **and independently reproduced** |
| 5b | Mutation scores in a versioned file | ❌ | ❌ | ❌ |
| 6 | Gate commands in committed scripts | ❌ | ❌ | ⚠️ in `ci.yml`, no `scripts/` |
| 7 | Skip records for any gate not run | ❌ | ❌ | ❌ **hatches regressed** |
| 8 | One test over the real event path | ❌ | ❌ | ❌ (DB seam ✅, broker seam ❌) |
| 9 | Coverage floor enforced | ✅ `fail_under=90` | ❌ | ❌ |

**Trajectory: 1 pass → 2 passes → 4 passes and 3 partials.** Real movement, three runs running.

---

## What to do next, in order

1. **`git push -u origin run1`.** Everything else on this list is second. You have a real workflow, a
   real repo and a valid token; the gap between "has CI" and "is verified" is one command. Expect the
   mutation job to fail on the first run for the reasons in findings 2 and 3 — that failure *is* the
   value.

2. **Fix the two things that will make CI fail, before or right after that push.** Move the mutation
   configs to `tests/mutation/{catalog,loans}-domains.toml` (or repoint `ci.yml`), and replace the
   hardcoded `C:/projekte/…/.venv/Scripts/python` with `python`.

3. **Decide where fixes live.** This run lost the role hardening and the mutation configs because they
   were fixed in `library-hub-testrun2` rather than in `kiln/src/kiln/resources/` and
   `kiln/examples/library-hub/`. Pick one direction and make it a rule, or the next run will lose the
   next batch of fixes the same way.

4. **Put the gate thresholds beyond the agents' reach.** `pyproject.toml` is regenerated every run,
   which is why `fail_under` has now been missing twice and `mypy files=` twice. Either move the
   thresholds out of it, or add `tests/test_gate_config.py` asserting `fail_under >= 90` and
   `[tool.mypy] strict = true` — a five-line test that turns two recurring silent regressions into a
   red build.

5. **Make the four decorative CI jobs able to fail.** Drop the `|| true` from `sast` and `complexity`,
   make `baseline-check` exit 1 when the file is absent, and move the clean-tree assertion out of CI
   into the handoff skill where a dirty tree is actually possible.

6. **Turn mutation into a ratchet.** `.mutation-scores.json` already exists in run4's tree with the
   right shape — carry it forward, write real scores into it, and fail when a score drops. Then the
   `frozen=True` survivor in finding 8 becomes visible instead of rounding away above the threshold.

7. **Fix the two test defects.** `assume()` instead of `pytest.skip()` in the return-book property,
   and add `tests/property/catalog/application/__init__.py`. Then make one gate fail on unexpected
   skips, so a dead property cannot hide as `1 skipped` again.

8. **One test over a real broker,** or a consumer-driven contract test on the `BookReturned` schema.
   Unchanged priority for three runs.

---

## For the record: the code

At 8.5 this is the best artifact of the three runs, and it earns it on substance rather than on
being easier to please:

- **Two Postgres containers, one per bounded context** — the correct microservice test topology, and
  better than run3's shared arrangement.
- **`layers` contracts instead of `forbidden` ones.** Two contracts now enforce the full ordering
  `infrastructure → application → domain` in each context, which subsumes and exceeds run4's four
  pairwise forbidden rules.
- **`ruff format --check` clean across 125 files**, mypy strict clean across 55, zero bandit findings,
  zero complexity or maintainability warnings, 98.79% coverage, 95.6% docstrings.
- **Mutation configs that explain their own exclusions**, including a subtle cosmic-ray globbing
  footgun (`catalog/infrastructure/*` silently excludes nothing; you need `**/*.py`). That comment
  saved a future reader a genuinely bad afternoon.

Against that: three small test-quality defects that no gate caught — the dead property test, the
missing `__init__.py`, and the unaddressed immutability survivor. None is serious. All three are
exactly the kind of thing a second opinion catches and self-reporting does not.

---

## Bottom line

run4 fixed the pipeline's honesty. run5 built the pipeline's machinery — real CI, reproducible
mutation, real infrastructure — and for the first time in three audits I could take a claim the
system made about itself, run it independently, and watch it come out right to two decimal places.

What run5 also demonstrates is why that machinery has to be switched on and has to live upstream. Two
of the fixes you made after the run4 audit — the hardened escape hatches and the mutation config
paths — did not survive into this run, because they were made in the run4 project rather than in the
template new runs are seeded from. A third, the coverage floor, was overwritten by the agents
regenerating `pyproject.toml`. Nothing detected any of the three, because the only process that could
have detected them has never executed.

You are one `git push` from closing the loop that has been open since run3.
