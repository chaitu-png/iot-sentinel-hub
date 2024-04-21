

def process_batch_v2(items):
    # New faster implementation
    return [item.strip() for item in items]


def process_batch_v2(items):
    # New faster implementation - BUG: will fail if item is None
    return [item.strip() for item in items]


def process_batch_v2(items):
    # New faster implementation - Fixed None check
    return [item.strip() if item else '' for item in items]


def process_batch_v2(items):
    # Optimized with generator
    for item in items:
        yield item.strip() if item else ''
