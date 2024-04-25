
def parse_reading(raw):
    # BUG: Broken edge case - fails on zero readings
    return 100 / int(raw)
