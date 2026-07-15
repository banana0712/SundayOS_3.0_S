"""Remove preferences+feedback section from main.py."""
import sys

target = "backend/app/main.py"

with open(target, encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find section start (comment line before preferences)
start = None
for i, line in enumerate(lines):
    if "# ── Feedback & Preferences (ADR-012)" in line:
        start = i
        print(f"Found section start at line {i+1}")
        break

# Find section end (after update_prefs, before next section)
end = None
for i in range(start + 1, len(lines)):
    # Look for next major section or next @app route
    if i > start + 20 and (lines[i].startswith("# ── Admin panel") or lines[i].startswith("class EmpathyRequest")):
        end = i - 1
        # Trim trailing blank lines
        while end > start and lines[end].strip() == "":
            end -= 1
        print(f"Found section end at line {end+1}")
        break

if start is None or end is None:
    print("Could not find preferences section boundaries!")
    sys.exit(1)

print(f"Will delete lines {start+1}-{end+1} ({end - start + 1} lines)")

# Show what we're deleting
print("\n=== First 3 lines to delete ===")
for line in lines[start:start+3]:
    print(repr(line))

print("\n=== Last 3 lines to delete ===")
for line in lines[end-2:end+1]:
    print(repr(line))

# Delete the section
new_lines = lines[:start] + lines[end+1:]

print(f"\nNew line count: {len(new_lines)}")

# Write back
with open(target, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Removed {end - start + 1} lines from {target}")
