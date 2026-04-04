"""
Generate a summary report from the known_repos ledger.

Usage:  python report.py
"""

from state import load_known_repos


def main():
    known = load_known_repos()
    if not known:
        print("No repos tracked yet. Run scan.py or seed_known_repos.py first.")
        return

    repos_with_e2 = {k: v for k, v in known.items() if v.get("e2_files")}
    repos_without = {k: v for k, v in known.items() if not v.get("e2_files")}
    total_e2 = sum(len(v["e2_files"]) for v in repos_with_e2.values())
    total_e1 = sum(v.get("e1_file_count", 0) for v in known.values())

    print("=" * 60)
    print("E2-SOURCES STATUS REPORT")
    print("=" * 60)
    print(f"  Repos tracked:           {len(known)}")
    print(f"  Repos with E2 files:     {len(repos_with_e2)}")
    print(f"  Repos without E2:        {len(repos_without)}")
    print(f"  Total E2 files:          {total_e2}")
    print(f"  Total E1 files seen:     {total_e1}")

    print(f"\n{'Repo':<60} {'E2':>4}  {'Last Checked':<22}  {'SHA':>10}")
    print("-" * 105)
    for repo in sorted(repos_with_e2.keys()):
        entry = repos_with_e2[repo]
        e2_count = len(entry["e2_files"])
        checked = entry.get("last_checked_at", "?")[:10]
        sha = (entry.get("last_checked_sha") or "?")[:10]
        print(f"  {repo:<58} {e2_count:>4}  {checked:<22}  {sha:>10}")

    # Size breakdown
    sizes = []
    for entry in repos_with_e2.values():
        for f in entry["e2_files"]:
            s = f.get("size", 0)
            if s > 0:
                sizes.append(s)
    if sizes:
        print(f"\nE2 file sizes (of {len(sizes)} with known size):")
        print(f"  Smallest: {min(sizes):>12,} bytes")
        print(f"  Largest:  {max(sizes):>12,} bytes")
        print(f"  Total:    {sum(sizes):>12,} bytes")


if __name__ == "__main__":
    main()
