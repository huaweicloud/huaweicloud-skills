// evaluator.cpp - C++ evaluator command source
//
// How the evolution platform calls this:
//   1. `CreateAlgorithm --build_command="bash ./build.sh"` compiles first
//   2. In `CreateEvolveTask`, `evaluator_func_name` points directly at the
//      compiled artefact (e.g. "build/evaluate <args>"); `evaluator_file` is
//      left blank
//   3. Once the candidate `sort_algorithm.cpp` is ready, the platform launches
//      this command
//
// Constraints:
//   - The command MUST print the final score (a single float) on its own line
//     to stdout
//   - Do NOT print anything else to stdout (route logs to stderr)
//   - The algorithm source file MUST wrap the function under evolution with
//     `// EVOLVE_START` / `// EVOLVE_END` markers
//
// This file is a minimal template; replace the `value` calculation with your
// own business logic.

#include <cstdio>
#include <cstdlib>
#include <string>

int main() {
    // TODO: invoke the candidate `sort_algorithm` and compute the evaluation
    // score per the protocol
    // Typical shape: run the candidate binary / read stdin protocol / measure
    // time / print the score
    double value = 0.0;

    std::printf("%.6f\n", value);
    return 0;
}
