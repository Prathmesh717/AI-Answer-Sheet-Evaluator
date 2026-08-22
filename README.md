# 📝 AI-Based Answer Sheet Evaluation System

An **AI-powered automated answer sheet evaluation platform** that evaluates student answer sheets against a master answer key using **semantic similarity, keyword coverage, structural analysis, and intelligent PDF/OCR processing**.

The system is designed to reduce manual evaluation effort while providing consistent, scalable, and data-driven assessment of student answers.

---

## 🚀 Overview

Traditional answer-sheet evaluation is time-consuming and can introduce inconsistencies between evaluators.

This project automates the evaluation workflow:

```text
Master Answer Key
       │
       ▼
Student Answer Sheets
       │
       ▼
PDF Text Extraction / OCR
       │
       ▼
Question & Answer Parsing
       │
       ▼
AI-Based Evaluation Engine
       │
       ├── Semantic Similarity
       ├── Keyword Coverage
       ├── Structure Analysis
       └── Answer Length Analysis
       │
       ▼
Marks + Feedback + Analytics
       │
       ├── Dashboard
       ├── Excel Reports
       ├── PDF Reports
       └── Email Results
```

---

# ✨ Key Features

## 🤖 AI-Based Answer Evaluation

The evaluation engine compares student answers against the master answer key using multiple criteria.

### Evaluation Criteria

| Criterion                | Weight |
| ------------------------ | -----: |
| Semantic Similarity      |    60% |
| Keyword Coverage         |    25% |
| Structure & Completeness |    10% |
| Length Appropriateness   |     5% |

The weighted evaluation helps the system assess **meaning and conceptual understanding**, rather than relying only on exact keyword matching.

---

## 🧠 Semantic Similarity

The system uses:

**Sentence Transformers — `all-MiniLM-L6-v2`**

to generate semantic embeddings and calculate similarity between:

```text
Master Answer
      ↓
Student Answer
      ↓
Sentence Embeddings
      ↓
Cosine Similarity
      ↓
Semantic Score
```

This allows answers with different wording but similar meaning to receive appropriate credit.

---

## 🔑 Keyword Coverage

The system identifies important technical terms associated with different subjects and checks whether the student's answer covers the expected concepts.

Supported subject areas include:

* Artificial Intelligence
* Cyber Security
* Blockchain
* Software Engineering
* Constitutional Law

The framework can be extended with additional subjects and technical terminology.

---

## 📄 PDF Answer Sheet Processing

Students can submit answer sheets as PDF files.

The system supports:

* Digital PDFs
* Scanned PDFs
* OCR-based extraction
* Batch PDF processing
* Temporary file processing
* Automatic question-answer parsing

# 📊 Evaluation & Analytics

The platform provides detailed evaluation results including:

* Student name
* Roll number
* Question-wise marks
* Total marks
* Maximum marks
* Percentage
* Evaluation feedback
* Subject-wise performance
* Class-level analytics

The frontend includes analytics and visualization components for reviewing evaluation results.

---

# 📈 Question-Level Evaluation

The system supports different question types.

### Main Questions

```text
Q1 → 10 marks
Q2 → 10 marks
Q3 → 10 marks
```

### Sub-Questions

```text
Q1a → 5 marks
Q1b → 5 marks
Q2a → 5 marks
```

The evaluator automatically determines the question type and corresponding maximum marks.

# 📑 Automated Reports

Evaluation results can be saved and exported for further analysis.

Supported outputs include:

* Excel evaluation reports
* PDF documents
* Detailed feedback
* Consolidated results

The system can also optionally send evaluation results through email.

---

# 🔐 Authentication

The application includes user authentication with:

* User registration
* Login
* Protected routes
* JWT-based authentication
* Password hashing
* User-specific evaluation access

---

# 💳 Subscription & Payments

The application includes subscription functionality with **Razorpay** integration.

The frontend provides pricing and subscription-related components, allowing the platform to be extended into a SaaS-based evaluation service.


## AI / Machine Learning

* **Sentence Transformers**
* **all-MiniLM-L6-v2**
* **PyTorch**
* **NVIDIA NIM**
* Semantic similarity
* Natural language processing

## PDF & OCR

* **PyPDF2**
* **pdf2image**
* **Pillow**
* **ReportLab**
* NVIDIA NIM Vision OCR

## Database

* **MongoDB**
* **PyMongo**
* **Motor**

## Authentication

* **JWT**
* **python-jose**
* **Passlib / bcrypt**

## Payments

* **Razorpay**

## Data Processing

* **Pandas**
* **NumPy**
* **OpenPyXL**

---

# 📂 Project Structure

```text
AI-Based-Answersheet-Eval-main/
│
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── evaluation_engine.py
│   │   ├── models.py
│   │   │
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── evaluation.py
│   │       ├── evaluations.py
│   │       ├── ocr.py
│   │       └── payments.py
│   │
│   ├── main.py
│   ├── requirements.txt
│   ├── nvidia_nim_migration_guide.py
│   └── nvidia_nim_ocr_processor.py
│
├── public/
│   ├── index.html
│   ├── favicon.ico
│   ├── logo192.png
│   ├── logo512.png
│   └── manifest.json
│
├── src/
│   ├── components/
│   │   ├── Analytics.jsx
│   │   ├── EvaluationPanel.jsx
│   │   ├── PDFTools.jsx
│   │   ├── Settings.jsx
│   │   ├── Sidebar.jsx
│   │   └── SubjectManager.jsx
│   │
│   ├── Pages/
│   │   ├── Dashboard.jsx
│   │   ├── HomePage.jsx
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   └── Pricingpage.jsx
│   │
│   ├── context/
│   │   └── AppContext.jsx
│   │
│   ├── services/
│   │   └── api.js
│   │
│   ├── subscription/
│   │   ├── SubscriptionContext.jsx
│   │   └── plans.js
│   │
│   ├── App.js
│   ├── App.css
│   └── index.js
│
├── evaluation_saver.py
├── package.json
├── package-lock.json
└── README.md
```

# ▶️ Run the Backend

From the `backend` directory:

```bash
uvicorn main:app --reload
```

The backend will run at:

```text
http://localhost:8000
```

FastAPI Swagger documentation:

```text
http://localhost:8000/docs
```

---

# ⚛️ Frontend Setup

Open another terminal and navigate to the project root:

```bash
cd AI-Based-Answersheet-Eval-main
```

Install dependencies:

```bash
npm install
```

Start the React application:

```bash
npm start
```

The frontend will normally be available at:

```text
http://localhost:3000
```

---

# 🔌 Core API Endpoints

### Authentication

```text
POST /auth/register
POST /auth/login
```

### Answer Evaluation

```text
POST /evaluation/evaluate-subject
POST /evaluation/evaluate-multi-subject
POST /evaluation/evaluate-batch
```

### OCR

```text
POST /ocr/extract-text
POST /ocr/extract-text-batch
```

### Evaluation History

```text
GET /evaluations
```

### Payments

Payment-related endpoints are provided through the payments router.

For the complete API specification, open:

```text
http://localhost:8000/docs
```

---

# 🧪 Example Evaluation Workflow

### 1. Create an account

Register through the application.

### 2. Login

Authenticate using your credentials.

### 3. Select a subject

Example:

```text
Artificial Intelligence
```

### 4. Upload the master answer key

Upload the professor's/reference answer PDF.

### 5. Upload student answer sheets

Upload one or more student PDFs.

### 6. Start evaluation

The system:

```text
Extracts PDF text
      ↓
Runs OCR when necessary
      ↓
Detects questions
      ↓
Extracts student answers
      ↓
Calculates semantic similarity
      ↓
Checks keyword coverage
      ↓
Analyzes structure
      ↓
Calculates marks
      ↓
Generates feedback
```

### 7. Review results

The dashboard displays student performance and evaluation analytics.

### 8. Export results

Results can be saved for further analysis and reporting.

---

# 📊 Evaluation Algorithm

For every student answer, the system calculates a weighted score:

```text
Final Score =
    Semantic Score × 0.60
  + Keyword Score  × 0.25
  + Structure Score × 0.10
  + Length Score   × 0.05
```

This approach combines **semantic understanding with content coverage and answer quality**.

---

# 🎯 Benefits

### For Teachers

* Reduces manual evaluation time
* Provides consistent evaluation
* Supports batch processing
* Generates structured reports
* Provides student analytics

### For Students

* Faster feedback
* Question-wise performance
* Detailed evaluation results
* Transparent scoring

### For Institutions

* Scalable evaluation infrastructure
* Centralized evaluation records
* Analytics-driven assessment
* Potential SaaS deployment

---








