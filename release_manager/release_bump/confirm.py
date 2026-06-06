from __future__ import annotations


def double_confirm(
    *, mode: str, mac_from: str | None, 
    mac_to: str | None, engine_from: str | None, 
    engine_to: str | None, file_count: int, dry_run: bool, assume_yes: bool,) -> bool:
    
    if dry_run:
        return True
    if assume_yes:
        return True

    print("\n=== Version bump confirmation ===")
    print(f"Mode: {mode}")
    if mac_to:
        print(f"Mac:    {mac_from} → {mac_to}")
    if engine_to:
        print(f"Engine: {engine_from} → {engine_to}")
    print(f"Files:  {file_count} (archived first)\n")
    
    answer1 = input("Type YES to continue: ").strip()
    if answer1 != "YES":
        print("Aborted.")
        return False
    answer2 = input("Type the word bump to apply: ").strip()
    if answer2 != "bump":
        print("Aborted.")
        return False
    return True
