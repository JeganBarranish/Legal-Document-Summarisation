import nltk
import numpy as np
import pdfplumber
import re
import os
import time

from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

load_dotenv()

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

embedder = SentenceTransformer('all-MiniLM-L6-v2')

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
        if not stripped: continue
        lower = stripped.lower()

        for section, keywords in section_keywords.items():
            if any(kw in lower for kw in keywords):
                current_section = section
                break

        if current_section:
            sections[current_section].append(stripped)

    return {k: " ".join(v) for k, v in sections.items()}

def retrieve_context(query, text, sections, top_k=5, threshold=0.20):
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
    if not sentences: return ""

    sent_embs = embedder.encode(sentences)
    query_emb = embedder.encode([query])
    scores    = cosine_similarity(query_emb, sent_embs)[0]

    top_indices = scores.argsort()[-top_k:][::-1]
    context_sentences = [sentences[i] for i in top_indices if scores[i] >= threshold]

    return " ".join(context_sentences)

def synthesize_answer(query, context):
    if not context.strip():
        return "❌ No relevant information found in the document."
        
    sentences = sent_tokenize(context)
    return " ".join(sentences[:3])

def summarize_section(section_name, content):
    if not content.strip():
        return "No content detected."
    
    sentences = preprocess_text(content)
    return " ".join(sentences[:2]) if sentences else "Could not summarize."

def is_valid_query(query):
    query_lower = query.lower()

    negative_keywords = [
        "next hearing", "today's date", "weather", "cricket",
        "judge's assistant", "first question asked", "lunch break",
        "phone number", "address of court"
    ]
    if any(neg in query_lower for neg in negative_keywords): return False

    if len(query.split()) >= 3: return True
    return False

def detect_question_type(query):
    q = query.lower()
    if any(w in q for w in ["who", "petitioner", "respondent", "party"]): return "PERSON"
    elif any(w in q for w in ["when", "date", "year", "period"]): return "TIME"
    elif any(w in q for w in ["why", "reason", "purpose"]): return "REASON"
    elif any(w in q for w in ["amount", "how much", "rupee", "money"]): return "NUMBER"
    elif any(w in q for w in ["judgment", "decision", "result", "held"]): return "JUDGMENT"
    elif any(w in q for w in ["what", "explain", "describe", "about", "key"]): return "DESCRIPTIVE"
    else: return "GENERAL"

def main():
    print("\n" + "="*48)
    print("   ⚖️  LEGAL QA CHATBOT  —  Pure NLP Extractive")
    print("="*48 + "\n")

    file_path = input("📄 Enter document path (.txt or .pdf): ").strip()
    if not file_path: return

    try:
        text = read_document(file_path)
        print(f"\n✅ Document loaded — {len(text.split())} words\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    sections = detect_sections(text)
    
    print("📂 Section Detection:")
    for s, c in sections.items():
        print(f"   {s}: {len(c.split())} words")

    print("\n" + "-"*48)
    print("📋 DOCUMENT SUMMARIES")
    print("-"*48)
    for section, content in sections.items():
        if content.strip():
            print(f"\n📌 {section}:")
            print(summarize_section(section, content))

    print("\n" + "="*48)
    print("💬 CHATBOT — Ask anything about the case.")
    print("   Type 'quit' to exit.\n")
    print("-"*48)

    while True:
        query = input("\n🧑 You: ").strip()
        if not query: continue
        if query.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!\n")
            break

        if not is_valid_query(query):
            print("🤖 Bot: ❌ That question doesn't seem related to this legal document.")
            continue

        q_type  = detect_question_type(query)
        context = retrieve_context(query, text, sections)
        answer  = synthesize_answer(query, context)

        print(f"🤖 Bot: {answer}")
        print(f"        [{q_type}]")

if __name__ == "__main__":
    main()
