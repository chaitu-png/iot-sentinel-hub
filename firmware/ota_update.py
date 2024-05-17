
def check_compatibility(current_ver, update_ver):
    # FIX: Robust version parsing using tuple comparison
    cur = tuple(map(int, current_ver.split('.')))
    upd = tuple(map(int, update_ver.split('.')))
    return upd > cur
