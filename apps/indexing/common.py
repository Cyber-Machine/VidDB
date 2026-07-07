from math import sqrt


def text_embedding(text: str) -> list[float]:
    letters = [0.0, 0.0, 0.0, 0.0]
    for character in text.lower():
        if "a" <= character <= "g":
            letters[0] += 1
        elif "h" <= character <= "n":
            letters[1] += 1
        elif "o" <= character <= "t":
            letters[2] += 1
        elif "u" <= character <= "z":
            letters[3] += 1
    length = sqrt(sum(value * value for value in letters)) or 1.0
    return [value / length for value in letters]


def cosine_score(left: list[float], right: list[float]) -> float:
    return sum(left_value * right_value for left_value, right_value in zip(left, right))
