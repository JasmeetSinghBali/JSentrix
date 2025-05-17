from docling.document_converter import DocumentConverter

def pdf_to_markdown(pdf_path, md_path):
    converter=DocumentConverter()
    docling_doc=converter.convert(pdf_path)
    md_text=docling_doc.document.export_to_markdown()
    with open(md_path,"w",encoding="utf-8") as f:
        f.write(md_text)
    return md_path
