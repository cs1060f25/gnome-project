from io import BytesIO
from urllib.request import urlopen
from fitz import open, Matrix
from PIL import Image

def pdf_url_to_screenshots(url: str, zoom: float = 1.0) -> list[Image]:
    """
    Convert a PDF from URL to a list of PIL Images.
    
    Adapted from Voyage's public Colab notebook:
    https://colab.research.google.com/drive/10ohlVGS_Ps6e9GoURs3Sas9BIvS2QCVt?usp=sharing
    
    Args:
        url: URL of the PDF file to download and process
        zoom: Zoom factor for rendering (default: 1.0)
        
    Returns:
        List of PIL Images, one for each page
    """

    # Ensure that the URL is valid
    if not url.startswith("http") and url.endswith(".pdf"):
        raise ValueError("Invalid URL")

    # Read the PDF from the specified URL
    with urlopen(url) as response:
        pdf_data = response.read()
    pdf_stream = BytesIO(pdf_data)
    pdf = open(stream=pdf_stream, filetype="pdf")

    images = []

    # Loop through each page, render as pixmap, and convert to PIL Image
    mat = Matrix(zoom, zoom)
    for n in range(pdf.page_count):
        pix = pdf[n].get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    # Close the document
    pdf.close()

    return images


def pdf_path_to_screenshots(path: str, zoom: float = 1.0) -> list[Image]:
    """
    Convert a local PDF file to a list of PIL Images.
    
    Args:
        path: Path to the local PDF file
        zoom: Zoom factor for rendering (default: 1.0)
        
    Returns:
        List of PIL Images, one for each page
    """

    # Ensure the path exists and is a PDF
    if not path.endswith(".pdf"):
        raise ValueError("File must be a PDF")
    
    # Open the PDF directly from the file path
    pdf = open(path) 
    
    images = []
    
    # Loop through each page, render as pixmap, and convert to PIL Image
    mat = Matrix(zoom, zoom)
    for n in range(pdf.page_count):
        pix = pdf[n].get_pixmap(matrix=mat)
        
        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    
    # Close the document
    pdf.close()
    
    return images

def bytesio_to_screenshots(bytesio: BytesIO, zoom: float = 1.0) -> list[Image]:
    """
    Convert a PDF from BytesIO to a list of PIL Images.
    
    Args:
        bytesio: BytesIO object containing the PDF
        zoom: Zoom factor for rendering (default: 1.0)
        
    Returns:
        List of PIL Images, one for each page  
    """
    pdf = open(stream=bytesio, filetype="pdf")

    images = []

    # Loop through each page, render as pixmap, and convert to PIL Image
    mat = Matrix(zoom, zoom)
    for n in range(pdf.page_count):
        pix = pdf[n].get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    # Close the document
    pdf.close()

    return images
