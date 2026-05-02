from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import sys

input_md = "HANDOUT.md"
output_pdf = "HANDOUT.pdf"

if len(sys.argv) > 1:
    input_md = sys.argv[1]
if len(sys.argv) > 2:
    output_pdf = sys.argv[2]

with open(input_md, 'r', encoding='utf-8') as f:
    lines = [line.rstrip('\n') for line in f]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Heading1Custom', fontSize=16, leading=18, spaceAfter=6, alignment=TA_LEFT))
styles.add(ParagraphStyle(name='Heading2Custom', fontSize=13, leading=15, spaceAfter=4, alignment=TA_LEFT))
styles.add(ParagraphStyle(name='NormalCustom', fontSize=10, leading=12, spaceAfter=4, alignment=TA_LEFT))

story = []

in_code = False
code_lines = []

for line in lines:
    if line.strip().startswith('```'):
        in_code = not in_code
        if not in_code:
            # flush code block
            for cl in code_lines:
                story.append(Paragraph('<font face="Courier">%s</font>' % cl.replace('<','&lt;').replace('>','&gt;'), styles['NormalCustom']))
            code_lines = []
        continue
    if in_code:
        code_lines.append(line)
        continue
    if line.startswith('# '):
        story.append(Paragraph(f'<b>{line[2:].strip()}</b>', styles['Heading1Custom']))
    elif line.startswith('## '):
        story.append(Paragraph(f'<b>{line[3:].strip()}</b>', styles['Heading2Custom']))
    elif line.startswith('---'):
        story.append(Spacer(1, 6))
    elif line.strip().startswith('- '):
        # bullet
        story.append(Paragraph('• ' + line.strip()[2:], styles['NormalCustom']))
    elif line.strip() == '':
        story.append(Spacer(1, 4))
    else:
        # wrap long lines
        story.append(Paragraph(line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'), styles['NormalCustom']))

# Build PDF

doc = SimpleDocTemplate(output_pdf, pagesize=A4,
                        rightMargin=20*mm, leftMargin=20*mm,
                        topMargin=20*mm, bottomMargin=20*mm)

doc.build(story)

print(f"Wrote {output_pdf}")
