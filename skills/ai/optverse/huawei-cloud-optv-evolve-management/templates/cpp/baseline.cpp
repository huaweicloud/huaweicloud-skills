// baseline.cpp - C++ baseline command source
//
// Same protocol as evaluator.cpp:
//   1. Compiles to an executable command (e.g. build/evaluate_baseline)
//   2. When invoked, prints the score (a single float) on its own line to stdout
//   3. `evaluator_baseline_func_name` in `CreateEvolveTask` points to that command
//
// The evaluator and baseline can be the same command (e.g. sharing `evaluate`
// with the same arguments); the evolution platform distinguishes them by
// swapping out the algorithm source file under evolution.

#include <cstdio>

int main() {
    // TODO: implement the local baseline run + score output
    double value = 0.0;
    std::printf("%.6f\n", value);
    return 0;
}
