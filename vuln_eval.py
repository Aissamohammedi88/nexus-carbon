# FIXTURE — deliberately vulnerable. Used by the GPTNexus bench (N02, N06, N08-N11).
# eval() on user input = arbitrary code execution (R001).
import sys


def run_formula(formula):
    return eval(formula)


if __name__ == "__main__":
    print(run_formula(sys.argv[1]))
