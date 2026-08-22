"""
evaluation_engine.py
Core evaluation logic extracted from s10.py — no GUI, no tkinter dependencies.
Used by FastAPI routes.
"""

import re
import os
import io
import base64
import time
import json
import tempfile
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from collections import defaultdict

import requests
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter

# ── Optional heavy deps ──────────────────────────────────────────────────────
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    import torch
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# ── Poppler (Windows only) ────────────────────────────────────────────────────
POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"   # Set via env var on Windows


# ===========================================================================
# FAIR EVALUATION ENGINE
# ===========================================================================
class FairEvaluationEngine:
    """
    Weighted multi-criteria answer evaluation:
      Semantic  60 %  |  Keywords  25 %  |  Structure  10 %  |  Length  5 %
    Mark distribution:
      Main questions  (Q1, Q2 …)   → 10 marks each
      Sub-questions   (Q1a, Q2b …) →  5 marks each
    """

    def __init__(self):
        self.model = None
        self.semantic_enabled = SEMANTIC_AVAILABLE

        self.weights = {
            "semantic": 0.60,
            "keyword": 0.25,
            "structure": 0.10,
            "length": 0.05,
        }
        self.question_weights = {"main": 10, "sub": 5}
        self.technical_terms = self._init_technical_terms()

        if self.semantic_enabled:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                print(f"⚠️ Semantic model load failed: {e}")
                self.semantic_enabled = False

    # ── Question type helpers ────────────────────────────────────────────────

    def detect_question_type(self, q_key: str) -> str:
        return "sub" if re.match(r"^\d+[a-z]$", str(q_key).lower().strip()) else "main"

    def get_question_max_marks(self, q_key: str) -> int:
        return self.question_weights[self.detect_question_type(q_key)]

    def calculate_total_possible_marks(self, question_keys) -> int:
        return sum(self.get_question_max_marks(k) for k in question_keys)

    # ── Subject detection ────────────────────────────────────────────────────

    def detect_subject(self, master_answer: str) -> str:
        master_lower = master_answer.lower()
        subject_keywords = {
            "software_engineering": ["software", "engineering", "ftr", "walkthrough", "loc",
                                     "white box", "version control", "cohesion", "coupling",
                                     "spiral", "reengineering", "srs", "testing", "code"],
            "cyber_security": ["cyber", "security", "cia", "confidentiality", "integrity",
                               "availability", "hacking", "phishing", "malware",
                               "digital signature", "firewall", "encryption", "forensics"],
            "artificial_intelligence": ["artificial intelligence", "machine learning", "neural",
                                        "nlp", "natural language", "computer vision",
                                        "supervised", "unsupervised", "reinforcement", "overfitting"],
            "blockchain": ["blockchain", "block", "decentralization", "merkle", "proof of work",
                           "proof of stake", "smart contract", "51%", "distributed ledger",
                           "bitcoin", "ethereum"],
            "constitutional_law": ["constitutional", "law", "rule of law", "separation of powers",
                                   "fundamental rights", "directive principles", "judicial review",
                                   "contract", "criminal", "civil"],
        }
        best, max_score = "software_engineering", 0
        for subject, kws in subject_keywords.items():
            score = sum(1 for kw in kws if kw in master_lower)
            if score > max_score:
                max_score, best = score, subject
        return best

    # ── Text helpers ─────────────────────────────────────────────────────────

    def preprocess_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r"[^\w\s\.\,\?\!\-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def extract_key_terms(self, text: str, subject: str = None):
        text_lower = self.preprocess_text(text)
        if not subject:
            subject = self.detect_subject(text)
        subject_terms = self.technical_terms.get(subject, {})
        all_terms = [t.lower() for cats in subject_terms.values() for t in cats]
        found = set()
        for term in all_terms:
            if term in text_lower:
                found.add(term)
            elif " " in term and term.replace(" ", "") in text_lower.replace(" ", ""):
                found.add(term)
        return found, subject

    # ── Individual scorers ───────────────────────────────────────────────────

    def calculate_semantic_similarity(self, master: str, student: str) -> float:
        if not self.semantic_enabled or not self.model:
            return self._word_overlap(master, student) * 0.8
        try:
            mp = self.preprocess_text(master)
            sp = self.preprocess_text(student)
            if not sp:
                return 0.0
            embs = self.model.encode([mp, sp], convert_to_tensor=True)
            sim = float(st_util.pytorch_cos_sim(embs[0], embs[1])[0][0])
            score = sim * 10
            if sim > 0.85:
                score = min(10, score * 1.1)
            return round(max(0, min(10, score)), 2)
        except Exception:
            return self._word_overlap(master, student) * 0.8

    def _word_overlap(self, master: str, student: str) -> float:
        mw = set(self.preprocess_text(master).split())
        sw = set(self.preprocess_text(student).split())
        if not mw:
            return 0.0
        return (len(mw & sw) / len(mw)) * 10

    def calculate_keyword_coverage(self, master: str, student: str) -> float:
        subject = self.detect_subject(master)
        mt, _ = self.extract_key_terms(master, subject)
        st, _ = self.extract_key_terms(student, subject)
        if not mt:
            return 5.0
        covered = mt & st
        score = (len(covered) / len(mt)) * 10
        extra = st - mt
        if extra:
            score = min(10, score + min(1.0, len(extra) * 0.1))
        return round(score, 2)

    def calculate_structure_score(self, master: str, student: str) -> float:
        if not student.strip():
            return 0.0
        score = 5.0
        paras = student.split("\n\n")
        if len(paras) >= 2:
            score += 1.0
        if len(paras) >= 3:
            score += 0.5
        if re.search(r"[•\-*]\s|\d+\.\s", student):
            score += 1.5
        if re.search(r"\b(is|are|refers to|defined as|means)\b", student.lower()):
            score += 1.0
        if re.search(r"\b(example|instance|such as|e\.g\.|like)\b", student.lower()):
            score += 1.0
        if any(c in student for c in [":", ";", "(", ")", "-"]):
            score += 0.5
        if len(student.split()) > 100 and len(paras) == 1:
            score -= 1.0
        return round(max(0, min(10, score)), 2)

    def calculate_length_score(self, master: str, student: str) -> float:
        if not student or not student.strip():
            return 0.0
        ml, sl = len(master.strip()), len(student.strip())
        min_ok = max(15, ml * 0.3)
        max_ok = ml * 1.5
        if sl < min_ok:
            score = (sl / min_ok) * 5
        elif sl <= max_ok:
            ratio = sl / ml
            score = 10.0 if 0.7 <= ratio <= 1.2 else 9.0
        else:
            score = 8.0
        return round(max(0, min(10, score)), 2)

    # ── Main evaluation entry point ──────────────────────────────────────────

    def evaluate_answer_fair(self, master: str, student: str, question_key=None):
        if not student or not student.strip():
            return 0.0, "No answer provided"

        sem = self.calculate_semantic_similarity(master, student)
        kw  = self.calculate_keyword_coverage(master, student)
        st  = self.calculate_structure_score(master, student)
        ln  = self.calculate_length_score(master, student)

        normalized = (sem * self.weights["semantic"] +
                      kw  * self.weights["keyword"] +
                      st  * self.weights["structure"] +
                      ln  * self.weights["length"])

        max_marks = self.get_question_max_marks(question_key) if question_key else 10
        final = round((normalized / 10) * max_marks, 2)
        feedback = self._generate_feedback(sem, kw, st, ln, normalized)
        return final, feedback

    def _generate_feedback(self, sem, kw, st, ln, total) -> str:
        parts = []
        if total >= 9:   parts.append("🎯 Outstanding answer!")
        elif total >= 7: parts.append("👍 Very good answer")
        elif total >= 5: parts.append("📘 Satisfactory answer")
        elif total >= 3: parts.append("📝 Needs improvement")
        else:            parts.append("❌ Incomplete answer")

        if sem >= 8:   parts.append("🌟 Excellent understanding")
        elif sem >= 6: parts.append("📚 Good grasp of main ideas")
        elif sem >= 4: parts.append("📝 Basic understanding shown")
        else:          parts.append("📖 Improve conceptual understanding")

        if kw >= 7:  parts.append("🔑 Strong technical terminology")
        elif kw >= 5: parts.append("📌 Adequate technical terms")
        else:         parts.append("💡 Missing key technical terms")

        if st >= 8:  parts.append("📋 Well-organized answer")
        elif st >= 6: parts.append("📄 Acceptable organization")
        else:         parts.append("✏️ Better structure needed")

        return "; ".join(parts[:4])

    # ── Grade helper ─────────────────────────────────────────────────────────

    @staticmethod
    def calculate_grade(percentage: float) -> str:
        if percentage >= 90: return "A+"
        if percentage >= 80: return "A"
        if percentage >= 70: return "B+"
        if percentage >= 60: return "B"
        if percentage >= 50: return "C"
        if percentage >= 40: return "D"
        return "F"

    # ── Technical terms dictionary ────────────────────────────────────────────

    def _init_technical_terms(self) -> dict:
        return {
            "software_engineering": {
                "FTR": ["formal","technical","review","structured","agenda","leader","recorder",
                        "report","software","quality","control"],
                "walkthrough": ["informal","peer","review","author","guides","knowledge",
                                "sharing","brainstorming","code","logic"],
                "LOC": ["lines","code","size","metric","effort","estimate","COCOMO",
                        "productivity","measure","software"],
                "white_box": ["structural","internal","logic","control flow","basis path",
                              "cyclomatic","condition","data flow","loop","statement","branch",
                              "coverage","testing"],
                "version_control": ["baseline","change request","impact analysis","CRB",
                                    "check-out","modification","audit","check-in","repository",
                                    "configuration"],
                "cohesion": ["functional","sequential","temporal","communicational","procedural",
                             "logical","coincidental","strength","module","internal"],
                "coupling": ["data","stamp","control","common","content","interdependence",
                             "independence","modules","external"],
                "spiral": ["evolutionary","iterative","risk","quadrant","planning","prototyping",
                           "engineering","evaluation","cumulative","model"],
                "reengineering": ["inventory","document","reverse","code","data","forward",
                                  "restructuring","legacy","maintainability"],
                "SRS": ["introduction","functional","non-functional","requirements","interface",
                        "database","security","availability","hospital","management"],
            },
            "cyber_security": {
                "cyber_security": ["confidentiality","integrity","availability","CIA","protection",
                                   "threat","attack","security","systems","networks","data"],
                "digital_signature": ["encryption","private key","public key","authentication",
                                      "non-repudiation","integrity","certificate","digital","verify"],
                "firewall": ["network","traffic","filter","barrier","security","access control",
                             "monitors","prevents"],
                "encryption": ["cipher","decrypt","key","confidentiality","algorithm","secure",
                                "convert","unreadable"],
                "ethical_hacking": ["white hat","authorized","vulnerability","penetration",
                                    "reconnaissance","exploit","testing","permission"],
            },
            "artificial_intelligence": {
                "ai": ["intelligent","machine learning","deep learning","neural","algorithm",
                       "automation","cognitive","adaptive","systems","reasoning","perception"],
                "ml": ["supervised","unsupervised","reinforcement","training","model","prediction",
                       "classification","regression","patterns","data"],
                "neural_network": ["neurons","layers","weights","activation","forward propagation",
                                   "backpropagation","input","hidden","output","connections"],
                "nlp": ["natural language","processing","semantic","syntax","tokenization",
                        "embedding","transformer","chatbot","sentiment","parsing"],
                "overfitting": ["noise","generalization","complex","training","validation",
                                "regularization","dropout","bias","variance"],
            },
            "blockchain": {
                "blockchain": ["distributed","ledger","decentralized","blocks","chain",
                               "transactions","immutable","transparent","consensus","nodes"],
                "smart_contract": ["self-executing","program","automated","conditions",
                                   "intermediaries","ethereum","code","agreement"],
                "proof_of_work": ["mining","puzzle","nonce","difficulty","hash","compute",
                                  "energy","competition","bitcoin"],
            },
            "constitutional_law": {
                "rule_of_law": ["supremacy of law","equality","accountability","fairness",
                                "justice","arbitrary","legal certainty","transparency"],
                "fundamental_rights": ["right to equality","freedom of speech","right to life",
                                       "constitutional remedies","enforceable","part III"],
                "contract_law": ["offer","acceptance","consideration","capacity","free consent",
                                 "lawful object","agreement","enforceable"],
            },
        }


# ===========================================================================
# PDF PROCESSOR  (NVIDIA NIM OCR)
# ===========================================================================
class PDFProcessor:
    NVIDIA_URL   = "https://integrate.api.nvidia.com/v1/chat/completions"
    NVIDIA_MODEL = "meta/llama-3.2-11b-vision-instruct"
    OCR_PROMPT = (
        "You are a precise OCR engine for handwritten university exam answer sheets. "
        "Your ONLY job is to transcribe exactly what is physically written on the page.\n\n"
        "STRICT RULES:\n"
        "1. Copy text EXACTLY as handwritten — do NOT fix spelling, grammar, or punctuation.\n"
        "2. The left margin may contain labels like 'Q1 a:' — copy these EXACTLY.\n"
        "3. Do NOT invent or reformat any labels.\n"
        "4. Keep the answer text that follows each label as a single continuous block.\n"
        "5. Do NOT split a single answer into multiple sub-entries.\n"
        "6. If text is truly unreadable write [illegible] — never guess.\n"
        "7. Output ONLY the raw transcribed text. No commentary, no markdown."
    )

    def __init__(self, nvidia_api_key: str):
        self.nvidia_api_key = nvidia_api_key
        self._headers = {
            "Authorization": f"Bearer {nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── Text extraction (digital PDF fast-path) ──────────────────────────────

    def extract_pdf_text(self, pdf_path: str) -> str:
        text = ""
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    pt = page.extract_text()
                    if pt:
                        text += pt + "\n"
        except Exception as e:
            print(f"PyPDF2 error: {e}")
        return text

    # ── OCR path ─────────────────────────────────────────────────────────────

    def extract_text_with_ocr(self, pdf_path: str, log_fn=None) -> str | None:
        def log(msg):
            if log_fn:
                log_fn(msg)
            print(msg)

        if not PDF2IMAGE_AVAILABLE or not PIL_AVAILABLE:
            log("❌ pdf2image or Pillow not installed.")
            return None

        log(f"🚀 NVIDIA NIM OCR: {os.path.basename(pdf_path)}")
        images = self._pdf_to_images(pdf_path, log)
        if images is None:
            return None

        total = len(images)
        log(f"📄 {total} page(s). Sending to NVIDIA NIM…")

        parts = []
        for n, img in enumerate(images, 1):
            log(f"🧠 OCR page {n}/{total}…")
            text = self._ocr_page(img, n, log)
            if text:
                parts.append(f"--- Page {n} ---\n{text}")
                log(f"  ✅ Page {n}: {len(text)} chars")
            else:
                log(f"  ⚠️ Page {n}: no text extracted")
            if n < total:
                time.sleep(2)

        if not parts:
            return None

        combined = "\n\n".join(parts)
        combined = re.sub(r"[ \t]+", " ", combined)
        combined = re.sub(r"\n{3,}", "\n\n", combined)
        log(f"✅ OCR complete — {len(combined)} chars from {total} page(s).")
        return combined.strip()

    def _pdf_to_images(self, pdf_path: str, log_fn):
        poppler = POPPLER_PATH if POPPLER_PATH and os.path.isdir(POPPLER_PATH) else None
        try:
            kwargs = {"dpi": 200, "fmt": "jpeg", "thread_count": 2}
            if poppler:
                kwargs["poppler_path"] = poppler
            return convert_from_path(pdf_path, **kwargs)
        except Exception as e:
            log_fn(f"❌ PDF→Image failed: {e}")
            return None

    def _image_to_b64(self, img) -> str:
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        w, h = img.size
        if w * h > 1_500_000:
            r = (1_500_000 / (w * h)) ** 0.5
            img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    def _ocr_page(self, img, page_num: int, log_fn) -> str:
        b64 = self._image_to_b64(img)
        payload = {
            "model": self.NVIDIA_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": self.OCR_PROMPT},
            ]}],
            "max_tokens": 2048,
            "temperature": 0.0,
            "top_p": 1.0,
            "stream": False,
        }
        for attempt in range(1, 3):
            try:
                resp = requests.post(self.NVIDIA_URL, headers=self._headers,
                                     json=payload, timeout=90)
                if resp.status_code == 200:
                    choices = resp.json().get("choices", [])
                    return choices[0].get("message", {}).get("content", "").strip() if choices else ""
                if resp.status_code == 429:
                    wait = 20 * attempt
                    log_fn(f"⏳ Rate limited — waiting {wait}s…")
                    time.sleep(wait)
                    continue
                if resp.status_code == 401:
                    log_fn("❌ Invalid NVIDIA API key.")
                    return ""
                if attempt == 1:
                    time.sleep(5)
            except requests.exceptions.Timeout:
                if attempt == 1:
                    time.sleep(5)
            except Exception as e:
                log_fn(f"❌ {e}")
                return ""
        return ""


# ===========================================================================
# ANSWER PARSER
# ===========================================================================
class AnswerParser:

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"(Q\d+[a-zA-Z]?)", r"\n\1:", text)
        return text.strip()

    @staticmethod
    def parse_answers(text: str) -> dict:
        answers = {}
        pattern = r"Q(\d+)\s*([a-zA-Z]?)\s*[:\.]?\s*(.*?)(?=Q\d+\s*[a-zA-Z]?\s*[:\.]|$)"
        for q_num, sub, ans in re.findall(pattern, text, re.DOTALL | re.IGNORECASE):
            ans = ans.strip()
            key = f"{int(q_num)}{sub.lower().strip()}" if sub.strip() else str(int(q_num))
            if ans and len(ans) > 3:
                answers[key] = ans

        # Markdown style ##Q1
        pattern2 = r"#+[\s]*Q(\d+)\s*([a-zA-Z]?)\s*[:\.]?\s*(.*?)(?=#+[\s]*Q\d+\s*[a-zA-Z]?\s*[:\.]|$)"
        for q_num, sub, ans in re.findall(pattern2, text, re.DOTALL | re.IGNORECASE):
            ans = ans.strip()
            key = f"{int(q_num)}{sub.lower().strip()}" if sub.strip() else str(int(q_num))
            if ans and len(ans) > 10 and key not in answers:
                answers[key] = ans

        return answers

    @staticmethod
    def extract_student_info(text: str) -> dict:
        info = {"name": "", "roll_no": "", "email": ""}

        for pat in [r"Student[^:\n]*:\s*([^\n(]+)", r"Name[^:\n]*:\s*([^\n(]+)"]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                name = re.sub(r"\s*\(.*\)", "", m.group(1).strip())
                if len(name) > 2:
                    info["name"] = name
                    break

        for pat in [r"Roll[^:\n]*:\s*([A-Za-z0-9-]+)", r"No[.\s]*:?\s*(\d+)"]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                info["roll_no"] = m.group(1).strip()
                break

        m = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
        if m:
            info["email"] = m.group(1).strip().lower()

        if not info["name"]:
            info["name"] = f"Student_{hash(text) % 1000:03d}"
        if not info["roll_no"]:
            info["roll_no"] = f"ID_{hash(text) % 10000:04d}"
        if not info["email"]:
            info["email"] = f"student_{info['roll_no']}@example.com"

        return info


# ===========================================================================
# EMAIL SENDER
# ===========================================================================
class EmailSender:

    def __init__(self, sender_email: str, app_password: str):
        self.sender_email = sender_email
        self.app_password = app_password
        self.log = []

    def test_connection(self):
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
                s.login(self.sender_email, self.app_password)
            return True, "Email connection successful"
        except Exception as e:
            return False, f"Email connection failed: {e}"

    def send_results_email(self, student_data: dict, subject_results: dict,
                           detailed_results: dict = None,
                           results_file: str = None) -> tuple:
        try:
            name  = student_data["Name"]
            email = student_data["Email"]
            roll  = student_data["Roll No"]

            if not email or "@" not in email:
                return False, f"No valid email for {name}"

            msg = MIMEMultipart()
            msg["From"]    = self.sender_email
            msg["To"]      = email
            msg["Subject"] = f"📊 Exam Results — {name}"

            subject_rows = ""
            overall_marks = overall_max = 0
            for subj, scores in subject_results.items():
                tm = scores.get("Total Marks", 0)
                mp = scores.get("Max Possible", 0)
                pct = scores.get("Percentage", 0)
                grade = scores.get("Grade", "N/A")
                overall_marks += tm
                overall_max += mp
                colour = "#27ae60" if grade in ["A+", "A", "B+"] else "#e74c3c"
                subject_rows += f"""
                <tr>
                  <td style="padding:8px;border-bottom:1px solid #ddd;"><b>{subj}</b></td>
                  <td style="padding:8px;border-bottom:1px solid #ddd;">{tm:.2f}/{mp}</td>
                  <td style="padding:8px;border-bottom:1px solid #ddd;">{pct:.2f}%</td>
                  <td style="padding:8px;border-bottom:1px solid #ddd;color:{colour};font-weight:bold;">{grade}</td>
                </tr>"""

            overall_pct = round(overall_marks / overall_max * 100, 2) if overall_max else 0
            overall_grade = FairEvaluationEngine.calculate_grade(overall_pct)

            html = f"""
            <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;">
              <div style="background:#2c3e50;color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h2>📊 Exam Evaluation Results</h2>
                <p>Student: <b>{name}</b> | Roll No: <b>{roll}</b></p>
              </div>
              <div style="padding:20px;background:#f8f9fa;">
                <table style="width:100%;border-collapse:collapse;">
                  <tr style="background:#ecf0f1;">
                    <th style="padding:8px;text-align:left;">Subject</th>
                    <th style="padding:8px;text-align:left;">Marks</th>
                    <th style="padding:8px;text-align:left;">Percentage</th>
                    <th style="padding:8px;text-align:left;">Grade</th>
                  </tr>
                  {subject_rows}
                  <tr style="background:#2c3e50;color:white;font-weight:bold;">
                    <td style="padding:8px;">OVERALL</td>
                    <td style="padding:8px;">{overall_marks:.2f}/{overall_max}</td>
                    <td style="padding:8px;">{overall_pct:.2f}%</td>
                    <td style="padding:8px;">{overall_grade}</td>
                  </tr>
                </table>
              </div>
              <div style="padding:15px;background:#ecf0f1;border-radius:0 0 8px 8px;font-size:12px;color:#7f8c8d;">
                This is an automated result email generated by the FAIR Evaluation System.
              </div>
            </body></html>"""

            msg.attach(MIMEText(html, "html"))

            if results_file and os.path.exists(results_file):
                with open(results_file, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition",
                                f"attachment; filename={os.path.basename(results_file)}")
                msg.attach(part)

            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
                s.login(self.sender_email, self.app_password)
                s.sendmail(self.sender_email, email, msg.as_string())

            entry = {"student": name, "roll": roll, "email": email,
                     "status": "sent", "timestamp": datetime.now().isoformat()}
            self.log.append(entry)
            return True, f"Email sent to {email}"

        except Exception as e:
            return False, f"Email failed: {e}"


# ===========================================================================
# MULTI-SUBJECT EVALUATOR  (orchestrator)
# ===========================================================================
class MultiSubjectEvaluator:
    """
    Orchestrates PDF extraction, answer parsing, FAIR evaluation,
    result saving, and email dispatch.  No GUI involved.
    """

    def __init__(self, nvidia_api_key: str, sender_email: str,
                 app_password: str, output_dir: str = "extracted_pdfs",
                 use_ocr: bool = True):
        self.output_dir = output_dir
        self.use_ocr = use_ocr
        self.fair_engine = FairEvaluationEngine()
        self.pdf_processor = PDFProcessor(nvidia_api_key)
        self.email_sender = EmailSender(sender_email, app_password)
        os.makedirs(output_dir, exist_ok=True)

    # ── Text extraction ──────────────────────────────────────────────────────

    def extract_text(self, pdf_path: str, label: str = "", log_fn=None) -> str:
        text = self.pdf_processor.extract_pdf_text(pdf_path)
        if text and len(text.strip()) > 100:
            return AnswerParser.clean_text(text)
        if self.use_ocr:
            ocr = self.pdf_processor.extract_text_with_ocr(pdf_path, log_fn)
            if ocr:
                return AnswerParser.clean_text(ocr)
        return text

    # ── Single subject evaluation ────────────────────────────────────────────

    def evaluate_subject(self, subject_name: str, master_pdf_path: str,
                         student_pdf_paths: list, log_fn=None) -> list:

        def log(msg):
            if log_fn:
                log_fn(msg)
            print(msg)

        log(f"\n📚 EVALUATING: {subject_name}")

        master_text = self.extract_text(master_pdf_path, "Master", log)
        if not master_text:
            raise ValueError(f"Could not extract text from master PDF for {subject_name}")

        master_answers = AnswerParser.parse_answers(master_text)
        if not master_answers:
            raise ValueError(f"No questions found in master PDF for {subject_name}")

        q_keys = list(master_answers.keys())
        total_possible = self.fair_engine.calculate_total_possible_marks(q_keys)
        log(f"✓ {len(master_answers)} questions | {total_possible} total marks possible")

        results = []
        for i, pdf_path in enumerate(student_pdf_paths, 1):
            fname = os.path.basename(pdf_path)
            log(f"\n🔍 [{i}/{len(student_pdf_paths)}] {fname}")

            student_text = self.extract_text(pdf_path, fname, log)
            if not student_text:
                log(f"  ✗ Failed to extract text from {fname}")
                continue

            sinfo = AnswerParser.extract_student_info(student_text)
            sanswers = AnswerParser.parse_answers(student_text)

            total_score = 0.0
            q_scores = {}
            q_feedback = {}
            answered = 0

            for q_key, m_ans in master_answers.items():
                s_ans = sanswers.get(q_key, "")
                score, feedback = self.fair_engine.evaluate_answer_fair(m_ans, s_ans, q_key)
                max_q = self.fair_engine.get_question_max_marks(q_key)
                q_scores[f"Q{q_key}"] = score
                q_feedback[f"Q{q_key}"] = {"score": score, "max_marks": max_q, "feedback": feedback}
                total_score += score
                if s_ans:
                    answered += 1

            pct = round((total_score / total_possible) * 100, 2) if total_possible > 0 else 0
            grade = FairEvaluationEngine.calculate_grade(pct)
            name = sinfo["name"].split("Emailid:")[0].strip()

            result = {
                "Subject":             subject_name,
                "Name":                name,
                "Roll No":             sinfo["roll_no"],
                "Email":               sinfo["email"],
                "Total Marks":         round(total_score, 2),
                "Max Possible":        total_possible,
                "Percentage":          pct,
                "Grade":               grade,
                "Questions Attempted": answered,
                "Total Questions":     len(master_answers),
                "_question_scores":    q_scores,
                "_feedback":           q_feedback,
            }
            results.append(result)
            log(f"  👤 {name} | Score: {total_score:.1f}/{total_possible} ({pct}%) | Grade: {grade}")

        return results

    # ── Save helpers ─────────────────────────────────────────────────────────

    def save_subject_results(self, subject_name: str, results: list) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_dir, f"{subject_name}_results_{ts}.xlsx")
        rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Results", index=False)
        return path

    def save_consolidated_results(self, all_results: list, subject_names: list) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_dir, f"consolidated_results_{ts}.xlsx")

        students = {}
        for r in all_results:
            rn = r["Roll No"]
            if rn not in students:
                students[rn] = {"Name": r["Name"], "Roll No": rn, "Email": r["Email"], "subjects": {}}
            students[rn]["subjects"][r["Subject"]] = {"marks": r["Total Marks"], "max": r["Max Possible"]}

        rows = []
        for rn, data in students.items():
            row = {"Name": data["Name"], "Roll No": rn, "Email": data["Email"]}
            for sn in subject_names:
                si = data["subjects"].get(sn, {})
                row[f"{sn} (Marks)"] = si.get("marks", "")
                row[f"{sn} (Max)"]   = si.get("max", "")
                row[f"{sn} (%)"]     = round(si["marks"] / si["max"] * 100, 2) if si else ""
            rows.append(row)

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name="All Results", index=False)

        return path

    def save_detailed_feedback(self, feedback: dict) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_dir, f"detailed_feedback_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(feedback, f, indent=2, ensure_ascii=False)
        return path

    # ── Email dispatch ────────────────────────────────────────────────────────

    def send_emails(self, all_results: list, detailed_feedback: dict,
                    results_file: str = None, log_fn=None) -> dict:
        def log(msg):
            if log_fn:
                log_fn(msg)
            print(msg)

        ok, _ = self.email_sender.test_connection()
        if not ok:
            return {"success": 0, "failed": 0, "error": "Email connection failed"}

        # Group by student
        by_student = {}
        for r in all_results:
            rn = r["Roll No"]
            if rn not in by_student:
                by_student[rn] = {"Name": r["Name"], "Email": r["Email"],
                                  "Roll No": rn, "subjects": {}}
            by_student[rn]["subjects"][r["Subject"]] = {
                "Total Marks": r["Total Marks"], "Max Possible": r["Max Possible"],
                "Percentage": r["Percentage"], "Grade": r["Grade"],
            }

        sent = failed = 0
        for rn, sd in by_student.items():
            key = f"{rn}_{sd['Name']}"
            det = detailed_feedback.get(key, {})
            success, msg = self.email_sender.send_results_email(
                sd, sd["subjects"], det, results_file)
            if success:
                sent += 1
                log(f"  ✅ {msg}")
            else:
                failed += 1
                log(f"  ❌ {msg}")

        return {"success": sent, "failed": failed}
