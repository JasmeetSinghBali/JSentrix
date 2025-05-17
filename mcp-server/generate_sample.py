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
    ("Transaction Limitations", "Cross-border transfers between Country A and Country B must not exceed $10,000 per calendar month."),  # Limit
    ("Prohibited Transactions", "Transactions involving sanctioned entities from Country X are strictly prohibited."),  # Prohibited
    ("Reporting Requirements", "All transactions over $5,000 must be reported within 24 hours."),  # Reporting
    ("Transaction Limitations", "Currency conversion for single transactions must not exceed $15,000 without prior approval."),  # Limit
    ("Prohibited Transactions", "Transfers to unverified third-party accounts are strictly prohibited."),  # Prohibited
    ("Reporting Requirements", "Suspicious activity must be logged and reported to the compliance team within 12 hours."),  # Reporting
    ("Transaction Limitations", "ATM withdrawals are limited to $1,000 per day per account."),  # Limit
    ("Prohibited Transactions", "Use of shell companies for fund transfers is prohibited."),  # Prohibited
    ("Reporting Requirements", "All large cash transactions above $10,000 must be documented and submitted weekly."),  # Reporting
    ("Transaction Limitations", "Wire transfers must not exceed $100,000 without compliance officer authorization."),  # Limit
    ("Prohibited Transactions", "Payments to politically exposed persons without enhanced due diligence are prohibited."),  # Prohibited
    ("Reporting Requirements", "Every transaction involving more than one jurisdiction must be reviewed and reported."),  # Reporting
    ("Transaction Limitations", "Mobile wallet top-ups are limited to $5,000 per week."),  # Limit
    ("Prohibited Transactions", "Sending funds to accounts flagged by international watchlists is prohibited."),  # Prohibited
    ("Reporting Requirements", "Weekly summaries of all international transfers must be submitted to the finance director."),  # Reporting
    ("Transaction Limitations", "Investment transactions exceeding $200,000 require executive approval."),  # Limit
    ("Prohibited Transactions", "Use of anonymizing VPNs during transaction initiation is prohibited."),  # Prohibited
    ("Reporting Requirements", "High-frequency accounts must be flagged and reported monthly."),  # Reporting
    ("Transaction Limitations", "Online foreign exchange transfers must not exceed $2,000 per transaction."),  # Limit
    ("Prohibited Transactions", "Payments involving cryptocurrency mixers are strictly prohibited."),  # Prohibited
]


pdf = PDF()
pdf.add_page()
pdf.set_font("Arial", size=12)

for i, (title, desc) in enumerate(clauses, 1):
    pdf.multi_cell(0, 10, f"Clause {i} - {title}:\n{desc}")
    pdf.ln(5)

pdf.output("sample_clauses.pdf")
print("Generated sample_clauses.pdf")
