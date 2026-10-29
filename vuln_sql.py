# FIXTURE — deliberately vulnerable. Used by the GPTNexus bench (N03, N07).
# SQL built by string concatenation = injection (R004).
import sys


def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return query


if __name__ == "__main__":
    print(get_user(sys.argv[1]))
