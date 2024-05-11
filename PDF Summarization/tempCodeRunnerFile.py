from flask import Flask, request, jsonify, render_template
import os
import fitz  # PyMuPDF
import numpy as np
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def process_pdf(file_path):
    # Process PDF file
    pdf_document = fitz.open(file_path)
    main_content = ""

    pattern = r"TODAY'S PAPER \|.*\nAFP \|  Published.*\n|JOIN OUR WHATSAPP CHANNEL.*\n|— AFP.*\n|— Reuters.*\n"

    for page_number in range(pdf_document.page_count):
        page = pdf_document.load_page(page_number)
        text = page.get_text()
        cleaned_text = re.sub(pattern, "", text)
        main_content += cleaned_text + "\n"

    pdf_document.close()
    return main_content

def summarize_text(content):
    # Summarize text
    sentences = sent_tokenize(content)
    featurizer = TfidfVectorizer(stop_words='english')
    X = featurizer.fit_transform(sentences)
    S = cosine_similarity(X)
    S /= S.sum(axis=1, keepdims=True)
    factor = 0.15
    S = (1 - factor) * S + factor * (np.ones_like(S) / len(S))
    eigenvals, eigenvecs = np.linalg.eig(S.T)
    limiting_dist = np.ones(len(S)) / len(S)
    threshold = 1e-8
    delta = float('inf')
    iters = 0
    while delta > threshold:
        iters += 1
        p = limiting_dist.dot(S)
        delta = np.abs(p - limiting_dist).sum()
        limiting_dist = p
    scores = limiting_dist
    sort_idx = np.argsort(-scores)
    summary = " ".join(sentences[i] for i in sort_idx[:6])
    return summary

@app.route('/')
def index():
    return render_template('upload_pdf.html')

@app.route('/summary')
def summary():
    return render_template('summary.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdfFile' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['pdfFile']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and file.filename.endswith('.pdf'):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            content = process_pdf(file_path)
            summary = summarize_text(content)
            return render_template('summary.html', summary=summary)

        except Exception as e:
            return jsonify({'error': str(e)})

    else:
        return jsonify({'error': 'Invalid file format'})

if __name__ == '__main__':
    app.run(debug=True)