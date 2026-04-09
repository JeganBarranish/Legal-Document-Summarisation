# ⚖️ Legal QA Chatbot — Setup Guide

AI-powered chatbot that answers questions about legal case documents (PDF or TXT).

---

## 📁 Project Structure

```
legal_qa_project/
│
├── main.py            ← Main chatbot program
├── requirements.txt   ← All dependencies
├── .env               ← Your API key goes here (never share this!)
└── README.md          ← This file
```

---

## ⚙️ Setup (Do this once)

### Step 1 — Make sure Python 3.9+ is installed
```bash
python --version
```

### Step 2 — Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### Step 3 — Install all dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Add your Gemini API Key
1. Go to https://aistudio.google.com
2. Click "Get API key" → Create a new key
3. Open the `.env` file in this folder
4. Replace `your_gemini_api_key_here` with your actual key:

```
GEMINI_API_KEY=AIzaSy...your_real_key...
```

---

## ▶️ Run the Chatbot

```bash
python main.py
```

Then enter the path to your legal PDF or TXT file when prompted.

**Example:**
```
📄 Enter document path (.txt or .pdf): documents/my_case.pdf
```

---

## 💬 Sample Questions to Ask

| Question | Expected Answer |
|---|---|
| Who filed the appeal? | Union of India filed the appeal. |
| Was the appeal successful? | No, the appeal was dismissed with costs. |
| What is excise duty applied on? | Excise duty is applied on production, not removal. |
| What did the court decide? | The court dismissed the appeal and upheld the concession. |
| Why was the demand notice quashed? | Because the sugar was produced in the eligible season. |

---

## ❌ Troubleshooting

| Error | Fix |
|---|---|
| `GEMINI_API_KEY not set` | Check your `.env` file has the correct key |
| `404 model not found` | Change model in `main.py` to `gemini-2.0-flash` |
| `PDF unreadable` | Make sure the PDF is not scanned/image-only |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |

---

## 🔒 Security Note
Never commit your `.env` file to GitHub.
Add `.env` to your `.gitignore` if using Git.
