"""
Algorithm source file template - Python (minimal workable version)

Constraints:
- Wrap the entire function to evolve (def signature + function body) with
  # EVOLVE_START / # EVOLVE_END markers
- The function name must exactly match `CreateEvolveTask --algorithm_func_name`
- Outside the markers: keep normal imports / helper functions
- The markers MUST use `#` (Python single-line comment), not `//`
"""

from typing import List

# EVOLVE_START
def sort_algorithm(arr: List[int]) -> List[int]:
    """
    Sort a 1D list in ascending order.
    """
    return sorted(arr)
# EVOLVE_END
