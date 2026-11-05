# Contributing to note-drift

Thanks for your interest in improving note-drift. Bug reports, ideas, documentation fixes and code are all welcome.

## Getting set up

```bash
git clone https://github.com/kishoren18-hue/note-drift
cd note-drift
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install        # optional: lint on every commit
```

Run the checks CI runs:

```bash
ruff check .
pytest --cov=note_drift
```

## Making a change

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Create a branch, make the change, and add or update tests.
3. Keep pull requests focused on one thing; describe what changed and why.
4. Make sure the checks above pass, then open a pull request.

Good tests matter more than clever code here. A bug fix should come with a test that fails without the fix.

## Ideas to start with

* Add an RxNorm-backed vocabulary loader
* Detect route changes (oral vs IV) for medications
* Add more synthetic note/summary pairs to the benchmark

## Changes that affect safety

This tool works with medical information. A change that could make it miss an error,
or report something wrong with confidence, needs:

* a test that reproduces the case,
* a note in the pull request describing what could go wrong,
* a preference for flagging or abstaining over guessing when the input is ambiguous.

Never add real patient data to the repository, including in tests or issues. Use synthetic examples.

## Code of conduct

By participating you agree to follow the [code of conduct](CODE_OF_CONDUCT.md).
