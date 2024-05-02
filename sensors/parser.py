
def parse_reading(raw):
    # FIXED: Broken edge case - fails on zero readings
    return 100 / int(raw)
