from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Sample Compliance Clauses Document', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

clauses = [
    {"id": "C1", "title": "Transaction Limitations", "text": "Cross-border transfers between Country A and Country B must not exceed $10,000 per calendar month."},
    {"id": "C2", "title": "Prohibited Transactions", "text": "Transactions involving sanctioned entities from Country X are strictly prohibited."},
    {"id": "C3", "title": "Reporting Requirements", "text": "All transactions over $5,000 must be reported within 24 hours."},
    {"id": "C4", "title": "Transaction Limitations", "text": "Currency conversion for single transactions must not exceed $15,000 without prior approval.", "references": ["C1"], "amends": ["C1"]},
    {"id": "C5", "title": "Prohibited Transactions", "text": "Transfers to unverified third-party accounts are strictly prohibited.", "references": ["C2"]},
    {"id": "C6", "title": "Reporting Requirements", "text": "Suspicious activity must be logged and reported within 12 hours.", "references": ["C3"], "overrides": ["C3"]},
    {"id": "C7", "title": "Transaction Limitations", "text": "Emergency transactions may exceed standard limits with compliance approval.", "overrides": ["C1", "C4"]},
    {"id": "C8", "title": "Due Diligence Requirements", "text": "All new customer accounts must undergo enhanced due diligence checks.", "references": ["C2"]},
    {"id": "C9", "title": "Documentation Standards", "text": "Transaction records must be maintained for minimum 7 years.", "references": ["C3"]},
    {"id": "C10", "title": "Cryptocurrency Transactions", "text": "Crypto transfers exceeding $5,000 require special authorization.", "overrides": ["C1"], "amends": ["C4"]},
    {"id": "C11", "title": "PEP Restrictions", "text": "Transactions involving Politically Exposed Persons require dual approval.", "references": ["C2", "C8"]},
    {"id": "C12", "title": "Audit Requirements", "text": "Random audits must be conducted quarterly on 5% of all transactions.", "references": ["C3", "C6"]},
    {"id": "C13", "title": "High-Risk Jurisdictions", "text": "Transfers to Category 3 countries limited to $2,000/month.", "amends": ["C1"], "references": ["C4"]},
    {"id": "C14", "title": "Whistleblower Policy", "text": "Anonymous reporting channels must be maintained for compliance violations.", "references": ["C6"]},
    {"id": "C15", "title": "Cash Handling Limits", "text": "Branch cash holdings must not exceed $500,000 at any time.", "overrides": ["C7"]},
    {"id": "C16", "title": "Third-Party Payments", "text": "Payments to non-registered vendors prohibited without pre-approval.", "references": ["C5"]},
    {"id": "C17", "title": "Data Retention Policy", "text": "Customer KYC documents must be archived for 10 years post-account closure.", "amends": ["C9"]},
    {"id": "C18", "title": "Cross-Border Reporting", "text": "All international transfers require ISO country code documentation.", "references": ["C1", "C10"]},
    {"id": "C19", "title": "Suspension Protocol", "text": "Accounts with 3 failed compliance checks must be frozen immediately.", "overrides": ["C6"]},
    {"id": "C20", "title": "Compliance Training", "text": "Mandatory anti-money laundering training required annually for all staff.", "references": ["C2", "C8", "C11"]}
]

pdf = PDF()
pdf.add_page()
pdf.set_font("Arial", size=11)

for clause in clauses:
    # Clause header
    pdf.set_font('Arial', 'B', 11)
    pdf.multi_cell(0, 7, f"Clause {clause['id']} - {clause['title']}")
    pdf.ln(2)
    
    # Clause text
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 7, clause["text"])
    pdf.ln(2)
    
    # Relationships
    pdf.set_font('Arial', 'I', 10)
    if 'references' in clause:
        pdf.set_text_color(0, 0, 200)  # Blue
        pdf.multi_cell(0, 7, f"References: {', '.join(clause['references'])}")
    if 'amends' in clause:
        pdf.set_text_color(0, 150, 0)  # Green
        pdf.multi_cell(0, 7, f"Amends: {', '.join(clause['amends'])}")
    if 'overrides' in clause:
        pdf.set_text_color(200, 0, 0)  # Red
        pdf.multi_cell(0, 7, f"Overrides: {', '.join(clause['overrides'])}")
    
    # Reset formatting
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

pdf.output("sample_compliance.pdf")
print("Generated sample_compliance.pdf with 20 interconnected clauses")
