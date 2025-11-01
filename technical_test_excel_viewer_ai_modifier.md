
# Technical Test — Excel Viewer & AI Modifier

### 🧠 Tech Stack

- **Frontend:** React + Next.js + TypeScript
- **Backend:** Python + FastAPI

---

## ⏱️ Estimated Time

**≈ 5 hours**

---

## 🧾 Problem Description

You are building a lightweight **Excel Viewer & Modifier** web app.

The goal is to let users **view**, **navigate**, and **export** enriched Excel files using an **AI-assisted backend**.

Users should be able to:

- Upload an Excel file (`.xlsx`)
- View the list of available sheets
- Switch between sheets and see their data as a table
- Click **“Export Modified Excel”** to generate a new version enriched by an LLM (based on a provided JSON rules file)

> 💡 The focus is on data handling and clear logic — not on UI polish or formatting details.

---

## 📎 Provided Assets

You will find:

- **`test_1.xlsx`** → multi-sheet Excel file with real data
- **`sample_test3.json`** → JSON rules for enrichment (how to insert or update data)

Example:

`sample_test3.json` contains instructions such as “Add LIMITES and DEDUCIBLES columns based on the unit type.”

---

## ✅ Requirements

### **Frontend (Next.js + TypeScript)**

Users should be able to:

- Upload an `.xlsx` file
- Display all sheet names as **tabs**
- On sheet selection:
    - Render the data in a **simple HTML table**
- Click **“Export Modified Excel”**
    - Send the file and selected sheet to the backend
    - Download the AI-modified Excel returned by the API

**Notes**

- Keep styling minimal and clean (plain Tailwind or CSS ok)
- Use `xlsx` (SheetJS) to parse Excel client-side for display
- Handle basic loading and error states

---

### **Backend (FastAPI)**

#### Required Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/sample-data` | Returns the JSON rules for enrichment |
| `POST` | `/export` | Receives Excel + sheet name → applies LLM → returns modified Excel |

**Backend responsibilities**

- Read the uploaded Excel (using `pandas` or `openpyxl`)
- Send sheet data + JSON rules to an LLM (e.g., OpenAI API)
- The model returns a transformed dataset (with new or modified columns)
- Generate and return a new `.xlsx` file for download

**Recommended libraries**

- `pandas` or `openpyxl` for Excel reading/writing
- `openai` or `requests` for API calls

> Formatting preservation is optional — focus on data correctness and flow.

---

## 💡 LLM Integration (Example)

Prompt idea:

```python
prompt = f"You are an AI underwriter in fleet that enriches Excel data.\nHere is the JSON rule set: {rules_json}\nHere is the current sheet data: {sheet_data}\nApply the rules and return the updated rows as JSON."
```

You can either:

- Mock the LLM response (apply rules directly), **or**
- Use a real model call if you have an API key.

---

## 📦 Deliverables

Your GitHub repository should contain:

```
/frontend  → Next.js app
/backend   → FastAPI service
```

Include a **README.md** with:

- Setup and run instructions
- Architecture overview (how front and back communicate)
- Short explanation of your AI logic (mocked or real)

---

## 🎯 Evaluation Criteria

| Area | What We Look For |
| --- | --- |
| **Frontend** | Excel handling, sheet navigation, clean UX |
| **Backend** | Data parsing, LLM integration, modular design |
| **AI Logic** | Smart use of the JSON enrichment rules |
| **Code Quality** | Typing, clarity, error handling |
| **Bonus** | Docker setup, unit tests, or architecture diagram |

---

## 📌 Submission

Please provide:

1. A **GitHub repository** link  
2. A short **Loom/video (2–3 min)** explaining:  
   - Your architecture and main decisions  
   - How the AI modifies the Excel  
   - What you would improve with more time
