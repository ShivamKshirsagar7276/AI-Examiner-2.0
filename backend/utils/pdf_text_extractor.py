import pdfplumber


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts clean text from a typed PDF question paper.
    Returns full document text as a single string.
    """

    full_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text.strip())
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {str(e)}")

    return "\n\n".join(full_text)