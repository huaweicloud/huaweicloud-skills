"""
Evaluator function template - Python (minimal workable version)

Constraints:
- Must be a parameterless `def evaluate()`; the filename must exactly match
  the value passed to `CreateEvolveTask --evaluator_file`
- `evaluate()` returns a single float; larger / smaller is determined by
  `--evaluator_parameter.smaller_better`

The platform imports the candidate code and the candidate function, so this
function only needs to:
1. Prepare the test data
2. Call the function under evaluation directly
3. Return a float score
"""


def evaluate():
    import time
    import random

    # 1. Prepare the test data
    test_data = [random.randint(1, 10_000_000) for _ in range(100_000)]

    # 2. Call the function under evaluation (the platform auto-injects
    #    the function being evolved, `sort_algorithm`)
    start = time.time()
    sort_algorithm(test_data)
    elapsed = time.time() - start

    # 3. Return the score (e.g. elapsed time; interpreted with
    #    `smaller_better=true`)
    return elapsed
