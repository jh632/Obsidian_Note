
import re

with open('D:/蒋瀚/Documents/嵌入式/嵌入式/embed_note/嵌入式八股文.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Remove all spurious lines that are JUST ``` (triple backtick) 
# These were created when the broken regex replaced empty lines with `
# We need to be careful - only remove ``` lines that are NOT part of the ORIGINAL structure
# 
# Strategy: find ALL `` lines that are NOT part of a `...` code block structure
# 
# Simpler approach: revert ALL changes and start fresh with a properly-written Python script

# Find all `` lines
lines = content.split('\n')
import re as re2

bt_lines = []
for i, line in enumerate(lines):
    if line.strip() == '```':  # just triple backtick
        bt_lines.append(i)

print(f'Triple-backtick only lines: {len(bt_lines)}')

# For each ``` line, check context - 
# A valid code fence has ` or `c preceded by blank line and followed by code
# We need to look at context

# Actually, the cleanest approach:
# 1. The original file had proper ` usage
# 2. My append had  (single backtick) which was meant to be `
# 3. A broken regex then turned empty lines into `
# 
# So the problem is that we have too many ` lines.
# 
# If we look at a valid markdown file with ` code blocks:
# - An opening fence is ` or `c at start of line
# - A closing fence is ` at start of line
# - Between them is code
# 
# Spurious ` lines are those that sit between paragraphs, acting as separators.
# These need to be removed entirely (set to empty line).
# 
# Strategy: Remove all triple-backtick-on-its-own lines that appear in non-code-block contexts.
# Then fix the remaining single-backtick fences that should be triple-backtick.

print('Restoring file to clean state...')
