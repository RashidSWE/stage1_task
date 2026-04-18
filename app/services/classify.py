def classify_age(age: int) -> str:
    if age <= 12:
        return "child"
    if age >= 13 and age <= 19:
        return "teenager"
    if age >= 20 and age <= 59:
        return "adult"
    if age >= 60:
        return "senior"