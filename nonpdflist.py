# Read the content from HASHES.txt
with open('HASHES.txt', 'r') as file:
    lines = file.readlines()

# Filter out lines where the filename ends with '.pdf'
non_pdf_lines = []
for line in lines:
    if line.strip():  # Skip empty lines
        filename = line.split(':')[0].strip()
        if not filename.endswith('.pdf'):
            non_pdf_lines.append(line)

# Extract EFTA number for sorting
def get_efta_number(line):
    filename = line.split(':')[0].strip()
    # Assuming format EFTA followed by digits before the extension
    base = filename.split('.')[0]
    if base.startswith('EFTA'):
        return int(base[4:])
    return 0  # Fallback if not matching

# Sort the non-pdf lines by EFTA number ascending
sorted_lines = sorted(non_pdf_lines, key=get_efta_number)

# Write to HASHES_nonpdf.txt
with open('HASHES_nonpdf.txt', 'w') as file:
    file.writelines(sorted_lines)