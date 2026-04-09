import os
import re
import time
import uuid
import werkzeug
from flask import Flask, request, jsonify, render_template, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import nltk
import numpy as np
import pdfplumber
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ─────────────────────────────────────────
# SETUP NLP MODELS
# ─────────────────────────────────────────
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

# Loading the sentence transformer model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# ─────────────────────────────────────────
# FLASK SETUP
# ─────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "super-secret-legal-key"
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory document storage mapping doc_id -> parsed data
DOCUMENTS_DB = {}
RAW_TEXT_DB = {}

# ─────────────────────────────────────────
# CORE LOGIC FROM main.py
# ─────────────────────────────────────────

def read_document(file_path):
    if file_path.lower().endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif file_path.lower().endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        if not text.strip():
            raise ValueError("PDF appears empty or unreadable.")
        return text

    raise ValueError("Unsupported format. Use .txt or .pdf")

def preprocess_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,;:()\'\"\-]', '', text)
    sentences = sent_tokenize(text)
    return [s.strip() for s in sentences if len(s.split()) > 4]

def detect_sections(text):
    sections = {"FACTS": [], "ARGUMENTS": [], "JUDGMENT": []}

    section_keywords = {
        "FACTS":     ["facts", "background", "brief facts", "factual"],
        "ARGUMENTS": ["argument", "contention", "submission", "urged", "counsel"],
        "JUDGMENT":  ["judgment", "decision", "order", "held", "dismissed",
                      "allowed", "result", "conclusion", "decree"]
    }

    current_section = None
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()

        for section, keywords in section_keywords.items():
            if any(kw in lower for kw in keywords):
                current_section = section
                break

        if current_section:
            sections[current_section].append(stripped)

    return {k: " ".join(v) for k, v in sections.items()}

def retrieve_context(query, text, sections, top_k=5, threshold=0.20):
    """Return a context object with selected sentences and processing details.

    Returns a dict:
      {
        'context': <joined selected sentences>,
        'selected_sentences': [ { 'sentence': str, 'score': float, 'tokens': [..], 'normalized_tokens': [..] }, ... ],
        'process': { 'sentence_count': int, 'selected_count': int, 'embedding_dim': int, 'notes': str }
      }
    """
    query_lower = query.lower()

    if any(w in query_lower for w in ["judgment", "decide", "result", "held",
                                       "order", "dismiss", "allow", "quash"]):
        search_text = sections.get("JUDGMENT", "")
    elif any(w in query_lower for w in ["argument", "contention", "urge",
                                         "government say", "petitioner argue"]):
        search_text = sections.get("ARGUMENTS", "")
    elif any(w in query_lower for w in ["fact", "background"]):
        search_text = sections.get("FACTS", "")
    else:
        search_text = " ".join(v for v in sections.values() if v.strip())

    if len(search_text.split()) < 40:
        search_text = text

    sentences = preprocess_text(search_text)
    if not sentences:
        return {'context': '', 'selected_sentences': [], 'process': {'sentence_count': 0, 'selected_count': 0, 'embedding_dim': 0, 'notes': 'No sentences extracted.'}}

    # Embeddings
    sent_embs = embedder.encode(sentences)
    query_emb = embedder.encode([query])
    scores = cosine_similarity(query_emb, sent_embs)[0]

    top_indices = scores.argsort()[-top_k:][::-1]

    selected = []
    for i in top_indices:
        if scores[i] >= threshold:
            sent = sentences[i]
            # Tokenization and simple normalization
            tokens = nltk.word_tokenize(sent)
            normalized_tokens = [re.sub(r"[^\w']", '', t).lower() for t in tokens if re.sub(r"[^\w']", '', t)]

            selected.append({
                'sentence': sent,
                'score': float(scores[i]),
                'tokens': tokens,
                'normalized_tokens': normalized_tokens
            })

    context_text = " ".join([s['sentence'] for s in selected])

    process = {
        'method': 'SentenceTransformer(all-MiniLM-L6-v2)',
        'sentence_count': len(sentences),
        'selected_count': len(selected),
        'embedding_dim': int(sent_embs.shape[1]) if hasattr(sent_embs, 'shape') and len(sent_embs.shape) > 1 else 0,
        'notes': 'Tokenization: NLTK word_tokenize -> normalization: remove punctuation & lowercase -> segmentation: sent_tokenize used -> vector semantics: cosine similarity between query and sentence embeddings.' ,
        'scores': [float(scores[i]) for i in top_indices]
    }

    return {'context': context_text, 'selected_sentences': selected, 'process': process}

def synthesize_answer(query, context):
    if not context.strip():
        return "❌ No relevant information found in the document."
    
    # NLP Extractive QA
    # The 'context' is already formed by the best matching sentences from 'retrieve_context'.
    # We will just format it nicely as the extractive answer.
    sentences = sent_tokenize(context)
    # Take up to the top 3 highly relevant sentences to keep it concise
    return " ".join(sentences[:3])

def summarize_section(section_name, content):
    if not content.strip():
        return "No content detected."
        
    # NLP Extractive Summarization
    sentences = preprocess_text(content)
    # Return the first 3 substantive sentences as a basic summary
    return " ".join(sentences[:3]) if sentences else "Could not summarize."

def detect_question_type(query):
    q = query.lower()
    if any(w in q for w in ["who", "petitioner", "respondent", "party"]):
        return "PERSON"
    elif any(w in q for w in ["when", "date", "year", "period"]):
        return "TIME"
    elif any(w in q for w in ["why", "reason", "purpose"]):
        return "REASON"
    elif any(w in q for w in ["amount", "how much", "rupee", "money"]):
        return "NUMBER"
    elif any(w in q for w in ["judgment", "decision", "result", "held"]):
        return "JUDGMENT"
    elif any(w in q for w in ["what", "explain", "describe", "about", "key"]):
        return "DESCRIPTIVE"
    else:
        return "GENERAL"


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'document' not in request.files:
        return jsonify({'error': 'No document uploaded'}), 400
        
    file = request.files['document']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.txt')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            text = read_document(filepath)
            sections = detect_sections(text)
            doc_id = str(uuid.uuid4())
            DOCUMENTS_DB[doc_id] = sections
            RAW_TEXT_DB[doc_id] = text
            
            # Generate summaries for each section
            summaries = {}
            for section, content in sections.items():
                if content.strip():
                    summaries[section] = summarize_section(section, content)

            return jsonify({
                'doc_id': doc_id,
                'filename': filename,
                'word_count': len(text.split()),
                'sections': {k: len(v.split()) for k, v in sections.items()},
                'summaries': summaries
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Unsupported file format'}), 400

@app.route('/api/query', methods=['POST'])
def query_doc():
    data = request.json
    doc_id = data.get('doc_id')
    query = data.get('query')
    
    if not doc_id or doc_id not in DOCUMENTS_DB:
        return jsonify({'error': 'Document not found or not uploaded yet.'}), 400
    if not query:
        return jsonify({'error': 'Empty query'}), 400
        
    try:
        sections = DOCUMENTS_DB[doc_id]
        text = RAW_TEXT_DB[doc_id]
        
        context_obj = retrieve_context(query, text, sections)
        context = context_obj.get('context', '')
        answer = synthesize_answer(query, context)
        q_type = detect_question_type(query)
        
        return jsonify({
            'answer': answer,
            'question_type': q_type,
            'selected_sentences': context_obj.get('selected_sentences', []),
            'process': context_obj.get('process', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
