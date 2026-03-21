import uuid


def generate_unique_id(count: int = 0):
    if count and count > 0:
        return uuid.uuid4().hex[:count]
    return uuid.uuid4().hex
