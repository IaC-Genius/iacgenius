import re

# Read the original file
with open('iacgenius/cli.py', 'r') as f:
    contents = f.read()

# Remove all trailing whitespace using regex
cleaned = re.sub(r'[ \t]+$', '', contents, flags=re.MULTILINE)

# Write the cleaned version back
with open('iacgenius/cli.py', 'w') as f:
    f.write(cleaned)

print("Successfully removed all trailing whitespace from cli.py")
