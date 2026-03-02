from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os


def run_document_intelligence_ocr(pdf_path: str):
    """
    Uses Azure Document Intelligence (prebuilt-read model)
    Input: PDF file path
    Output: Page-wise OCR text ONLY (no polygon, no layout data)
    """

    # --------------------------------------------------
    # LOAD ENV VARIABLES AT RUNTIME
    # --------------------------------------------------
    AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT")
    AZURE_DI_KEY = os.getenv("AZURE_DI_KEY")

    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise RuntimeError(
            "Azure Document Intelligence environment variables not set. "
            "Please set AZURE_DI_ENDPOINT and AZURE_DI_KEY."
        )

    # --------------------------------------------------
    # CREATE CLIENT
    # --------------------------------------------------
    client = DocumentAnalysisClient(
        endpoint=AZURE_DI_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DI_KEY)
    )

    # --------------------------------------------------
    # RUN OCR
    # --------------------------------------------------
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            document=f
        )

    result = poller.result()

    pages_output = []

    for page in result.pages:
        page_data = {
            "page_number": page.page_number,
            "lines": []
        }

        for line in page.lines:
            page_data["lines"].append({
                "text": line.content.strip()
            })

        pages_output.append(page_data)

    return pages_output
