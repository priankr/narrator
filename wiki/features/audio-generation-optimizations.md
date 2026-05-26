# Audio Generation Optimizations

Branch: `usability-improvements-2`

One change: parallel paragraph synthesis on the default (`cache_segments=False`) path using `ThreadPoolExecutor`.

---

## Overview

Synthesis of a long post is strictly sequential — each paragraph blocks until the previous one completes. With 42 paragraphs at ~60–70 seconds each, a 20-minute post takes 45+ minutes to generate.

The Kokoro ONNX model releases the Python GIL during NumPy inference, so threads can genuinely run concurrently. With 4 workers, expected speedup is 2–4×, bringing a 45-min run to roughly 12–20 min.

**Scope constraint:** Parallelism applies only to the `cache_segments=False` path (the default). The `cache_segments=True` path (used with `--cache-segments`) remains strictly sequential — its write-per-segment manifest contract cannot be safely parallelized without sacrificing incremental checkpoint granularity, which is the entire purpose of that path.

---

## 1. Parallel Synthesis (`--workers N`)

### What changes

**`tts/kokoro_provider.py`**

`_ensure_loaded()` has a thread-safety bug today: two threads can both observe `self._model is None` and both attempt to initialize the model. Fix: add a `threading.Lock` to `KokoroProvider.__init__` and acquire it around the `None` check in `_ensure_loaded()`.

```python
def __init__(self, model_path=None, voices_path=None):
    ...
    self._load_lock = threading.Lock()

def _ensure_loaded(self) -> None:
    with self._load_lock:
        if self._model is not None:
            return
        # ... existing load logic
```

This fix is a correctness requirement independent of whether parallelism is used — ship it before enabling parallel synthesis.

**`pipeline/synthesizer.py`**

Add `workers: int = 4` to the `synthesize()` signature.

In the `cache_segments=False` branch only:

1. Pre-filter empty paragraphs while preserving their original 1-based indices. This is required because `ThreadPoolExecutor` must receive only non-empty paragraphs, but progress events must report the correct index relative to the full paragraph list.
2. Submit all non-empty paragraphs to `ThreadPoolExecutor(max_workers=workers)`.
3. Collect results via `executor.map()` — this yields results in submission order regardless of completion order, so assembly is correct without any sorting.
4. After collection, emit `segment_done` progress events in paragraph order and assemble as before.

The `cache_segments=True` branch is **unchanged** — sequential, no manifest locking needed.

**`narrator.py`**

Add `--workers` flag to the `generate` command:

```python
@click.option("--workers", default=4, type=int, show_default=True,
              help="Number of synthesis threads. Only applies when --cache-segments is not set.")
```

Pass `workers` through to `synthesize()`. Add it to the dry-run output:

```python
"workers": workers,
```

### Files to edit

| File | Change |
|---|---|
| `tts/kokoro_provider.py` | Add `threading.Lock` to `__init__`; acquire in `_ensure_loaded()` |
| `pipeline/synthesizer.py` | Add `workers: int = 4` param; parallelize `cache_segments=False` branch with `ThreadPoolExecutor` |
| `narrator.py` | Add `--workers` flag to `generate`; pass to `synthesize()`; add `"workers"` to dry-run output |
| `wiki/agent-guidelines.md` | §1.2: add `--workers` to generate options table; §1.3: note `segment_done` ordering when workers > 1, update dry-run schema; §2.2: update synthesizer contract |
| `AGENTS.md` | Add `--workers` to key generate flags table; note `--cache-segments` does not benefit from parallelism |
| `wiki/getting-started.md` | Add performance note |
| `wiki/configuration.md` | Add `--workers` to generate CLI reference table |
| `tests/test_synthesizer_resume.py` | Add new test cases (see below) |

### New tests (`tests/test_synthesizer_resume.py`)

| Test | What it asserts |
|---|---|
| `test_parallel_run_preserves_paragraph_order` | Body WAV is assembled from results in paragraph order regardless of which thread completes first |
| `test_parallel_run_calls_provider_n_times` | Provider is called exactly once per non-empty paragraph |
| `test_parallel_run_skips_empty_paragraphs` | Empty paragraphs produce no provider call and no gap in assembled output |
| `test_workers_1_matches_default_output` | `workers=1` produces the same body WAV as `workers=4` (order is deterministic) |
| `test_provider_load_lock_prevents_double_init` | Concurrent calls to `_ensure_loaded()` result in exactly one model initialization |

### What does NOT change

- `cache_segments=True` path — sequential, unchanged; no manifest locking required
- `mix()`, `encode()` — receive the same `Path` contract; untouched
- `--progress` event **schema** — `segment_done` fields are unchanged; however, when `workers > 1` events are emitted in paragraph order after all futures resolve, not one-by-one as each completes (see agent-guidelines.md §1.3)
- Exit codes (0/1)
- `TTSProvider` abstract interface — the lock is internal to `KokoroProvider`

---

## Implementation Order

1. `tts/kokoro_provider.py` — add `threading.Lock`, fix `_ensure_loaded()`
2. `pipeline/synthesizer.py` — add `workers` param, parallelize `cache_segments=False` branch
3. `narrator.py` — add `--workers` flag, pass through, add to dry-run output
4. `tests/test_synthesizer_resume.py` — add the five new test cases
5. `wiki/agent-guidelines.md` — §1.2 generate table, §1.3 progress events and dry-run schema, §2.2 synthesizer contract
6. `AGENTS.md` — add `--workers`, note about `--cache-segments`
7. `wiki/getting-started.md` — add performance note
8. `wiki/configuration.md` — add `--workers` to CLI reference
