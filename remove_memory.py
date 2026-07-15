"""Remove memory + experience section from main.py."""
import sys

target = "backend/app/main.py"

with open(target, encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find memory section start (MemoryStoreRequest class)
start = None
for i, line in enumerate(lines, 1):
    if "class MemoryStoreRequest" in line:
        start = i - 1  # 0-indexed
        print(f"Found MemoryStoreRequest at line {i}")
        break

if start is None:
    print("Could not find MemoryStoreRequest!")
    sys.exit(1)

# Memory section goes until end of file
end = len(lines) - 1
print(f"Section goes to end of file (line {end+1})")

# Need to keep the blank line before MemoryStoreRequest (line 1090)
# So start from line 1091 (index 1090)
print(f"Will delete lines {start+1}-{end+1} ({end - start + 1} lines)")

# Show what we're deleting
print("\n=== First 5 lines to delete ===")
for line in lines[start:start+5]:
    print(repr(line))

print("\n=== Last 5 lines to delete ===")
for line in lines[end-4:end+1]:
    print(repr(line))

# Delete the section, keep everything before
new_lines = lines[:start]

print(f"\nNew line count: {len(new_lines)}")

# Write back
with open(target, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"✓ Removed {end - start + 1} lines from {target}")
