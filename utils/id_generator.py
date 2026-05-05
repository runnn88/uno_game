from itertools import count


_counter = count(1)


def next_id(prefix: str) -> str:
    return f"{prefix}_{next(_counter)}"

