from io import BytesIO
from urllib.request import urlopen
from fitz import open, Matrix
from PIL import Image
from pathlib import Path


def parse_local_pdf(path: str, zoom: float = 1.0) -> list[Image]:
    """
    Convert a local PDF file to a list of PIL Images.
    
    Args:
        path: Path to the local PDF file
        zoom: Zoom factor for rendering (default: 1.0)
        
    Returns:
        List of PIL Images, one for each page
    """
    if not path:
        raise ValueError("No path was provided.")
    if not isinstance(path, str):
        raise ValueError("Path must be provided as a string.")
    if not isinstance(zoom, float):
        raise ValueError("Zoom factor must be a float.")

    pdf_path = Path(path)

    if not pdf_path.exists():
        raise ValueError("Provided path does not exist.")
    if not pdf_path.is_file():
        raise ValueError("Provided path is not a file.")
    if not pdf_path.suffix == ".pdf":
        raise ValueError("Provided file is not a PDF.")
    
    with open(path) as pdf:
        images = []
        
        # Loop through each page, render as pixmap, and convert to PIL Image.
        zoom_matrix = Matrix(zoom, zoom)
        for n in range(pdf.page_count):
            pixmap = pdf[n].get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pixmap.width, pixmap.height],
                                  pixmap.samples)
            images.append(img)
    
    return images


def parse_binary_pdf(binary_data: BytesIO, zoom: float = 1.0) -> list[Image]:
    """
    Convert binary PDF data to a list of PIL Images.
    
    Args:
        binary_data: BytesIO object containing PDF binary data.
        zoom: Zoom factor for rendering.
        
    Returns:
        List of PIL Images, one for each page.
    """
    if not binary_data:
        raise ValueError("No binary data was provided.")
    if not isinstance(binary_data, BytesIO):
        raise ValueError("Binary data must be a BytesIO object.")
    if not isinstance(zoom, float):
        raise ValueError("Zoom factor must be a float.")

    with open(stream=binary_data, filetype="pdf") as pdf:
        images = []

        # Loop through each page, render as pixmap, and convert to PIL Image.
        zoom_matrix = Matrix(zoom, zoom)
        for n in range(pdf.page_count):
            pixmap = pdf[n].get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pixmap.width, pixmap.height],
                                  pixmap.samples)
            images.append(img)

    return images
