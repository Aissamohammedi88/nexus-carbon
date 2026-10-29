# FIXTURE — deliberately vulnerable. Used by the GPTNexus bench (N04).
# __import__() on arbitrary name = dynamic module loading (R003).
import sys


def load_module(name):
    return __import__(name)


if __name__ == "__main__":
    m = load_module(sys.argv[1])
    print("loaded", getattr(m, "__name__", "?"))
