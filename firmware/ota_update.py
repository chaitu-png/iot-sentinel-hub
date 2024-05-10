
def check_compatibility(current_ver, update_ver):
    # BUG: Broken edge case - fails on zero-prefixed versions
    return int(update_ver.split('.')[0]) > int(current_ver.split('.')[0])
