from flask import Flask, request, jsonify, render_template
import pytesseract
from docx import Document
import PyPDF2
import requests
from PIL import Image
import io
import json
import os
import fitz  # PyMuPDF
import imghdr

app = Flask(__name__)

@app.route('/')
def index():

    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    file = request.files['file']
    language = request.form.get('language', 'por')
    keywords = json.loads(request.form.get('keywords', '[]'))

    if file.filename.endswith('.pdf'):
        text = extract_text_from_pdf(file, language)
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(file)
    elif file.filename.endswith(('.png', '.jpg', '.jpeg','.webp')):
        text = extract_text_from_image(file, language)
    else:
        return jsonify({'error': 'Tipo de arquivo não suportado'}), 400

    filtered_text = filter_text_by_keywords(text, keywords)

    return jsonify({'text': filtered_text})

@app.route('/process-url', methods=['POST'])
def process_url():
    data = request.get_json()
    file_url = data.get('url')
    language = data.get('language', 'por')
    keywords = data.get('keywords', [])

    response = requests.get(file_url)
    file = io.BytesIO(response.content)
    
    file_type = imghdr.what(file)
    if file_type in ['png', 'jpeg', 'webp']:
        file.seek(0)  # Reiniciar o ponteiro do buffer
        text = extract_text_from_image(file, language)    
    elif file_url.endswith('.pdf'):
        text = extract_text_from_pdf(file, language)
    elif file_url.endswith('.docx'):
        text = extract_text_from_docx(file)
    # elif file_url.endswith(('.png', '.jpg', '.jpeg')):
    #     text = extract_text_from_image(file, language)
    else:
        return jsonify({'error': 'Tipo de arquivo não suportado'}), 400

    filtered_text = filter_text_by_keywords(text, keywords)
    return jsonify({'text': filtered_text})

def extract_text_from_pdf(file, language):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    # Se o texto extraído estiver vazio, use OCR (Utilizando OCR como FALLBACK)
    if not text.strip():
        # Reinicie o ponteiro do arquivo
        file.seek(0)
        
        # Use PyMuPDF para abrir o PDF
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
        # no heroku
        pytesseract.pytesseract.tesseract_cmd = '/app/.apt/usr/bin/tesseract'         
        # Configure a variável de ambiente para os dados de linguagem
        os.environ["TESSDATA_PREFIX"] = "/app/.apt/usr/share/tesseract-ocr/4.00/tessdata" 

        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Utilize Tesseract OCR para extrair o texto da imagem
            text += pytesseract.image_to_string(img, lang=language)

    return text        

def extract_text_from_docx(file):
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text_from_image(file, language):
    # no heroku
    pytesseract.pytesseract.tesseract_cmd = '/app/.apt/usr/bin/tesseract'         
    # Configure a variável de ambiente para os dados de linguagem
    os.environ["TESSDATA_PREFIX"] = "/app/.apt/usr/share/tesseract-ocr/4.00/tessdata" 

    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    image = Image.open(file)
    if image.format == 'WEBP':
        image = image.convert('RGB')    

    text = pytesseract.image_to_string(image, lang=language)
    return text

def filter_text_by_keywords(text, keywords):
    paragraphs = text.split('\n')
    filtered_paragraphs = []
    for para in paragraphs:
        if any(keyword in para for keyword in keywords):
            filtered_paragraphs.append(para)
    return "\n".join(filtered_paragraphs)

if __name__ == '__main__':
    app.run(debug=True)
