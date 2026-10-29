# FIXTURE — deliberately SAFE. Used by the GPTNexus anti-false-positive test (N05).
# The scanner must report ZERO findings here. A scanner that cries wolf
# on clean code is useless (ULTRA: T — test-proof, a green that lies is a red).
#
# REGRESSION PIN (caught by bench N13, v1.0.1): the comments below MENTION
# dangerous constructs — they are documentation, not vulnerabilities.
# Full-line comments must never be flagged.
#   Never do: eval(user_input) on raw strings.
#   Never do: __import__(untrusted_name) either.
#   Never do: os.system("rm -rf /") obviously.
#   And never hardcode: password = "hunter2" in real code.
import math


def area(radius):
    if radius < 0:
        raise ValueError("radius must be non-negative")
    return math.pi * radius**2


def classify(n):
    total = 0
    for i in range(n):
        total += i
    if total > 100:
        return "big"
    return "small"


if __name__ == "__main__":
    print(round(area(2), 3))
    print(classify(20))
