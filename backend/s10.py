import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import json
import base64
import re
import pandas as pd
from datetime import datetime
import tempfile
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from PyPDF2 import PdfReader, PdfWriter
import requests
import glob
import csv
from pathlib import Path
import numpy as np
from collections import defaultdict
import time
import io

# ========================================
# NVIDIA NIM OCR IMPORTS
# ========================================
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("⚠️ pdf2image not installed. Run: pip install pdf2image")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow not installed. Run: pip install pillow")

# ========================================
# NLP SEMANTIC ANALYSIS IMPORTS
# ========================================
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    SEMANTIC_AVAILABLE = True
    print("✅ NLP semantic analysis enabled - using Sentence Transformers")
except ImportError:
    print("⚠️ sentence-transformers not installed. Run: pip install sentence-transformers")
    SEMANTIC_AVAILABLE = False

# ========================================
# CONFIGURATION
# ========================================
NVIDIA_API_KEY = "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"
SENDER_EMAIL = "nitesh.t.mulam2004@gmail.com"
APP_PASSWORD = "gxdd zdyh gfym mlcq"
OUTPUT_DIR = "extracted_pdfs"

# ── Poppler path for Windows ──────────────────────────────────────────────────
# If poppler is NOT in your system PATH, set the full path to its bin/ folder here.
# Example: POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin\pdftoppm.exe"
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Leave as None if poppler is already in your PATH or on Linux/macOS
POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"   # ← Directory, NOT the .exe file

# ========================================
# ENHANCED: FAIR EVALUATION ENGINE WITH MULTI-SUBJECT SUPPORT
# ========================================
class FairEvaluationEngine:
    """
    Comprehensive fair evaluation engine with:
    1. Semantic understanding (60%) - Meaning matching
    2. Keyword coverage (25%) - Technical terms presence
    3. Structure & completeness (10%) - Answer organization
    4. Length appropriateness (5%) - Not too short/long
    
    Question marks distribution:
    - Main questions (Q1, Q2, etc.): 10 marks each
    - Sub-questions (Q1a, Q2b, etc.): 5 marks each
    """
    
    def __init__(self):
        self.model = None
        self.semantic_enabled = SEMANTIC_AVAILABLE
        
        # Fair evaluation weights - Balanced for fairness
        self.weights = {
            'semantic': 0.60,      # 60% - Understanding of concepts
            'keyword': 0.25,       # 25% - Technical term usage
            'structure': 0.10,     # 10% - Answer organization
            'length': 0.05         # 5%  - Appropriate length
        }
        
        # Question type weights for different question formats
        self.question_weights = {
            'main': 10,     # Main question: 10 marks
            'sub': 5        # Sub-question: 5 marks
        }
        
        # Subject-specific technical term dictionaries
        self.technical_terms = self.initialize_technical_terms()
        
        # Initialize semantic model
        if self.semantic_enabled:
            try:
                self.load_model()
            except Exception as e:
                print(f"⚠️ Failed to load semantic model: {e}")
                self.semantic_enabled = False
    
    def detect_question_type(self, question_key):
        """
        Detect if question is main or sub-question
        Main question: just number (1, 2, 3)
        Sub-question: number with letter (1a, 2b, 3c)
        """
        # Convert to string for pattern matching
        q_key_str = str(question_key).lower().strip()
        
        # Pattern for sub-questions: number followed by letter (1a, 2b, 3c)
        sub_q_pattern = r'^\d+[a-z]$'
        
        if re.match(sub_q_pattern, q_key_str):
            return 'sub'
        else:
            return 'main'
    
    def get_question_max_marks(self, question_key):
        """Get maximum marks for a question based on its type"""
        q_type = self.detect_question_type(question_key)
        return self.question_weights[q_type]
    
    def calculate_total_possible_marks(self, question_keys):
        """
        Calculate total possible marks based on question types
        Main questions: 10 marks each
        Sub-questions: 5 marks each
        """
        total = 0
        for q_key in question_keys:
            total += self.get_question_max_marks(q_key)
        return total
    
    def initialize_technical_terms(self):
        """Initialize subject-specific technical term dictionaries"""
        return {
            'software_engineering': {
                'FTR': ['formal', 'technical', 'review', 'structured', 'agenda', 'leader', 'recorder', 'report', 'software', 'quality', 'control'],
                'walkthrough': ['informal', 'peer', 'review', 'author', 'guides', 'knowledge', 'sharing', 'brainstorming', 'code', 'logic'],
                'LOC': ['lines', 'code', 'size', 'metric', 'effort', 'estimate', 'COCOMO', 'productivity', 'measure', 'software'],
                'white_box': ['structural', 'internal', 'logic', 'control flow', 'basis path', 'cyclomatic', 'condition', 'data flow', 'loop', 'statement', 'branch', 'coverage', 'testing'],
                'version_control': ['baseline', 'change request', 'impact analysis', 'CRB', 'check-out', 'modification', 'audit', 'check-in', 'repository', 'configuration'],
                'cohesion': ['functional', 'sequential', 'temporal', 'communicational', 'procedural', 'logical', 'coincidental', 'strength', 'module', 'internal'],
                'coupling': ['data', 'stamp', 'control', 'common', 'content', 'interdependence', 'independence', 'modules', 'external'],
                'spiral': ['evolutionary', 'iterative', 'risk', 'quadrant', 'planning', 'prototyping', 'engineering', 'evaluation', 'cumulative', 'model'],
                'reengineering': ['inventory', 'document', 'reverse', 'code', 'data', 'forward', 'restructuring', 'legacy', 'maintainability'],
                'SRS': ['introduction', 'functional', 'non-functional', 'requirements', 'interface', 'database', 'security', 'availability', 'hospital', 'management']
            },
            'cyber_security': {
                'cyber_security': ['confidentiality', 'integrity', 'availability', 'CIA', 'protection', 'threat', 'attack', 'security', 'systems', 'networks', 'data'],
                'cyber_crime': ['hacking', 'identity theft', 'phishing', 'fraud', 'malware', 'ransomware', 'cyber stalking', 'cyber terrorism', 'illegal', 'unauthorized'],
                'digital_signature': ['encryption', 'private key', 'public key', 'authentication', 'non-repudiation', 'integrity', 'certificate', 'digital', 'verify'],
                'cyber_law': ['IT Act', '2000', 'legal', 'framework', 'electronic', 'transaction', 'evidence', 'regulation', 'cyber crimes', 'information technology'],
                'firewall': ['network', 'traffic', 'filter', 'barrier', 'security', 'access control', 'monitors', 'prevents'],
                'encryption': ['cipher', 'decrypt', 'key', 'confidentiality', 'algorithm', 'secure', 'convert', 'unreadable'],
                'ethical_hacking': ['white hat', 'authorized', 'vulnerability', 'penetration', 'reconnaissance', 'exploit', 'testing', 'permission'],
                'cyber_forensics': ['evidence', 'digital', 'investigation', 'preservation', 'analysis', 'recovery', 'forensic copy', 'digital evidence'],
                'data_protection': ['privacy', 'personal data', 'sensitive', 'misuse', 'unauthorized access', 'disclosure', 'protection laws']
            },
            'artificial_intelligence': {
                'ai': ['intelligent', 'machine learning', 'deep learning', 'neural', 'algorithm', 'automation', 'cognitive', 'adaptive', 'systems', 'reasoning', 'perception'],
                'ml': ['supervised', 'unsupervised', 'reinforcement', 'training', 'model', 'prediction', 'classification', 'regression', 'patterns', 'data'],
                'neural_network': ['neurons', 'layers', 'weights', 'activation', 'forward propagation', 'backpropagation', 'input', 'hidden', 'output', 'connections'],
                'nlp': ['natural language', 'processing', 'semantic', 'syntax', 'tokenization', 'embedding', 'transformer', 'chatbot', 'sentiment', 'parsing'],
                'computer_vision': ['image', 'video', 'recognition', 'cnn', 'convolutional', 'facial', 'object detection', 'visual', 'processing'],
                'overfitting': ['noise', 'generalization', 'complex', 'training', 'validation', 'regularization', 'dropout', 'bias', 'variance']
            },
            'blockchain': {
                'blockchain': ['distributed', 'ledger', 'decentralized', 'blocks', 'chain', 'transactions', 'immutable', 'transparent', 'consensus', 'nodes'],
                'decentralization': ['distributed', 'central authority', 'peer-to-peer', 'nodes', 'control', 'no single point', 'failure', 'trust'],
                'block_structure': ['block header', 'timestamp', 'hash', 'previous hash', 'merkle root', 'nonce', 'transactions', 'data'],
                'merkle_tree': ['hash', 'binary', 'tree', 'root', 'verification', 'efficient', 'transactions', 'integrity'],
                'proof_of_work': ['mining', 'puzzle', 'nonce', 'difficulty', 'hash', 'compute', 'energy', 'competition', 'bitcoin'],
                'proof_of_stake': ['validator', 'stake', 'cryptocurrency', 'selected', 'energy efficient', 'ethereum', 'consensus'],
                'smart_contract': ['self-executing', 'program', 'automated', 'conditions', 'intermediaries', 'ethereum', 'code', 'agreement'],
                '51_percent_attack': ['majority', 'control', 'mining power', 'stake', 'double-spending', 'reversal', 'vulnerability'],
                'applications': ['finance', 'supply chain', 'healthcare', 'voting', 'identity', 'cryptocurrency', 'bitcoin', 'ethereum']
            },
            'constitutional_law': {
                'constitutional_law': ['constitution', 'governance', 'fundamental', 'rights', 'principles', 'framework', 'authority', 'powers', 'institutions'],
                'rule_of_law': ['supremacy of law', 'equality', 'accountability', 'fairness', 'justice', 'arbitrary', 'legal certainty', 'transparency'],
                'separation_of_powers': ['legislature', 'executive', 'judiciary', 'checks and balances', 'independence', 'distribution', 'functions'],
                'fundamental_rights': ['right to equality', 'freedom of speech', 'right to life', 'constitutional remedies', 'enforceable', 'part III'],
                'directive_principles': ['DPSP', 'social justice', 'economic justice', 'welfare', 'non-justiciable', 'policy', 'guidelines', 'part IV'],
                'judicial_review': ['constitutionality', 'legislative action', 'executive action', 'courts', 'interpretation', 'invalid', 'basic structure'],
                'contract_law': ['offer', 'acceptance', 'consideration', 'capacity', 'free consent', 'lawful object', 'agreement', 'enforceable'],
                'criminal_law': ['offense', 'crime', 'punishment', 'deterrence', 'retribution', 'rehabilitation', 'IPC', 'penal', 'prosecution']
            }
        }
    
    def load_model(self):
        """Load the sentence transformer model for semantic analysis"""
        if not self.semantic_enabled:
            return False
        
        try:
            # Use lightweight but effective model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            return True
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            self.semantic_enabled = False
            return False
    
    def detect_subject(self, master_answer):
        """Detect subject from master answer content"""
        master_lower = master_answer.lower()
        
        # Subject detection keywords
        subject_keywords = {
            'software_engineering': ['software', 'engineering', 'ftr', 'walkthrough', 'loc', 'white box', 'version control', 
                                     'cohesion', 'coupling', 'spiral', 'reengineering', 'srs', 'testing', 'code'],
            'cyber_security': ['cyber', 'security', 'cia', 'confidentiality', 'integrity', 'availability', 'hacking', 
                               'phishing', 'malware', 'digital signature', 'firewall', 'encryption', 'forensics'],
            'artificial_intelligence': ['artificial intelligence', 'machine learning', 'neural', 'nlp', 'natural language',
                                        'computer vision', 'supervised', 'unsupervised', 'reinforcement', 'overfitting'],
            'blockchain': ['blockchain', 'block', 'decentralization', 'merkle', 'proof of work', 'proof of stake',
                           'smart contract', '51%', 'distributed ledger', 'bitcoin', 'ethereum'],
            'constitutional_law': ['constitutional', 'law', 'rule of law', 'separation of powers', 'fundamental rights',
                                   'directive principles', 'judicial review', 'contract', 'criminal', 'civil']
        }
        
        # Check for subject-specific keywords
        best_match = 'software_engineering'  # Default
        max_score = 0
        
        for subject, keywords in subject_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in master_lower)
            if score > max_score:
                max_score = score
                best_match = subject
        
        return best_match
    
    def preprocess_text(self, text):
        """Enhanced text preprocessing for better matching"""
        if not text or not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\.\,\?\!\-]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_key_terms(self, text, subject=None):
        """Extract important technical terms from text"""
        text_lower = self.preprocess_text(text)
        
        if not subject:
            subject = self.detect_subject(text)
        
        # Get subject-specific technical terms
        subject_terms = self.technical_terms.get(subject, {})
        
        # Flatten all terms
        all_technical_terms = []
        for category_terms in subject_terms.values():
            all_technical_terms.extend([t.lower() for t in category_terms])
        
        # Find matches
        found_terms = set()
        for term in all_technical_terms:
            if term in text_lower:
                found_terms.add(term)
            # Check for multi-word terms
            elif ' ' in term and term.replace(' ', '') in text_lower.replace(' ', ''):
                found_terms.add(term)
        
        return found_terms, subject
    
    def calculate_semantic_similarity(self, master_answer, student_answer):
        """Calculate semantic understanding score (0-10)"""
        if not self.semantic_enabled or not self.model:
            return self.calculate_word_overlap_score(master_answer, student_answer) * 0.8
        
        try:
            master_processed = self.preprocess_text(master_answer)
            student_processed = self.preprocess_text(student_answer)
            
            if not student_processed:
                return 0.0
            
            # Encode sentences
            embeddings = self.model.encode([master_processed, student_processed], 
                                          convert_to_tensor=True)
            
            # Calculate cosine similarity
            cosine_score = util.pytorch_cos_sim(embeddings[0], embeddings[1])
            similarity = float(cosine_score[0][0])
            
            # Scale to 0-10
            semantic_score = similarity * 10
            
            # Bonus for very high similarity
            if similarity > 0.85:
                semantic_score = min(10, semantic_score * 1.1)
            
            return round(max(0, min(10, semantic_score)), 2)
            
        except Exception as e:
            print(f"Semantic similarity error: {e}")
            return self.calculate_word_overlap_score(master_answer, student_answer) * 0.8
    
    def calculate_word_overlap_score(self, master_answer, student_answer):
        """Fallback word overlap calculation"""
        master_words = set(self.preprocess_text(master_answer).split())
        student_words = set(self.preprocess_text(student_answer).split())
        
        if not master_words:
            return 0.0
        
        overlap = len(master_words.intersection(student_words))
        return (overlap / len(master_words)) * 10
    
    def calculate_keyword_coverage(self, master_answer, student_answer):
        """Calculate technical term coverage score (0-10)"""
        # Detect subject
        subject = self.detect_subject(master_answer)
        
        # Extract technical terms
        master_terms, _ = self.extract_key_terms(master_answer, subject)
        student_terms, _ = self.extract_key_terms(student_answer, subject)
        
        if not master_terms:
            return 5.0  # Neutral score if no technical terms in master
        
        # Calculate coverage
        covered_terms = master_terms.intersection(student_terms)
        coverage_ratio = len(covered_terms) / len(master_terms)
        
        # Scale to 0-10
        keyword_score = coverage_ratio * 10
        
        # Bonus for using additional relevant terms
        additional_terms = student_terms - master_terms
        if additional_terms:
            bonus = min(1.0, len(additional_terms) * 0.1)
            keyword_score = min(10, keyword_score + bonus)
        
        return round(keyword_score, 2)
    
    def calculate_structure_score(self, master_answer, student_answer):
        """Evaluate answer structure and organization (0-10)"""
        student_text = student_answer.strip()
        
        if not student_text:
            return 0.0
        
        score = 5.0  # Base score
        
        # Check for paragraphs (organization)
        paragraphs = student_text.split('\n\n')
        if len(paragraphs) >= 2:
            score += 1.0
        if len(paragraphs) >= 3:
            score += 0.5
        
        # Check for bullet points or numbered lists
        if re.search(r'[•\-*]\s|\d+\.\s', student_text):
            score += 1.5
        
        # Check for clear definition or explanation
        if re.search(r'is|are|refers to|defined as|means', student_text.lower()):
            score += 1.0
        
        # Check for examples
        if re.search(r'example|instance|such as|e\.g\.|like', student_text.lower()):
            score += 1.0
        
        # Check for technical terms with proper formatting
        technical_indicators = [':', ';', '(', ')', '-']
        if any(indicator in student_text for indicator in technical_indicators):
            score += 0.5
        
        # Penalty for lack of structure
        if len(student_text.split()) > 100 and len(paragraphs) == 1:
            score -= 1.0
        
        return round(max(0, min(10, score)), 2)
    
    def calculate_length_score(self, master_answer, student_answer):
        """Evaluate length appropriateness (0-10)"""
        if not student_answer or not student_answer.strip():
            return 0.0
        
        master_len = len(master_answer.strip())
        student_len = len(student_answer.strip())
        
        # Ideal length: 30% to 150% of master answer (more forgiving for brief answers)
        min_acceptable = max(15, master_len * 0.3)
        max_acceptable = master_len * 1.5
        
        if student_len < min_acceptable:
            # Too short - linear scale
            score = (student_len / min_acceptable) * 5
        elif student_len <= max_acceptable:
            # Good length - full points with bonus for optimal
            ratio = student_len / master_len
            if 0.7 <= ratio <= 1.2:
                score = 10.0  # Perfect length
            else:
                score = 9.0   # Acceptable
        else:
            # Too long - small penalty
            score = 8.0
        
        return round(max(0, min(10, score)), 2)
    
    def evaluate_answer_fair(self, master_answer, student_answer, question_key=None):
        """
        FAIR evaluation with multiple balanced criteria:
        - Semantic understanding: 60%
        - Technical keyword coverage: 25%
        - Structure and organization: 10%
        - Length appropriateness: 5%
        
        Returns score out of max marks for the question type
        """
        if not student_answer or not student_answer.strip():
            return 0.0, "No answer provided"
        
        # Calculate individual scores (each on 0-10 scale)
        semantic_score = self.calculate_semantic_similarity(master_answer, student_answer)
        keyword_score = self.calculate_keyword_coverage(master_answer, student_answer)
        structure_score = self.calculate_structure_score(master_answer, student_answer)
        length_score = self.calculate_length_score(master_answer, student_answer)
        
        # Apply weights to get score on 0-10 scale
        normalized_score = (
            semantic_score * self.weights['semantic'] +
            keyword_score * self.weights['keyword'] +
            structure_score * self.weights['structure'] +
            length_score * self.weights['length']
        )
        
        # Determine max marks for this question type
        max_marks = 10  # Default for main questions
        if question_key:
            max_marks = self.get_question_max_marks(question_key)
        
        # Scale to actual question marks
        final_score = (normalized_score / 10) * max_marks
        final_score = round(final_score, 2)
        
        # Generate detailed feedback
        feedback = self.generate_fair_feedback(
            semantic_score, keyword_score, 
            structure_score, length_score, 
            normalized_score
        )
        
        return final_score, feedback
    
    def generate_fair_feedback(self, semantic, keyword, structure, length, total):
        """Generate detailed, constructive feedback"""
        feedback = []
        
        # Semantic feedback
        if semantic >= 8:
            feedback.append("🌟 Excellent understanding of concepts")
        elif semantic >= 6:
            feedback.append("📚 Good grasp of main ideas")
        elif semantic >= 4:
            feedback.append("📝 Basic understanding shown")
        else:
            feedback.append("📖 Needs to improve conceptual understanding")
        
        # Keyword feedback
        if keyword >= 7:
            feedback.append("🔑 Strong use of technical terminology")
        elif keyword >= 5:
            feedback.append("📌 Adequate technical terms used")
        else:
            feedback.append("💡 Missing key technical terms")
        
        # Structure feedback
        if structure >= 8:
            feedback.append("📋 Well-organized answer")
        elif structure >= 6:
            feedback.append("📄 Acceptable organization")
        else:
            feedback.append("✏️ Consider better structuring your answer")
        
        # Length feedback
        if length >= 9:
            feedback.append("✅ Appropriate length")
        elif length >= 7:
            feedback.append("📏 Acceptable length")
        elif length >= 5:
            feedback.append("⚠️ Answer could be more comprehensive")
        else:
            feedback.append("⚠️ Answer is too brief")
        
        # Overall feedback
        if total >= 9:
            feedback.insert(0, "🎯 Outstanding answer!")
        elif total >= 7:
            feedback.insert(0, "👍 Very good answer")
        elif total >= 5:
            feedback.insert(0, "📘 Satisfactory answer")
        elif total >= 3:
            feedback.insert(0, "📝 Needs improvement")
        else:
            feedback.insert(0, "❌ Incomplete answer")
        
        return "; ".join(feedback[:4])  # Return top 4 feedback points


class SubjectData:
    """Class to hold subject information"""
    
    def __init__(self, name, master_pdf_path, student_pdfs=None):
        self.name = name
        self.master_pdf_path = master_pdf_path
        self.student_pdfs = student_pdfs if student_pdfs else []
        self.results = None
        self.results_file = None
        self.master_answers = {}
        
    def to_dict(self):
        """Convert to dictionary for saving"""
        return {
            'name': self.name,
            'master_pdf': self.master_pdf_path,
            'student_pdfs': self.student_pdfs
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            name=data['name'],
            master_pdf_path=data['master_pdf'],
            student_pdfs=data.get('student_pdfs', [])
        )


class MultiSubjectPDFProcessor:
    """
    Handles PDF text extraction using NVIDIA NIM Vision API (llama-3.2-11b-vision-instruct).
    Falls back to PyPDF2 for digital (non-scanned) PDFs automatically.
    """

    NVIDIA_URL   = "https://integrate.api.nvidia.com/v1/chat/completions"
    NVIDIA_MODEL = "meta/llama-3.2-11b-vision-instruct"

    OCR_PROMPT = (
        "You are a precise OCR engine for handwritten university exam answer sheets. "
        "Your ONLY job is to transcribe exactly what is physically written on the page.\n\n"
        "STRICT RULES:\n"
        "1. Copy text EXACTLY as handwritten — do NOT fix spelling, grammar, or punctuation.\n"
        "2. The left margin may contain short labels like 'Q1 a:', 'Q2 b:', 'Q3 c:' — "
        "   copy these labels EXACTLY as they appear, including any space between the number and letter.\n"
        "3. Do NOT invent, add, or reformat any labels. If the margin says 'Q1 a:' write 'Q1 a:' — never 'Q1a::' or 'Q1::'.\n"
        "4. Keep the answer text that follows each label on the same or next line, as a single continuous block.\n"
        "5. Do NOT split a single answer into multiple sub-entries. If there is no new label, the text belongs to the current question.\n"
        "6. If text is truly unreadable write [illegible] — never guess.\n"
        "7. Output ONLY the raw transcribed text. No commentary, no explanation, no markdown formatting."
    )

    def __init__(self, nvidia_api_key):
        self.nvidia_api_key = nvidia_api_key
        self.log_messages   = []
        self._headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def log(self, message, widget=None):
        """Log message to console and optionally to GUI widget"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_messages.append(log_entry)
        if widget:
            widget.insert(tk.END, log_entry + "\n")
            widget.see(tk.END)

    def extract_pdf_text(self, pdf_path):
        """Fast path: extract text from digital PDFs using PyPDF2"""
        text = ''
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            return text
        except Exception as e:
            self.log(f"✗ Error reading PDF {pdf_path}: {e}")
            return ''

    def split_pdf_into_chunks(self, pdf_path, pages_per_chunk=3):
        """Split PDF into chunks (kept for compatibility)"""
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            if total_pages <= pages_per_chunk:
                return [pdf_path]
            chunks   = []
            temp_dir = tempfile.mkdtemp()
            for start_page in range(0, total_pages, pages_per_chunk):
                end_page = min(start_page + pages_per_chunk, total_pages)
                writer   = PdfWriter()
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                chunk_filename = os.path.join(
                    temp_dir, f"chunk_{start_page // pages_per_chunk + 1}.pdf"
                )
                with open(chunk_filename, 'wb') as out:
                    writer.write(out)
                chunks.append(chunk_filename)
            return chunks
        except Exception as e:
            self.log(f"❌ Error splitting PDF: {str(e)}")
            return [pdf_path]

    def _find_poppler_path(self):
        """
        Auto-detect poppler on Windows by checking common install locations.
        Returns the bin path string if found, or None to let pdf2image search PATH.
        """
        # 1. Use explicit POPPLER_PATH from configuration if set
        if POPPLER_PATH and os.path.isdir(POPPLER_PATH):
            return POPPLER_PATH

        # 2. Search common Windows locations automatically
        common_roots = [
            r"C:\poppler",
            r"C:\Program Files\poppler",
            r"C:\Program Files (x86)\poppler",
            os.path.join(os.path.expanduser("~"), "poppler"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "poppler"),
        ]
        for root in common_roots:
            if os.path.isdir(root):
                # Walk subdirs looking for pdftoppm.exe
                for dirpath, dirnames, filenames in os.walk(root):
                    if "pdftoppm.exe" in filenames:
                        return dirpath

        # 3. Not found — return None and hope it's in PATH
        return None

    def _convert_pdf_to_images(self, pdf_path, log_widget=None):
        """
        Convert PDF pages to PIL images using pdf2image + poppler.
        Tries auto-detect for poppler path on Windows.
        Returns list of PIL images or None on failure.
        """
        poppler_path = self._find_poppler_path()

        try:
            kwargs = dict(dpi=200, fmt="jpeg", thread_count=2)
            if poppler_path:
                kwargs["poppler_path"] = poppler_path
                self.log(f"📍 Using poppler at: {poppler_path}", log_widget)
            else:
                self.log("📍 Using poppler from system PATH", log_widget)

            images = convert_from_path(pdf_path, **kwargs)
            return images

        except Exception as e:
            err = str(e)
            self.log(f"❌ PDF→Image conversion failed: {err}", log_widget)

            # Give a very clear fix message for Windows users
            self.log(
                "\n🔧 HOW TO FIX — Install Poppler for Windows:\n"
                "  Step 1: Go to https://github.com/oschwartz10612/poppler-windows/releases\n"
                "  Step 2: Download the latest Release zip (e.g. Release-24.08.0-0.zip)\n"
                "  Step 3: Extract it — you will get a folder like 'poppler-24.08.0'\n"
                "  Step 4: Move that folder to C:\\poppler\\\n"
                "           so you have: C:\\poppler\\poppler-24.08.0\\Library\\bin\\pdftoppm.exe\n"
                "  Step 5: Open this file (s10.py) and find the line:\n"
                "             POPPLER_PATH = None\n"
                "           Change it to:\n"
                "             POPPLER_PATH = r'C:\\poppler\\poppler-24.08.0\\Library\\bin'\n"
                "  Step 6: Save and re-run the app.\n"
                "  ── OR ──\n"
                "  Add the bin\\ folder to Windows System PATH:\n"
                "    Control Panel → System → Advanced → Environment Variables\n"
                "    → Edit 'Path' → Add: C:\\poppler\\poppler-24.08.0\\Library\\bin",
                log_widget
            )
            return None

    def _image_to_base64_jpeg(self, image):
        """Convert PIL Image to base64 JPEG string"""
        buf = io.BytesIO()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        # Resize if too large for NVIDIA NIM (~20MB limit)
        w, h = image.size
        max_px = 1_500_000
        if w * h > max_px:
            ratio = (max_px / (w * h)) ** 0.5
            image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        image.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def _ocr_single_page(self, image, page_num, log_widget=None):
        """Send one page image to NVIDIA NIM and return extracted text"""
        img_b64 = self._image_to_base64_jpeg(image)
        payload = {
            "model": self.NVIDIA_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    },
                    {
                        "type": "text",
                        "text": self.OCR_PROMPT
                    }
                ]
            }],
            "max_tokens":  2048,
            "temperature": 0.0,
            "top_p":       1.0,
            "stream":      False,
        }

        for attempt in range(1, 3):
            try:
                resp = requests.post(
                    self.NVIDIA_URL,
                    headers=self._headers,
                    json=payload,
                    timeout=90
                )
                if resp.status_code == 200:
                    choices = resp.json().get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    self.log(f"⚠️ Page {page_num}: empty response from NVIDIA NIM", log_widget)
                    return ""

                elif resp.status_code == 429:
                    wait = 20 * attempt
                    self.log(f"⏳ Rate limited — waiting {wait}s before retry…", log_widget)
                    time.sleep(wait)
                    continue

                elif resp.status_code == 401:
                    self.log(
                        "❌ NVIDIA NIM: Invalid API key (HTTP 401).\n"
                        "   Check NVIDIA_API_KEY in the CONFIGURATION section.",
                        log_widget
                    )
                    return ""

                else:
                    self.log(
                        f"⚠️ Page {page_num} attempt {attempt}: "
                        f"HTTP {resp.status_code} — {resp.text[:200]}",
                        log_widget
                    )
                    if attempt == 1:
                        time.sleep(5)
                    continue

            except requests.exceptions.Timeout:
                self.log(f"⏱️ Page {page_num} attempt {attempt}: Timeout. Retrying…", log_widget)
                if attempt == 1:
                    time.sleep(5)
                continue
            except Exception as e:
                self.log(f"❌ Page {page_num}: {e}", log_widget)
                return ""

        return ""

    def extract_text_with_ocr(self, pdf_path, log_widget=None):
        """
        Extract text from scanned/handwritten PDF using NVIDIA NIM Vision Model.
        Converts each page to JPEG → sends to NVIDIA NIM → combines all text.
        """
        try:
            if not PDF2IMAGE_AVAILABLE or not PIL_AVAILABLE:
                self.log(
                    "❌ Cannot run OCR: pdf2image or Pillow not installed.\n"
                    "   Run: pip install pdf2image pillow",
                    log_widget
                )
                return None

            self.log(
                f"🚀 NVIDIA NIM OCR starting for: {os.path.basename(pdf_path)}",
                log_widget
            )

            # Step 1: PDF → images (with auto poppler detection)
            self.log("📸 Converting PDF pages to images (200 DPI)…", log_widget)
            images = self._convert_pdf_to_images(pdf_path, log_widget)
            if images is None:
                return None

            total = len(images)
            self.log(f"📄 {total} page(s) found. Sending to NVIDIA NIM…", log_widget)

            # Step 2: OCR each page
            all_parts = []
            for page_num, image in enumerate(images, start=1):
                self.log(
                    f"🧠 NVIDIA NIM — page {page_num}/{total}…",
                    log_widget
                )
                page_text = self._ocr_single_page(image, page_num, log_widget)
                if page_text:
                    all_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    self.log(
                        f"  ✅ Page {page_num}: {len(page_text)} characters extracted",
                        log_widget
                    )
                else:
                    self.log(f"  ⚠️ Page {page_num}: no text extracted", log_widget)

                # Respect NVIDIA free-tier rate limits (~10 req/min)
                if page_num < total:
                    time.sleep(2)

            if not all_parts:
                self.log("❌ No text extracted from any page.", log_widget)
                return None

            # Step 3: Combine and clean
            combined = "\n\n".join(all_parts)
            combined = re.sub(r'[ \t]+', ' ', combined)
            combined = re.sub(r'\n{3,}', '\n\n', combined)
            # Do NOT reformat Q-labels here — the OCR already preserves them as written

            self.log(
                f"✅ NVIDIA NIM OCR complete — {len(combined)} characters from {total} page(s).",
                log_widget
            )
            return combined.strip()

        except Exception as e:
            self.log(f"❌ NVIDIA NIM OCR failed: {str(e)}", log_widget)
            return None

    def create_searchable_pdf(self, text_content, output_path):
        """Create a PDF from extracted text"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_LEFT
            from reportlab.lib.units import inch

            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                leftMargin=0.75 * inch,
                rightMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )
            styles = getSampleStyleSheet()
            text_style = ParagraphStyle(
                'ExtractedText',
                parent=styles['Normal'],
                fontSize=11,
                leading=14,
                alignment=TA_LEFT,
                wordWrap='CJK'
            )
            story = []
            for line in text_content.split('\n'):
                if line.strip():
                    story.append(Paragraph(line.strip(), text_style))
                    story.append(Spacer(1, 6))
            if story:
                doc.build(story)
                return True
            return False

        except ImportError:
            self.log("⚠️ ReportLab not installed. Cannot create PDF.")
            return False
        except Exception as e:
            self.log(f"❌ Error creating PDF: {str(e)}")
            return False




class EmailSender:
    """Handles email sending functionality for multiple subjects"""
    
    def __init__(self, sender_email, app_password):
        self.sender_email = sender_email
        self.app_password = app_password
        self.sent_emails_log = []
    
    def test_connection(self):
        """Test email connection"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.sender_email, self.app_password)
            return True, "Email connection successful"
        except Exception as e:
            return False, f"Email connection failed: {str(e)}"
    
    def send_results_email(self, student_data, subject_results, detailed_results=None, results_file=None):
        """Send detailed results email to student with multiple subjects"""
        try:
            student_name = student_data['Name']
            student_email = student_data['Email']
            roll_no = student_data['Roll No']
            
            # Validate email
            if not student_email or student_email == f"student_{student_data.get('id', 0)}@example.com":
                return False, f"No valid email found for {student_name}"
            
            # Create email message
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = student_email
            message["Subject"] = f"📊 Comprehensive Exam Results - {student_name}"
            
            # Create subject-wise detailed table
            subject_table = ""
            detailed_breakdown = ""
            
            # Calculate overall totals
            total_marks_obtained = 0
            total_max_possible = 0
            
            for subject_name, scores in subject_results.items():
                total = scores.get('Total Marks', 0)
                max_possible = scores.get('Max Possible', 40)  # Get the actual max possible for this subject
                percentage = scores.get('Percentage', 0)
                grade = scores.get('Grade', 'N/A')
                
                # Add to overall totals
                total_marks_obtained += total
                total_max_possible += max_possible
                
                subject_table += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>{subject_name}:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{total:.2f}/{max_possible}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{percentage:.2f}%</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold; color: {'#27ae60' if grade in ['A+', 'A', 'B+'] else '#e74c3c'};">{grade}</td>
                </tr>
                """
                
                # Add detailed question-wise feedback if available
                if detailed_results and subject_name in detailed_results:
                    detailed_breakdown += f"""
                    <div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-left: 4px solid #3498db;">
                        <h5 style="color: #2c3e50; margin-top: 0;">📋 {subject_name} - Question-wise Analysis</h5>
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                            <tr style="background-color: #e9ecef;">
                                <th style="padding: 6px; text-align: left;">Question</th>
                                <th style="padding: 6px; text-align: left;">Score/Max</th>
                                <th style="padding: 6px; text-align: left;">Feedback</th>
                            </tr>
                            {self.format_detailed_feedback(detailed_results[subject_name])}
                        </table>
                    </div>
                    """
            
            # Calculate overall performance
            overall_percentage = (total_marks_obtained / total_max_possible) * 100 if total_max_possible > 0 else 0
            overall_grade = self.calculate_overall_grade(overall_percentage)
            
            # Create email body
            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px 15px 0 0; color: white;">
                    <h1 style="margin: 0; font-size: 28px;">🎓 Multi-Subject Exam Results</h1>
                    <p style="margin: 10px 0 0; opacity: 0.9;">Complete Performance Analysis Report</p>
                </div>
                
                <div style="background-color: #ffffff; padding: 30px; border-radius: 0 0 15px 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                    <p style="font-size: 18px; color: #2c3e50;">Dear <strong>{student_name}</strong>,</p>
                    
                    <p>Your comprehensive exam evaluation across all subjects is complete. Here is your detailed performance analysis:</p>
                    
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 10px; margin: 20px 0; color: white;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h3 style="margin: 0; color: white;">📊 Overall Performance</h3>
                                <p style="margin: 10px 0 0; font-size: 14px; opacity: 0.9;">Roll Number: {roll_no}</p>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 48px; font-weight: bold;">{overall_percentage:.1f}%</div>
                                <div style="font-size: 24px; background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; display: inline-block; margin-top: 5px;">
                                    {overall_grade}
                                </div>
                                <div style="font-size: 16px; margin-top: 5px;">{total_marks_obtained:.1f}/{total_max_possible} marks</div>
                            </div>
                        </div>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; margin-top: 0;">📚 Subject-wise Results</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background-color: #e9ecef;">
                                <th style="padding: 12px; text-align: left; border-radius: 5px 0 0 5px;">Subject</th>
                                <th style="padding: 12px; text-align: left;">Marks Obtained</th>
                                <th style="padding: 12px; text-align: left;">Percentage</th>
                                <th style="padding: 12px; text-align: left; border-radius: 0 5px 5px 0;">Grade</th>
                            </tr>
                            {subject_table}
                        </table>
                    </div>
                    
                    {detailed_breakdown}
                    
                    <div style="background-color: #e8f4fc; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h4 style="color: #2980b9; margin-top: 0;">📈 Performance Feedback</h4>
                        <p style="font-size: 16px; line-height: 1.6;">{self.get_performance_feedback(overall_percentage)}</p>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                        <h4 style="color: #856404; margin-top: 0;">💡 Improvement Tips</h4>
                        <ul style="color: #856404; margin: 0; padding-left: 20px;">
                            {self.generate_improvement_tips(subject_results)}
                        </ul>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p><strong>Note:</strong> For detailed question-wise scores and complete feedback, please check the attached Excel file.</p>
                        <p style="color: #7f8c8d; font-style: italic;">This is an automated message from the Multi-Subject Exam Evaluation System. Please do not reply to this email.</p>
                    </div>
                    
                    <div style="margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 12px;">
                        <p>Generated on: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
                        <p>© Multi-Subject Fair Evaluation System v2.0</p>
                    </div>
                </div>
            </div>
            """
            
            message.attach(MIMEText(body, "html"))
            
            # Attach results file if available
            if results_file and os.path.exists(results_file):
                try:
                    with open(results_file, "rb") as file:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename=Complete_Results_{student_name.replace(' ', '_')}.xlsx",
                        )
                        message.attach(part)
                except Exception as e:
                    return False, f"Could not attach file: {e}"
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, student_email, message.as_string())
            
            self.sent_emails_log.append({
                'student': student_name,
                'email': student_email,
                'subjects': len(subject_results),
                'overall_percentage': overall_percentage,
                'overall_grade': overall_grade,
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'Sent'
            })
            
            return True, f"Email sent to {student_name}"
            
        except Exception as e:
            error_msg = str(e)
            self.sent_emails_log.append({
                'student': student_name,
                'email': student_email,
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'Failed',
                'error': error_msg
            })
            return False, f"Failed to send email: {error_msg}"
    
    def format_detailed_feedback(self, question_data):
        """Format detailed question feedback for email"""
        html = ""
        for q_key, data in question_data.items():
            if isinstance(data, dict):
                score = data.get('score', 0)
                max_marks = data.get('max_marks', 10)  # Get max marks for this question
                feedback = data.get('feedback', 'No feedback')
            else:
                score = data
                max_marks = 10  # Default if not specified
                feedback = "Answer evaluated"
            
            color = '#27ae60' if score >= (max_marks * 0.7) else '#f39c12' if score >= (max_marks * 0.4) else '#e74c3c'
            html += f"""
            <tr>
                <td style="padding: 6px; border-bottom: 1px solid #ddd;"><strong>{q_key}</strong></td>
                <td style="padding: 6px; border-bottom: 1px solid #ddd; color: {color};">{score:.1f}/{max_marks}</td>
                <td style="padding: 6px; border-bottom: 1px solid #ddd;">{feedback}</td>
            </tr>
            """
        return html
    
    def calculate_overall_grade(self, percentage):
        """Calculate overall grade from percentage"""
        if percentage >= 90: return 'A+'
        elif percentage >= 80: return 'A'
        elif percentage >= 70: return 'B+'
        elif percentage >= 60: return 'B'
        elif percentage >= 50: return 'C'
        elif percentage >= 40: return 'D'
        else: return 'F'
    
    def get_performance_feedback(self, percentage):
        """Generate personalized performance feedback"""
        if percentage >= 90:
            return "🌟 Outstanding performance! You have demonstrated exceptional understanding across all subjects. Your consistent excellence is remarkable. Keep up the great work!"
        elif percentage >= 80:
            return "🎯 Excellent overall performance! You have strong command over most subjects. With focused effort on a few areas, you can achieve perfection."
        elif percentage >= 70:
            return "👍 Very good performance! You have solid understanding of core concepts. Continue building on this foundation to reach the next level."
        elif percentage >= 60:
            return "📚 Good overall effort. You have satisfactory knowledge in most subjects. Identify your weaker areas and dedicate more time to them."
        elif percentage >= 50:
            return "⚠️ Average performance. You have basic understanding but need more practice. Focus on understanding fundamental concepts before moving to advanced topics."
        elif percentage >= 40:
            return "📉 Below average performance. You need to significantly improve in multiple subjects. Consider revisiting the basics and practicing more regularly."
        else:
            return "❌ Needs significant improvement. Please seek help from teachers, use additional learning resources, and practice regularly. Don't get discouraged - consistent effort will lead to improvement."
    
    def generate_improvement_tips(self, subject_results):
        """Generate subject-specific improvement tips"""
        tips = ""
        weak_subjects = []
        strong_subjects = []
        
        for subject, scores in subject_results.items():
            percentage = scores.get('Percentage', 0)
            if percentage < 60:
                weak_subjects.append((subject, percentage))
            elif percentage >= 80:
                strong_subjects.append(subject)
        
        if weak_subjects:
            tips += f"<li><strong>Focus Areas:</strong> {', '.join([f'{s} ({p:.1f}%)' for s, p in weak_subjects])} - These subjects need more attention.</li>"
        
        if strong_subjects:
            tips += f"<li><strong>Strengths:</strong> {', '.join(strong_subjects)} - You're doing excellent here. Help classmates in these subjects.</li>"
        
        tips += """
        <li><strong>Practice regularly:</strong> Solve previous years' question papers and take mock tests.</li>
        <li><strong>Review feedback:</strong> Carefully read the question-wise feedback in the attached Excel file.</li>
        <li><strong>Use technical terms:</strong> Incorporate more subject-specific terminology in your answers.</li>
        <li><strong>Structure answers:</strong> Use clear headings, bullet points, and examples in your responses.</li>
        """
        
        return tips


class MultiSubjectFairEvaluator:
    """
    Main evaluation system with FAIR scoring for all subjects
    """
    
    def __init__(self, use_ocr=False):
        self.use_ocr = use_ocr
        self.subjects = []  # List of SubjectData objects
        self.consolidated_results_file = None
        self.log_messages = []
        self.email_sender = EmailSender(SENDER_EMAIL, APP_PASSWORD)
        self.pdf_processor = MultiSubjectPDFProcessor(NVIDIA_API_KEY)
        
        # Initialize the FAIR evaluation engine
        self.fair_evaluator = FairEvaluationEngine()
        self.log_messages.append(f"✅ Fair Evaluation Engine: {'Enabled (Semantic NLP)' if self.fair_evaluator.semantic_enabled else 'Enabled (Standard Mode)'}")
    
    def add_subject(self, name, master_pdf_path, student_pdfs=None):
        """Add a subject to evaluate"""
        subject = SubjectData(name, master_pdf_path, student_pdfs)
        self.subjects.append(subject)
        return subject
    
    def remove_subject(self, name):
        """Remove a subject by name"""
        self.subjects = [s for s in self.subjects if s.name != name]
    
    def get_subject(self, name):
        """Get subject by name"""
        for subject in self.subjects:
            if subject.name == name:
                return subject
        return None
    
    def load_subjects_from_csv(self, csv_path):
        """Load multiple subjects from CSV file"""
        try:
            df = pd.read_csv(csv_path)
            subjects = []
            
            for _, row in df.iterrows():
                subject_name = row['Subject_Name']
                master_pdf = row['Master_PDF']
                student_pdfs = eval(row.get('Student_PDFs', '[]')) if 'Student_PDFs' in row else []
                
                if os.path.exists(master_pdf):
                    # Filter existing PDFs
                    valid_pdfs = [p for p in student_pdfs if os.path.exists(p)]
                    subject = SubjectData(
                        name=subject_name,
                        master_pdf_path=master_pdf,
                        student_pdfs=valid_pdfs
                    )
                    subjects.append(subject)
            
            self.subjects = subjects
            return True, f"Loaded {len(subjects)} subjects from CSV"
        except Exception as e:
            return False, f"Failed to load subjects: {str(e)}"
    
    def save_subjects_to_csv(self, csv_path):
        """Save subjects configuration to CSV"""
        try:
            data = []
            for subject in self.subjects:
                data.append({
                    'Subject_Name': subject.name,
                    'Master_PDF': subject.master_pdf_path,
                    'Student_PDFs': str(subject.student_pdfs)
                })
            
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False)
            return True, f"Saved {len(self.subjects)} subjects to CSV"
        except Exception as e:
            return False, f"Failed to save subjects: {str(e)}"
    
    def log(self, message, widget=None):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_messages.append(log_entry)
        
        if widget:
            widget.insert(tk.END, log_entry + "\n")
            widget.see(tk.END)
    
    def extract_text_from_pdf(self, pdf_path, source_name, log_widget=None):
        """Extract text from PDF using either PyPDF2 or OCR"""
        # First try PyPDF2
        text = self.pdf_processor.extract_pdf_text(pdf_path)
        if text and len(text.strip()) > 100:
            return self.clean_extracted_text(text)
        
        # If PyPDF2 fails or text is too short, use NVIDIA NIM OCR
        if self.use_ocr and NVIDIA_API_KEY:
            self.log(f"  🔄 Using NVIDIA NIM OCR for {source_name}", log_widget)
            ocr_text = self.pdf_processor.extract_text_with_ocr(pdf_path, log_widget)
            if ocr_text:
                return self.clean_extracted_text(ocr_text)
        
        return text
    
    def clean_extracted_text(self, text):
        """Clean extracted text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(Q\d+[a-zA-Z]?)', r'\n\1:', text)
        return text.strip()
    
    def parse_master_answer(self, text):
        """Parse master answers from text"""
        master_answers = {}
        
        # Pattern handles: Q1, Q1a, Q1 a, Q1:, Q1a:, Q1 a: (with or without space between number and letter)
        pattern = r'Q(\d+)\s*([a-zA-Z]?)\s*[:\.]?\s*(.*?)(?=Q\d+\s*[a-zA-Z]?\s*[:\.]|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        for q_num, subpart, answer in matches:
            q_num = int(q_num) if q_num.isdigit() else q_num
            answer = answer.strip()
            
            if subpart and subpart.strip():
                key = f"{q_num}{subpart.lower().strip()}"
            else:
                key = str(q_num)
            
            if answer and len(answer) > 10:  # Only include substantial answers
                master_answers[key] = answer
        
        # Also look for ## Q1 a: format (from markdown-style)
        pattern2 = r'#+[\s]*Q(\d+)\s*([a-zA-Z]?)\s*[:\.]?\s*(.*?)(?=#+[\s]*Q\d+\s*[a-zA-Z]?\s*[:\.]|$)'
        matches2 = re.findall(pattern2, text, re.DOTALL | re.IGNORECASE)
        
        for q_num, subpart, answer in matches2:
            q_num = int(q_num) if q_num.isdigit() else q_num
            answer = answer.strip()
            
            if subpart and subpart.strip():
                key = f"{q_num}{subpart.lower().strip()}"
            else:
                key = str(q_num)
            
            if answer and len(answer) > 10 and key not in master_answers:
                master_answers[key] = answer
        
        return master_answers
    
    def extract_student_info(self, text):
        """Extract student information from text"""
        info = {'name': '', 'roll_no': '', 'email': ''}
        
        # Extract name
        name_patterns = [
            r'Student[^:\n]*:\s*([^\n(]+)',
            r'Name[^:\n]*:\s*([^\n(]+)',
            r'Student\s*name[^:\n]*:\s*([^\n(]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+)'  # Simple name pattern
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['name'] = match.group(1).strip()
                info['name'] = re.sub(r'\s*\(.*\)', '', info['name'])
                if len(info['name']) > 2:
                    break
        
        # Extract roll number
        roll_patterns = [
            r'Roll[^:\n]*:\s*([A-Za-z0-9-]+)',
            r'Roll\s*(?:No|no|No\.?|Number)[:\s]*([A-Za-z0-9-]+)',
            r'Roll\s*:\s*(\d+)',
            r'No[.\s]*:?\s*(\d+)'
        ]
        
        for pattern in roll_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['roll_no'] = match.group(1).strip()
                break
        
        # Extract email
        email_patterns = [
            r'Email[^:\n]*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'Email\s*id[^:\n]*:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        for pattern in email_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['email'] = match.group(1).strip().lower()
                break
        
        # Set defaults if not found
        if not info['name']:
            info['name'] = f'Student_{hash(text) % 1000:03d}'
        if not info['roll_no']:
            info['roll_no'] = f'ID_{hash(text) % 10000:04d}'
        if not info['email']:
            info['email'] = f'student_{info["roll_no"]}@example.com'
        
        return info
    
    def parse_student_answers(self, text, student_id):
        """Parse student answers and info"""
        info = self.extract_student_info(text)
        
        # Extract answers
        answers = {}
        
        # Pattern handles: Q1, Q1a, Q1 a, Q1:, Q1a:, Q1 a: (with or without space between number and letter)
        pattern = r'Q(\d+)\s*([a-zA-Z]?)\s*[:\.]?\s*(.*?)(?=Q\d+\s*[a-zA-Z]?\s*[:\.]|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        for q_num, subpart, answer in matches:
            q_num = int(q_num) if q_num.isdigit() else q_num
            answer = answer.strip()
            
            if subpart and subpart.strip():
                key = f"{q_num}{subpart.lower().strip()}"
            else:
                key = str(q_num)
            
            if answer and len(answer) > 3:
                answers[key] = answer
        
        # Also look for numbered answers without Q prefix
        if not answers:
            pattern2 = r'(\d+)([a-zA-Z]?)[\.\)]\s*(.*?)(?=\d+[a-zA-Z]?[\.\)]|$)'
            matches2 = re.findall(pattern2, text, re.DOTALL)
            for num, subpart, answer in matches2:
                answer = answer.strip()
                if answer and len(answer) > 3:
                    key = f"{num}{subpart.lower()}" if subpart else str(num)
                    answers[key] = answer
        
        # Look for ## Q format (markdown-style)
        pattern3 = r'#+[\s]*Q(\d+)\s*([a-zA-Z]?)\s*[:\.]?\s*(.*?)(?=#+[\s]*Q\d+\s*[a-zA-Z]?\s*[:\.]|$)'
        matches3 = re.findall(pattern3, text, re.DOTALL | re.IGNORECASE)
        
        for q_num, subpart, answer in matches3:
            q_num = int(q_num) if q_num.isdigit() else q_num
            answer = answer.strip()
            
            if subpart and subpart.strip():
                key = f"{q_num}{subpart.lower().strip()}"
            else:
                key = str(q_num)
            
            if answer and len(answer) > 3 and key not in answers:
                answers[key] = answer
        
        return {
            'name': info['name'],
            'roll_no': info['roll_no'],
            'email': info['email'],
            'answers': answers
        }
    
    def calculate_grade(self, percentage):
        """Calculate grade from percentage"""
        if percentage >= 90: return 'A+'
        elif percentage >= 80: return 'A'
        elif percentage >= 70: return 'B+'
        elif percentage >= 60: return 'B'
        elif percentage >= 50: return 'C'
        elif percentage >= 40: return 'D'
        else: return 'F'
    
    def evaluate_subject(self, subject_data, log_widget=None):
        """Evaluate a single subject with FAIR scoring"""
        self.log(f"\n📚 EVALUATING SUBJECT: {subject_data.name}", log_widget)
        self.log(f"Master PDF: {os.path.basename(subject_data.master_pdf_path)}", log_widget)
        self.log(f"Student PDFs: {len(subject_data.student_pdfs)} files", log_widget)
        self.log(f"Evaluation Method: FAIR Scoring (Semantic + Keywords + Structure + Length)", log_widget)
        
        # Extract Master Answers
        master_text = self.extract_text_from_pdf(
            subject_data.master_pdf_path, 
            f"Master - {subject_data.name}", 
            log_widget
        )
        if not master_text:
            raise Exception(f"Failed to extract text from master PDF for {subject_data.name}")
        
        master_answers = self.parse_master_answer(master_text)
        if not master_answers:
            raise Exception(f"Could not parse questions from master for {subject_data.name}")
        
        # Store master answers in subject data
        subject_data.master_answers = master_answers
        
        # Calculate total possible marks based on question types
        question_keys = list(master_answers.keys())
        total_possible_marks = self.fair_evaluator.calculate_total_possible_marks(question_keys)
        
        self.log(f"✓ Found {len(master_answers)} questions in master", log_widget)
        self.log(f"📊 Question breakdown:", log_widget)
        
        # Log question type breakdown
        main_count = sum(1 for q in question_keys if self.fair_evaluator.detect_question_type(q) == 'main')
        sub_count = len(question_keys) - main_count
        self.log(f"   • Main questions ({main_count}): {main_count * 10} marks", log_widget)
        self.log(f"   • Sub-questions ({sub_count}): {sub_count * 5} marks", log_widget)
        self.log(f"   • Total possible: {total_possible_marks} marks", log_widget)
        
        # Process Student Answer Sheets
        results = []
        
        for i, student_pdf in enumerate(subject_data.student_pdfs):
            filename = os.path.basename(student_pdf)
            self.log(f"\n🔍 Processing {filename} ({i+1}/{len(subject_data.student_pdfs)})", log_widget)
            
            student_text = self.extract_text_from_pdf(student_pdf, filename, log_widget)
            if not student_text:
                self.log(f"  ✗ Failed to extract text", log_widget)
                continue
            
            student_data = self.parse_student_answers(student_text, i+1)
            
            # Evaluate answers with FAIR scoring
            total_score = 0
            question_scores = {}
            question_feedback = {}
            answered_count = 0
            
            for q_key, m_ans in master_answers.items():
                s_ans = student_data['answers'].get(q_key, '')
                
                # Use FAIR evaluation with question type awareness
                score, feedback = self.fair_evaluator.evaluate_answer_fair(m_ans, s_ans, q_key)
                
                max_q_marks = self.fair_evaluator.get_question_max_marks(q_key)
                question_scores[f"Q{q_key}"] = score
                question_feedback[f"Q{q_key}"] = {
                    'score': score,
                    'max_marks': max_q_marks,
                    'feedback': feedback
                }
                total_score += score
                
                if s_ans:
                    answered_count += 1
                
                # Log low-scoring questions for debugging
                if score < (max_q_marks * 0.3) and s_ans:  # Less than 30% of max marks
                    self.log(f"  ⚠️ Q{q_key}: Low score ({score}/{max_q_marks}) - {feedback.split(';')[0]}", log_widget)
                elif not s_ans:
                    self.log(f"  ⚠️ Q{q_key}: Not attempted", log_widget)
            
            # Calculate percentage based on actual total possible marks
            percentage = round((total_score / total_possible_marks) * 100, 2) if total_possible_marks > 0 else 0
            grade = self.calculate_grade(percentage)
            
            # Clean up name - remove "Emailid:" if present
            name = student_data['name']
            if 'Emailid:' in name:
                name = name.split('Emailid:')[0].strip()
            
            # Create result with summary columns
            result = {
                'Subject': subject_data.name,
                'Name': name,
                'Roll No': student_data['roll_no'],
                'Email': student_data['email'],
                'Total Marks': round(total_score, 2),
                'Max Possible': total_possible_marks,
                'Percentage': percentage,
                'Grade': grade,
                'Questions Attempted': answered_count,
                'Total Questions': len(master_answers)
            }
            
            # Store question scores and feedback separately for detailed analysis
            result['_question_scores'] = question_scores
            result['_feedback'] = question_feedback
            
            results.append(result)
            
            self.log(f"  👤 Name: {name}", log_widget)
            self.log(f"  📝 Roll No: {student_data['roll_no']}", log_widget)
            self.log(f"  📊 Score: {total_score:.1f}/{total_possible_marks} ({percentage}%)", log_widget)
            self.log(f"  🏆 Grade: {grade}", log_widget)
            self.log(f"  📋 Attempted: {answered_count}/{len(master_answers)} questions", log_widget)
            
            # Log top strengths and areas for improvement
            self.log_student_feedback(result, log_widget)
        
        subject_data.results = results
        return results
    
    def log_student_feedback(self, result, log_widget=None):
        """Log personalized feedback for student"""
        # Get question scores from internal storage
        q_scores = result.get('_question_scores', {})
        
        if not q_scores:
            return
        
        # Find strengths and weaknesses
        strengths = [q for q, s in q_scores.items() if s >= 7]
        improvements = [q for q, s in q_scores.items() if s < 5 and s > 0]
        not_attempted = [q for q, s in q_scores.items() if s == 0]
        
        feedback = []
        if strengths:
            feedback.append(f"  💪 Strengths: {', '.join(strengths[:3])}")
        if improvements:
            feedback.append(f"  📝 Needs work: {', '.join(improvements[:3])}")
        if not_attempted:
            feedback.append(f"  ⚠️ Not attempted: {', '.join(not_attempted[:3])}")
        
        for msg in feedback:
            self.log(msg, log_widget)
    
    def evaluate_all_subjects(self, log_widget=None, progress_callback=None):
        """Evaluate all subjects with FAIR scoring"""
        self.log("=" * 70, log_widget)
        self.log("🎯 STARTING FAIR MULTI-SUBJECT EVALUATION", log_widget)
        self.log(f"Subjects: {len(self.subjects)}", log_widget)
        self.log(f"Evaluation Engine: FAIR Scoring System v2.0", log_widget)
        self.log(f"  • Semantic Understanding: {self.fair_evaluator.weights['semantic']*100}%", log_widget)
        self.log(f"  • Keyword Coverage: {self.fair_evaluator.weights['keyword']*100}%", log_widget)
        self.log(f"  • Structure: {self.fair_evaluator.weights['structure']*100}%", log_widget)
        self.log(f"  • Length Appropriateness: {self.fair_evaluator.weights['length']*100}%", log_widget)
        self.log("=" * 70, log_widget)
        
        # Create output directory
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        
        all_results = []
        subject_detailed_feedback = {}
        
        for idx, subject in enumerate(self.subjects):
            if progress_callback:
                progress_callback((idx + 1) / len(self.subjects) * 50)
            
            try:
                self.log(f"\n{'='*50}", log_widget)
                self.log(f"📘 SUBJECT {idx+1}/{len(self.subjects)}: {subject.name}", log_widget)
                self.log(f"{'='*50}", log_widget)
                
                subject_results = self.evaluate_subject(subject, log_widget)
                all_results.extend(subject_results)
                
                # Save individual subject results
                subject.results_file = self.save_subject_results(subject, log_widget)
                
                # Store detailed feedback for emails
                for result in subject_results:
                    student_key = f"{result['Roll No']}_{result['Name']}"
                    if student_key not in subject_detailed_feedback:
                        subject_detailed_feedback[student_key] = {}
                    subject_detailed_feedback[student_key][subject.name] = result.get('_feedback', {})
                
            except Exception as e:
                self.log(f"❌ Error evaluating {subject.name}: {str(e)}", log_widget)
                continue
        
        # Save Consolidated Results
        self.log("\n" + "=" * 50, log_widget)
        self.log("💾 SAVING CONSOLIDATED RESULTS", log_widget)
        self.log("=" * 50, log_widget)
        
        if all_results:
            self.consolidated_results_file = self.save_consolidated_results(all_results, log_widget)
            self.consolidated_feedback_file = self.save_detailed_feedback(subject_detailed_feedback, log_widget)
            
            # Generate comprehensive summary
            self.generate_comprehensive_summary(all_results, log_widget)
            
            if progress_callback:
                progress_callback(100)
            
            self.log("\n" + "=" * 50, log_widget)
            self.log("✅ EVALUATION COMPLETE!", log_widget)
            self.log(f"📁 Results saved to: {self.consolidated_results_file}", log_widget)
            self.log("=" * 50, log_widget)
        else:
            raise Exception("No results to evaluate")
        
        return all_results, subject_detailed_feedback
    
    def save_subject_results(self, subject_data, log_widget=None):
        """Save individual subject results to Excel with only summary columns"""
        if not subject_data.results:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"{subject_data.name}_results_{timestamp}.xlsx")
        
        # Create a copy with only summary columns (no question scores)
        excel_results = []
        for result in subject_data.results:
            # Only include summary columns, not individual question scores
            result_copy = {
                'Name': result.get('Name', ''),
                'Roll No': result.get('Roll No', ''),
                'Email': result.get('Email', ''),
                'Total Marks': result.get('Total Marks', 0),
                'Max Possible': result.get('Max Possible', 0),
                'Percentage': result.get('Percentage', 0),
                'Grade': result.get('Grade', ''),
                'Questions Attempted': result.get('Questions Attempted', 0),
                'Total Questions': result.get('Total Questions', 0)
            }
            excel_results.append(result_copy)
        
        df = pd.DataFrame(excel_results)
        
        # Save to Excel with formatting
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Results', index=False)
            
            worksheet = writer.sheets['Results']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 30)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        self.log(f"✓ {subject_data.name} results saved to: {filename}", log_widget)
        return filename
    
    def save_consolidated_results(self, all_results, log_widget=None):
        """Save consolidated results with subjects as columns (pivot table format)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"consolidated_results_{timestamp}.xlsx")
        
        # Get all unique subject names
        subject_names = [subject.name for subject in self.subjects]
        
        # Group results by student
        student_data = {}
        
        for result in all_results:
            roll_no = result.get('Roll No', '')
            name = result.get('Name', '')
            email = result.get('Email', '')
            subject = result.get('Subject', '')
            total_marks = result.get('Total Marks', 0)
            max_possible = result.get('Max Possible', 0)
            
            if roll_no not in student_data:
                student_data[roll_no] = {
                    'Name': name,
                    'Roll No': roll_no,
                    'Email': email,
                    'subjects': {}
                }
            
            # Store subject marks and max possible
            student_data[roll_no]['subjects'][subject] = {
                'marks': total_marks,
                'max': max_possible
            }
        
        # Create consolidated dataframe with subjects as columns
        consolidated_rows = []
        
        for roll_no, data in student_data.items():
            row = {
                'Name': data['Name'],
                'Roll No': data['Roll No'],
                'Email': data['Email']
            }
            
            # Add subject columns with marks and max
            for subject_name in subject_names:
                subject_info = data['subjects'].get(subject_name, {})
                if subject_info:
                    row[f'{subject_name} (Marks)'] = subject_info['marks']
                    row[f'{subject_name} (Max)'] = subject_info['max']
                    percentage = (subject_info['marks'] / subject_info['max'] * 100) if subject_info['max'] > 0 else 0
                    row[f'{subject_name} (%)'] = round(percentage, 2)
                else:
                    row[f'{subject_name} (Marks)'] = ''
                    row[f'{subject_name} (Max)'] = ''
                    row[f'{subject_name} (%)'] = ''
            
            consolidated_rows.append(row)
        
        df_consolidated = pd.DataFrame(consolidated_rows)
        
        # Create summary sheet
        summary_rows = []
        for roll_no, data in student_data.items():
            row = {
                'Roll No': data['Roll No'],
                'Name': data['Name'],
                'Email': data['Email'],
                'Total Subjects': len(data['subjects'])
            }
            
            total_marks_obtained = 0
            total_max_marks = 0
            
            for subject_name, subject_info in data['subjects'].items():
                total_marks_obtained += subject_info['marks']
                total_max_marks += subject_info['max']
                row[f'{subject_name} Marks'] = subject_info['marks']
            
            if total_max_marks > 0:
                overall_percentage = (total_marks_obtained / total_max_marks) * 100
                row['Total Marks'] = total_marks_obtained
                row['Max Possible'] = total_max_marks
                row['Overall %'] = round(overall_percentage, 2)
                row['Overall Grade'] = self.calculate_grade(overall_percentage)
            
            summary_rows.append(row)
        
        df_summary = pd.DataFrame(summary_rows)
        
        # Create statistics sheet
        stats_rows = []
        for subject in self.subjects:
            if subject.results:
                marks = [r['Total Marks'] for r in subject.results]
                percentages = [r['Percentage'] for r in subject.results]
                max_possible = subject.results[0]['Max Possible'] if subject.results else 0
                
                stats_rows.append({
                    'Subject': subject.name,
                    'Number of Students': len(subject.results),
                    'Max Possible': max_possible,
                    'Average Marks': round(sum(marks) / len(marks), 2) if marks else 0,
                    'Average %': round(sum(percentages) / len(percentages), 2) if percentages else 0,
                    'Highest Marks': max(marks) if marks else 0,
                    'Lowest Marks': min(marks) if marks else 0,
                    'Pass Rate %': round(sum(1 for p in percentages if p >= 40) / len(percentages) * 100, 2) if percentages else 0
                })
        
        df_stats = pd.DataFrame(stats_rows)
        
        # Save to Excel with multiple sheets
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df_consolidated.to_excel(writer, sheet_name='All Results', index=False)
            if not df_summary.empty:
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
            if not df_stats.empty:
                df_stats.to_excel(writer, sheet_name='Statistics', index=False)
        
        self.log(f"✓ Consolidated results saved to: {filename}", log_widget)
        return filename
    
    def save_detailed_feedback(self, subject_detailed_feedback, log_widget=None):
        """Save detailed feedback to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"detailed_feedback_{timestamp}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(subject_detailed_feedback, f, indent=2, ensure_ascii=False)
            self.log(f"✓ Detailed feedback saved to: {filename}", log_widget)
            return filename
        except Exception as e:
            self.log(f"✗ Failed to save detailed feedback: {e}", log_widget)
            return None
    
    def generate_comprehensive_summary(self, all_results, log_widget=None):
        """Display comprehensive summary statistics"""
        self.log("\n" + "=" * 70, log_widget)
        self.log("📊 COMPREHENSIVE EVALUATION SUMMARY", log_widget)
        self.log("=" * 70, log_widget)
        
        if not all_results:
            self.log("No results to display", log_widget)
            return
        
        # Overall Statistics
        unique_students = len(set([r['Roll No'] for r in all_results]))
        total_submissions = len(all_results)
        
        self.log("\n📈 OVERALL STATISTICS:", log_widget)
        self.log(f"  • Total Students: {unique_students}", log_widget)
        self.log(f"  • Total Subjects: {len(self.subjects)}", log_widget)
        self.log(f"  • Total Answer Sheets: {total_submissions}", log_widget)
        self.log(f"  • Average Sheets per Student: {total_submissions/unique_students:.1f}", log_widget)
        
        # Subject-wise summary
        self.log("\n📚 SUBJECT-WISE PERFORMANCE:", log_widget)
        for subject in self.subjects:
            if subject.results:
                subject_name = subject.name
                percentages = [r['Percentage'] for r in subject.results]
                total_marks = [r['Total Marks'] for r in subject.results]
                max_possible = subject.results[0]['Max Possible'] if subject.results else 0
                
                self.log(f"\n  {subject_name}:", log_widget)
                self.log(f"    • Students: {len(percentages)}", log_widget)
                self.log(f"    • Max Possible: {max_possible} marks", log_widget)
                self.log(f"    • Average: {sum(percentages)/len(percentages):.1f}%", log_widget)
                self.log(f"    • Median: {sorted(percentages)[len(percentages)//2]:.1f}%", log_widget)
                self.log(f"    • Highest: {max(percentages):.1f}%", log_widget)
                self.log(f"    • Lowest: {min(percentages):.1f}%", log_widget)
                self.log(f"    • Std Dev: {np.std(percentages):.2f}", log_widget)
                
                # Grade distribution
                grade_dist = {}
                for result in subject.results:
                    grade = result['Grade']
                    grade_dist[grade] = grade_dist.get(grade, 0) + 1
                
                grade_str = ", ".join([f"{g}: {c}" for g, c in sorted(grade_dist.items())])
                self.log(f"    • Grades: {grade_str}", log_widget)
                
                # Pass/Fail rate
                pass_count = sum(1 for p in percentages if p >= 40)
                fail_count = len(percentages) - pass_count
                self.log(f"    • Pass Rate: {pass_count/len(percentages)*100:.1f}% ({pass_count}/{len(percentages)})", log_widget)
        
        # Student rankings
        self.log("\n🏆 TOP PERFORMERS:", log_widget)
        
        # Calculate overall percentage for each student
        student_overall = {}
        for result in all_results:
            roll_no = result['Roll No']
            name = result['Name']
            percentage = result['Percentage']
            
            if roll_no not in student_overall:
                student_overall[roll_no] = {'name': name, 'percentages': [], 'subjects': set()}
            
            student_overall[roll_no]['percentages'].append(percentage)
            student_overall[roll_no]['subjects'].add(result['Subject'])
        
        # Calculate averages and sort
        student_avgs = []
        for roll_no, data in student_overall.items():
            avg = sum(data['percentages']) / len(data['percentages'])
            student_avgs.append({
                'roll': roll_no,
                'name': data['name'],
                'avg': avg,
                'subjects': len(data['subjects']),
                'sheets': len(data['percentages'])
            })
        
        student_avgs.sort(key=lambda x: x['avg'], reverse=True)
        
        for i, student in enumerate(student_avgs[:5], 1):
            self.log(f"  {i}. {student['name']} (Roll: {student['roll']}) - {student['avg']:.1f}%", log_widget)
        
        self.log("\n" + "=" * 70, log_widget)
    
    def send_emails(self, all_results, detailed_feedback, log_widget=None, progress_callback=None):
        """Send emails to all students with multi-subject results and detailed feedback"""
        self.log("\n" + "=" * 70, log_widget)
        self.log("📧 SENDING COMPREHENSIVE RESULTS EMAILS", log_widget)
        self.log("=" * 70, log_widget)
        
        # Test email connection
        self.log("Testing email connection...", log_widget)
        success, message = self.email_sender.test_connection()
        if not success:
            self.log(f"✗ {message}", log_widget)
            return 0, len(set([r['Roll No'] for r in all_results]))
        
        self.log(f"✓ {message}", log_widget)
        
        # Group results by student
        student_results = {}
        for result in all_results:
            roll_no = result['Roll No']
            if roll_no not in student_results:
                student_results[roll_no] = {
                    'Name': result['Name'],
                    'Email': result['Email'],
                    'Roll No': roll_no,
                    'subjects': {}
                }
            
            student_results[roll_no]['subjects'][result['Subject']] = {
                'Total Marks': result['Total Marks'],
                'Max Possible': result['Max Possible'],
                'Percentage': result['Percentage'],
                'Grade': result['Grade']
            }
        
        success_count = 0
        fail_count = 0
        
        for i, (roll_no, student_data) in enumerate(student_results.items()):
            self.log(f"\n📨 Sending to {student_data['Name']} ({i+1}/{len(student_results)})", log_widget)
            self.log(f"  Email: {student_data['Email']}", log_widget)
            self.log(f"  Subjects: {', '.join(student_data['subjects'].keys())}", log_widget)
            
            if progress_callback:
                progress_callback((i + 1) / len(student_results) * 100)
            
            # Get detailed feedback for this student
            student_key = f"{roll_no}_{student_data['Name']}"
            student_detailed = detailed_feedback.get(student_key, {})
            
            success, msg = self.email_sender.send_results_email(
                student_data, 
                student_data['subjects'],
                student_detailed,
                self.consolidated_results_file
            )
            
            if success:
                self.log(f"  ✅ {msg}", log_widget)
                success_count += 1
            else:
                self.log(f"  ❌ {msg}", log_widget)
                fail_count += 1
        
        # Save email log
        self.save_email_log(log_widget)
        
        self.log(f"\n📧 EMAIL SUMMARY:", log_widget)
        self.log(f"  ✅ Successfully sent: {success_count}", log_widget)
        self.log(f"  ❌ Failed to send: {fail_count}", log_widget)
        self.log(f"  📝 Email log saved", log_widget)
        
        return success_count, fail_count
    
    def save_email_log(self, log_widget=None):
        """Save email sending log"""
        if self.email_sender.sent_emails_log:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(OUTPUT_DIR, f"email_log_{timestamp}.csv")
            
            df = pd.DataFrame(self.email_sender.sent_emails_log)
            df.to_csv(log_file, index=False)
            self.log(f"\n📝 Email log saved to: {log_file}", log_widget)


class MultiSubjectGUI:
    """GUI Application for Multi-Subject FAIR Answer Sheet Evaluation System"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Subject FAIR Answer Sheet Evaluation System v2.0")
        self.root.geometry("1400x900")
        
        # Variables
        self.subjects = []  # List of SubjectData objects
        self.use_ocr = tk.BooleanVar(value=True)
        self.send_emails = tk.BooleanVar(value=False)
        self.use_semantic = tk.BooleanVar(value=True)
        self.current_subject_index = -1
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_subject_manager_tab()
        self.create_evaluation_tab()
        self.create_pdf_processing_tab()
        self.create_results_analytics_tab()
        self.create_settings_tab()
        
        # Status bar
        self.status_bar = tk.Label(
            root, 
            text="Ready - FAIR Evaluation System v2.0", 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            font=("Arial", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize evaluator
        self.evaluator = MultiSubjectFairEvaluator(use_ocr=self.use_ocr.get())
    
    def create_subject_manager_tab(self):
        """Create the subject management tab"""
        self.subject_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.subject_frame, text="📚 Subject Manager")
        
        # Title
        title_frame = ttk.Frame(self.subject_frame)
        title_frame.pack(fill='x', padx=20, pady=10)
        
        title_label = tk.Label(
            title_frame, 
            text="📚 Multi-Subject Management - FAIR Evaluation System", 
            font=("Arial", 18, "bold"),
            fg="#2c3e50"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Configure subjects, upload master answer sheets, and manage student PDFs",
            font=("Arial", 10),
            fg="#7f8c8d"
        )
        subtitle_label.pack()
        
        # Main content frame
        content_frame = ttk.Frame(self.subject_frame)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left panel - Subject List
        left_panel = ttk.LabelFrame(content_frame, text="📋 Subjects List", padding=15)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Subject count label
        self.subject_count_display = tk.Label(
            left_panel, 
            text="Total Subjects: 0", 
            font=("Arial", 11, "bold"),
            fg="#3498db"
        )
        self.subject_count_display.pack(anchor='w', pady=(0, 10))
        
        # Subject listbox with scrollbar
        listbox_frame = ttk.Frame(left_panel)
        listbox_frame.pack(fill='both', expand=True)
        
        self.subject_listbox = tk.Listbox(
            listbox_frame, 
            height=15, 
            font=("Arial", 11),
            selectbackground="#3498db",
            selectforeground="white",
            activestyle="none"
        )
        self.subject_listbox.pack(side='left', fill='both', expand=True)
        
        listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical')
        listbox_scrollbar.pack(side='right', fill='y')
        self.subject_listbox.config(yscrollcommand=listbox_scrollbar.set)
        listbox_scrollbar.config(command=self.subject_listbox.yview)
        
        # Subject list buttons
        list_buttons_frame = ttk.Frame(left_panel)
        list_buttons_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            list_buttons_frame, 
            text="🔄 Refresh List", 
            command=self.refresh_subject_list,
            width=15
        ).pack(side='left', padx=2)
        
        ttk.Button(
            list_buttons_frame, 
            text="🗑️ Remove Selected", 
            command=self.remove_selected_subject,
            width=15
        ).pack(side='left', padx=2)
        
        ttk.Button(
            list_buttons_frame, 
            text="📋 Clear All", 
            command=self.clear_all_subjects,
            width=15
        ).pack(side='left', padx=2)
        
        # Right panel - Add/Edit Subject
        right_panel = ttk.LabelFrame(content_frame, text="✏️ Add/Edit Subject", padding=20)
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Subject name
        ttk.Label(right_panel, text="Subject Name:", font=("Arial", 10)).grid(
            row=0, column=0, sticky='w', pady=8
        )
        self.subject_name_var = tk.StringVar()
        ttk.Entry(
            right_panel, 
            textvariable=self.subject_name_var, 
            width=35,
            font=("Arial", 10)
        ).grid(row=0, column=1, padx=10, pady=8, sticky='ew')
        
        # Master PDF
        ttk.Label(right_panel, text="Master Answer Sheet:", font=("Arial", 10)).grid(
            row=1, column=0, sticky='w', pady=8
        )
        self.master_pdf_var = tk.StringVar()
        master_frame = ttk.Frame(right_panel)
        master_frame.grid(row=1, column=1, padx=10, pady=8, sticky='ew')
        ttk.Entry(
            master_frame, 
            textvariable=self.master_pdf_var, 
            width=25,
            font=("Arial", 10)
        ).pack(side='left', fill='x', expand=True)
        ttk.Button(
            master_frame, 
            text="Browse", 
            command=self.browse_master_pdf,
            width=10
        ).pack(side='left', padx=5)
        
        # Student PDFs
        ttk.Label(right_panel, text="Student Answer Sheets:", font=("Arial", 10)).grid(
            row=2, column=0, sticky='w', pady=8
        )
        
        # Frame for student PDFs controls
        student_pdfs_frame = ttk.Frame(right_panel)
        student_pdfs_frame.grid(row=2, column=1, padx=10, pady=8, sticky='ew')
        
        # Student PDFs listbox with scrollbar
        ttk.Label(
            student_pdfs_frame, 
            text="Selected Student PDFs:",
            font=("Arial", 9, "italic")
        ).pack(anchor='w', pady=(0, 5))
        
        listbox_container = ttk.Frame(student_pdfs_frame)
        listbox_container.pack(fill='both', expand=True)
        
        self.student_pdfs_listbox = tk.Listbox(
            listbox_container, 
            height=6, 
            font=("Arial", 9),
            selectbackground="#3498db",
            selectforeground="white"
        )
        self.student_pdfs_listbox.pack(side='left', fill='both', expand=True)
        
        listbox_scroll = ttk.Scrollbar(listbox_container, orient='vertical')
        listbox_scroll.pack(side='right', fill='y')
        self.student_pdfs_listbox.config(yscrollcommand=listbox_scroll.set)
        listbox_scroll.config(command=self.student_pdfs_listbox.yview)
        
        # Student PDFs buttons
        student_buttons_frame = ttk.Frame(student_pdfs_frame)
        student_buttons_frame.pack(fill='x', pady=8)
        
        ttk.Button(
            student_buttons_frame, 
            text="➕ Add PDFs", 
            command=self.add_student_pdfs,
            width=12
        ).pack(side='left', padx=2)
        
        ttk.Button(
            student_buttons_frame, 
            text="🗑️ Remove", 
            command=self.remove_selected_student_pdf,
            width=12
        ).pack(side='left', padx=2)
        
        ttk.Button(
            student_buttons_frame, 
            text="📋 Clear All", 
            command=self.clear_student_pdfs,
            width=12
        ).pack(side='left', padx=2)
        
        # Control buttons
        buttons_frame = ttk.Frame(right_panel)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            buttons_frame, 
            text="➕ Add Subject", 
            command=self.add_subject, 
            style='Accent.TButton',
            width=15
        ).pack(side='left', padx=10)
        
        ttk.Button(
            buttons_frame, 
            text="✏️ Update Subject", 
            command=self.update_subject,
            width=15
        ).pack(side='left', padx=10)
        
        # Import/Export buttons
        import_export_frame = ttk.Frame(right_panel)
        import_export_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(
            import_export_frame, 
            text="📥 Import from CSV", 
            command=self.import_subjects_csv,
            width=18
        ).pack(side='left', padx=5)
        
        ttk.Button(
            import_export_frame, 
            text="📤 Export to CSV", 
            command=self.export_subjects_csv,
            width=18
        ).pack(side='left', padx=5)
        
        # Configure grid weights
        right_panel.columnconfigure(1, weight=1)
        
        # Subject count label
        self.subject_count_label = tk.Label(
            right_panel, 
            text="Subjects: 0", 
            font=("Arial", 11, "bold"),
            fg="#27ae60"
        )
        self.subject_count_label.grid(row=5, column=0, columnspan=2, pady=15)
        
        # Bind listbox selection
        self.subject_listbox.bind('<<ListboxSelect>>', self.on_subject_select)
    
    def create_evaluation_tab(self):
        """Create the evaluation tab"""
        self.eval_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.eval_frame, text="🎯 Evaluation")
        
        # Title
        title_frame = ttk.Frame(self.eval_frame)
        title_frame.pack(fill='x', padx=20, pady=10)
        
        title_label = tk.Label(
            title_frame, 
            text="🎯 FAIR Multi-Subject Evaluation Engine", 
            font=("Arial", 18, "bold"),
            fg="#2c3e50"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Evaluate all subjects with advanced NLP semantic analysis and fair scoring",
            font=("Arial", 10),
            fg="#7f8c8d"
        )
        subtitle_label.pack()
        
        # Main content frame
        content_frame = ttk.Frame(self.eval_frame)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Left panel for controls
        left_panel = ttk.Frame(content_frame)
        left_panel.pack(side='left', fill='y', padx=(0, 20))
        
        # Evaluation summary
        summary_frame = ttk.LabelFrame(left_panel, text="📊 Evaluation Summary", padding=15)
        summary_frame.pack(fill='x', pady=(0, 15))
        
        self.summary_text = tk.Text(
            summary_frame, 
            height=8, 
            width=45,
            font=("Courier", 10),
            bg="#f8f9fa",
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.summary_text.pack(fill='both', expand=True)
        self.summary_text.config(state='disabled')
        
        # Evaluation options
        options_frame = ttk.LabelFrame(left_panel, text="⚙️ Evaluation Options", padding=15)
        options_frame.pack(fill='x', pady=(0, 15))
        
        # OCR option
        ocr_check = ttk.Checkbutton(
            options_frame, 
            text="Use OCR (for handwritten/ scanned answer sheets)", 
            variable=self.use_ocr
        )
        ocr_check.pack(anchor='w', pady=5)
        
        # Semantic analysis option
        semantic_frame = ttk.Frame(options_frame)
        semantic_frame.pack(fill='x', pady=5)
        
        semantic_check = ttk.Checkbutton(
            semantic_frame, 
            text="Use Advanced Semantic NLP Analysis (Recommended)", 
            variable=self.use_semantic
        )
        semantic_check.pack(side='left', anchor='w')
        
        # Show semantic status
        if SEMANTIC_AVAILABLE:
            ttk.Label(
                semantic_frame, 
                text="✅ Available", 
                foreground="green", 
                font=("Arial", 9, "bold")
            ).pack(side='left', padx=10)
        else:
            ttk.Label(
                semantic_frame, 
                text="❌ Not Installed", 
                foreground="red", 
                font=("Arial", 9, "bold")
            ).pack(side='left', padx=10)
            ttk.Label(
                semantic_frame,
                text="(pip install sentence-transformers)",
                foreground="gray",
                font=("Arial", 8)
            ).pack(side='left', padx=5)
        
        # Scoring weights info
        weights_frame = ttk.Frame(options_frame)
        weights_frame.pack(fill='x', pady=8)
        
        ttk.Label(
            weights_frame,
            text="Scoring Weights:",
            font=("Arial", 9, "bold")
        ).pack(anchor='w')
        
        weights_text = "• Semantic: 60%  • Keywords: 25%  • Structure: 10%  • Length: 5%"
        ttk.Label(
            weights_frame,
            text=weights_text,
            font=("Arial", 8),
            foreground="#34495e"
        ).pack(anchor='w', pady=(5, 0))
        
        # Email option
        ttk.Checkbutton(
            options_frame, 
            text="Send Results Emails to Students", 
            variable=self.send_emails
        ).pack(anchor='w', pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill='x', pady=10)
        
        ttk.Button(
            control_frame, 
            text="🚀 Start FAIR Evaluation", 
            command=self.start_evaluation, 
            style='Accent.TButton',
            width=25
        ).pack(fill='x', pady=5)
        
        ttk.Button(
            control_frame, 
            text="📧 Send Results Emails", 
            command=self.send_emails_only,
            width=25
        ).pack(fill='x', pady=5)
        
        ttk.Button(
            control_frame, 
            text="📁 Open Results Folder", 
            command=self.open_results_folder,
            width=25
        ).pack(fill='x', pady=5)
        
        # Progress bar
        progress_frame = ttk.Frame(left_panel)
        progress_frame.pack(fill='x', pady=15)
        
        ttk.Label(progress_frame, text="Progress:", font=("Arial", 9)).pack(anchor='w')
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode='determinate',
            length=300,
            style='Accent.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill='x', pady=5)
        
        # Right panel for logs
        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Log header with controls
        log_header = ttk.Frame(right_panel)
        log_header.pack(fill='x', pady=(0, 10))
        
        ttk.Label(
            log_header, 
            text="📝 Evaluation Log", 
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        ttk.Button(
            log_header, 
            text="Clear Log", 
            command=self.clear_log,
            width=12
        ).pack(side='right')
        
        ttk.Button(
            log_header, 
            text="Save Log", 
            command=self.save_log,
            width=12
        ).pack(side='right', padx=5)
        
        # Log text area with scrollbar
        log_frame = ttk.Frame(right_panel)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=25, 
            width=80,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            wrap=tk.WORD
        )
        self.log_text.pack(fill='both', expand=True)
        
        # Configure log tags for colors
        self.log_text.tag_config("error", foreground="#f48771")
        self.log_text.tag_config("success", foreground="#6a9955")
        self.log_text.tag_config("warning", foreground="#dcdcaa")
        self.log_text.tag_config("info", foreground="#9cdcfe")
        self.log_text.tag_config("header", foreground="#c586c0", font=("Consolas", 11, "bold"))
    
    def create_pdf_processing_tab(self):
        """Create PDF processing tab"""
        self.pdf_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pdf_frame, text="📄 PDF OCR Processing")
        
        # Title
        title_frame = ttk.Frame(self.pdf_frame)
        title_frame.pack(fill='x', padx=20, pady=10)
        
        title_label = tk.Label(
            title_frame, 
            text="📄 PDF OCR Processing & Text Extraction", 
            font=("Arial", 18, "bold"),
            fg="#2c3e50"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Convert handwritten/scanned PDFs to searchable text using NVIDIA NIM Vision API",
            font=("Arial", 10),
            fg="#7f8c8d"
        )
        subtitle_label.pack()
        
        content_frame = ttk.Frame(self.pdf_frame)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Input section
        input_frame = ttk.LabelFrame(content_frame, text="📂 Input", padding=20)
        input_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(
            input_frame, 
            text="Select PDF file or folder containing PDFs:",
            font=("Arial", 10)
        ).pack(anchor='w')
        
        self.pdf_input_path = tk.StringVar()
        input_path_frame = ttk.Frame(input_frame)
        input_path_frame.pack(fill='x', pady=10)
        
        ttk.Entry(
            input_path_frame, 
            textvariable=self.pdf_input_path, 
            width=50,
            font=("Arial", 10)
        ).pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            input_path_frame, 
            text="Browse File", 
            command=self.browse_pdf_file,
            width=15
        ).pack(side='left', padx=5)
        
        ttk.Button(
            input_path_frame, 
            text="Browse Folder", 
            command=self.browse_pdf_folder,
            width=15
        ).pack(side='left', padx=5)
        
        # Output options
        options_frame = ttk.LabelFrame(content_frame, text="⚙️ Output Options", padding=20)
        options_frame.pack(fill='x', pady=(0, 20))
        
        self.create_searchable_pdf = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="Create searchable PDF from extracted text", 
            variable=self.create_searchable_pdf
        ).pack(anchor='w', pady=5)
        
        ttk.Label(
            options_frame,
            text="Output directory: " + OUTPUT_DIR,
            font=("Arial", 9),
            foreground="#34495e"
        ).pack(anchor='w', pady=5)
        
        # Process button
        process_btn = ttk.Button(
            content_frame, 
            text="🔄 Start OCR Processing", 
            command=self.process_pdfs_ocr, 
            style='Accent.TButton',
            width=30
        )
        process_btn.pack(pady=20)
        
        # PDF processing log
        log_header = ttk.Frame(content_frame)
        log_header.pack(fill='x', pady=(20, 10))
        
        ttk.Label(
            log_header, 
            text="📝 OCR Processing Log", 
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        ttk.Button(
            log_header, 
            text="Clear Log", 
            command=lambda: self.pdf_log_text.delete(1.0, tk.END),
            width=12
        ).pack(side='right')
        
        self.pdf_log_text = scrolledtext.ScrolledText(
            content_frame, 
            height=15, 
            width=80,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4"
        )
        self.pdf_log_text.pack(fill='both', expand=True)
    
    def create_results_analytics_tab(self):
        """Create results analytics tab"""
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="📊 Results Analytics")
        
        # Title
        title_label = tk.Label(
            self.analytics_frame, 
            text="📊 Results Analytics & Performance Dashboard", 
            font=("Arial", 18, "bold"),
            fg="#2c3e50"
        )
        title_label.pack(pady=20)
        
        # Content frame
        content_frame = ttk.Frame(self.analytics_frame)
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Info message
        info_frame = ttk.Frame(content_frame)
        info_frame.pack(fill='both', expand=True)
        
        tk.Label(
            info_frame,
            text="📈 Run an evaluation first to view detailed analytics",
            font=("Arial", 14),
            fg="#7f8c8d"
        ).pack(expand=True)
        
        tk.Label(
            info_frame,
            text="Results will appear here after evaluation",
            font=("Arial", 11),
            fg="#95a5a6"
        ).pack(pady=10)
        
        # Placeholder for future analytics visualizations
        self.analytics_placeholder = ttk.LabelFrame(
            content_frame, 
            text="Analytics Dashboard",
            padding=20
        )
        self.analytics_placeholder.pack(fill='both', expand=True, pady=20)
        
        tk.Label(
            self.analytics_placeholder,
            text="📊 Subject Performance Charts",
            font=("Arial", 12, "bold")
        ).pack(anchor='w', pady=5)
        
        tk.Label(
            self.analytics_placeholder,
            text="• Grade Distribution Analysis",
            font=("Arial", 10)
        ).pack(anchor='w', pady=2)
        
        tk.Label(
            self.analytics_placeholder,
            text="• Student Ranking & Percentiles",
            font=("Arial", 10)
        ).pack(anchor='w', pady=2)
        
        tk.Label(
            self.analytics_placeholder,
            text="• Subject Difficulty Analysis",
            font=("Arial", 10)
        ).pack(anchor='w', pady=2)
        
        tk.Label(
            self.analytics_placeholder,
            text="• Question-wise Performance Metrics",
            font=("Arial", 10)
        ).pack(anchor='w', pady=2)
    
    def create_settings_tab(self):
        """Create settings tab"""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ Settings")
        
        # Title
        title_frame = ttk.Frame(self.settings_frame)
        title_frame.pack(fill='x', padx=20, pady=10)
        
        title_label = tk.Label(
            title_frame, 
            text="⚙️ System Configuration", 
            font=("Arial", 18, "bold"),
            fg="#2c3e50"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Configure email, OCR, and NLP settings",
            font=("Arial", 10),
            fg="#7f8c8d"
        )
        subtitle_label.pack()
        
        content_frame = ttk.Frame(self.settings_frame)
        content_frame.pack(fill='both', expand=True, padx=50, pady=20)
        
        # Email settings
        email_frame = ttk.LabelFrame(content_frame, text="📧 Email Settings", padding=20)
        email_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(email_frame, text="Sender Email:", font=("Arial", 10)).grid(
            row=0, column=0, sticky='w', pady=8
        )
        self.sender_email_var = tk.StringVar(value=SENDER_EMAIL)
        ttk.Entry(
            email_frame, 
            textvariable=self.sender_email_var, 
            width=40,
            font=("Arial", 10)
        ).grid(row=0, column=1, padx=10, pady=8)
        
        ttk.Label(email_frame, text="App Password:", font=("Arial", 10)).grid(
            row=1, column=0, sticky='w', pady=8
        )
        self.app_password_var = tk.StringVar(value=APP_PASSWORD)
        ttk.Entry(
            email_frame, 
            textvariable=self.app_password_var, 
            show="*", 
            width=40,
            font=("Arial", 10)
        ).grid(row=1, column=1, padx=10, pady=8)
        
        ttk.Button(
            email_frame, 
            text="Test Email Connection", 
            command=self.test_email_connection,
            width=20
        ).grid(row=2, column=0, columnspan=2, pady=15)
        
        # OCR settings
        ocr_frame = ttk.LabelFrame(content_frame, text="🔍 NVIDIA NIM OCR Settings", padding=20)
        ocr_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(ocr_frame, text="NVIDIA NIM API Key:", font=("Arial", 10)).grid(
            row=0, column=0, sticky='w', pady=8
        )
        self.ocr_api_key_var = tk.StringVar(value=NVIDIA_API_KEY)
        ttk.Entry(
            ocr_frame, 
            textvariable=self.ocr_api_key_var, 
            width=40,
            font=("Arial", 10)
        ).grid(row=0, column=1, padx=10, pady=8)
        
        ttk.Label(ocr_frame, text="Output Directory:", font=("Arial", 10)).grid(
            row=1, column=0, sticky='w', pady=8
        )
        self.output_dir_var = tk.StringVar(value=OUTPUT_DIR)
        output_frame = ttk.Frame(ocr_frame)
        output_frame.grid(row=1, column=1, padx=10, pady=8, sticky='ew')
        ttk.Entry(
            output_frame, 
            textvariable=self.output_dir_var, 
            width=35,
            font=("Arial", 10)
        ).pack(side='left', fill='x', expand=True)
        ttk.Button(
            output_frame, 
            text="Browse", 
            command=lambda: self.output_dir_var.set(filedialog.askdirectory()),
            width=10
        ).pack(side='left', padx=5)
        
        # NLP Settings
        nlp_frame = ttk.LabelFrame(content_frame, text="🧠 NLP Settings", padding=20)
        nlp_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(
            nlp_frame, 
            text="Semantic Analysis Model:", 
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, sticky='w', pady=8)
        
        model_status = "✅ Installed and Ready" if SEMANTIC_AVAILABLE else "❌ Not Installed"
        model_color = "green" if SEMANTIC_AVAILABLE else "red"
        ttk.Label(
            nlp_frame, 
            text=model_status, 
            foreground=model_color,
            font=("Arial", 10)
        ).grid(row=0, column=1, sticky='w', pady=8, padx=10)
        
        if not SEMANTIC_AVAILABLE:
            ttk.Label(
                nlp_frame, 
                text="Install with: pip install sentence-transformers", 
                foreground="blue",
                font=("Arial", 9)
            ).grid(row=1, column=0, columnspan=2, pady=5, sticky='w')
        
        ttk.Label(
            nlp_frame,
            text="Model: all-MiniLM-L6-v2 (lightweight, 80MB)",
            font=("Arial", 9),
            foreground="#34495e"
        ).grid(row=2, column=0, columnspan=2, pady=5, sticky='w')
        
        # Save button
        ttk.Button(
            content_frame, 
            text="💾 Save All Settings", 
            command=self.save_settings, 
            style='Accent.TButton',
            width=25
        ).pack(pady=30)
        
        # Configure grid weights
        email_frame.columnconfigure(1, weight=1)
        ocr_frame.columnconfigure(1, weight=1)
    
    def add_subject(self):
        """Add a new subject"""
        name = self.subject_name_var.get().strip()
        master_pdf = self.master_pdf_var.get().strip()
        
        # Get student PDFs from listbox
        student_pdfs = self.get_student_pdfs_from_listbox()
        
        if not name:
            messagebox.showerror("Error", "Please enter a subject name")
            return
        
        if not master_pdf or not os.path.exists(master_pdf):
            messagebox.showerror("Error", "Please select a valid master PDF file")
            return
        
        if not student_pdfs:
            messagebox.showwarning("Warning", "Please add at least one student PDF")
            return
        
        # Check if subject already exists
        for subject in self.subjects:
            if subject.name.lower() == name.lower():
                messagebox.showwarning("Warning", f"Subject '{name}' already exists")
                return
        
        # Add subject
        subject = SubjectData(name, master_pdf, student_pdfs)
        self.subjects.append(subject)
        
        # Update evaluator
        self.evaluator.add_subject(name, master_pdf, student_pdfs)
        
        # Update UI
        self.refresh_subject_list()
        self.update_summary()
        
        # Clear form
        self.clear_subject_form()
        
        self.log_message(f"✅ Added subject: {name} with {len(student_pdfs)} student PDFs")
        messagebox.showinfo("Success", f"Subject '{name}' added successfully!")
    
    def update_subject(self):
        """Update selected subject"""
        if self.current_subject_index < 0:
            messagebox.showwarning("Warning", "Please select a subject to update")
            return
        
        name = self.subject_name_var.get().strip()
        master_pdf = self.master_pdf_var.get().strip()
        
        # Get student PDFs from listbox
        student_pdfs = self.get_student_pdfs_from_listbox()
        
        if not name:
            messagebox.showerror("Error", "Please enter a subject name")
            return
        
        if not master_pdf or not os.path.exists(master_pdf):
            messagebox.showerror("Error", "Please select a valid master PDF file")
            return
        
        if not student_pdfs:
            messagebox.showwarning("Warning", "Please add at least one student PDF")
            return
        
        # Check if name conflicts with another subject
        for i, subject in enumerate(self.subjects):
            if subject.name.lower() == name.lower() and i != self.current_subject_index:
                messagebox.showwarning("Warning", f"Subject '{name}' already exists")
                return
        
        old_name = self.subjects[self.current_subject_index].name
        
        # Update subject
        self.subjects[self.current_subject_index].name = name
        self.subjects[self.current_subject_index].master_pdf_path = master_pdf
        self.subjects[self.current_subject_index].student_pdfs = student_pdfs
        
        # Update evaluator
        self.evaluator.remove_subject(old_name)
        self.evaluator.add_subject(name, master_pdf, student_pdfs)
        
        # Update UI
        self.refresh_subject_list()
        self.update_summary()
        
        self.log_message(f"✅ Updated subject: {name}")
        messagebox.showinfo("Success", f"Subject '{name}' updated successfully!")
    
    def add_student_pdfs(self):
        """Add individual student PDF files"""
        file_paths = filedialog.askopenfilenames(
            title="Select Student Answer Sheets",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        added_count = 0
        for file_path in file_paths:
            if os.path.exists(file_path):
                # Check if already in listbox
                existing_items = self.student_pdfs_listbox.get(0, tk.END)
                if file_path not in existing_items:
                    self.student_pdfs_listbox.insert(tk.END, file_path)
                    added_count += 1
        
        if added_count > 0:
            self.log_message(f"✅ Added {added_count} student PDF(s)")
    
    def remove_selected_student_pdf(self):
        """Remove selected student PDF from listbox"""
        selection = self.student_pdfs_listbox.curselection()
        if selection:
            for index in reversed(selection):
                self.student_pdfs_listbox.delete(index)
            self.log_message("✅ Removed selected student PDF(s)")
    
    def clear_student_pdfs(self):
        """Clear all student PDFs from listbox"""
        if self.student_pdfs_listbox.size() > 0:
            self.student_pdfs_listbox.delete(0, tk.END)
            self.log_message("✅ Cleared all student PDFs")
    
    def get_student_pdfs_from_listbox(self):
        """Get list of student PDFs from listbox"""
        return list(self.student_pdfs_listbox.get(0, tk.END))
    
    def remove_selected_subject(self):
        """Remove selected subject"""
        selection = self.subject_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a subject to remove")
            return
        
        index = selection[0]
        subject_name = self.subjects[index].name
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove '{subject_name}'?"):
            # Remove from list
            self.subjects.pop(index)
            self.evaluator.remove_subject(subject_name)
            
            # Update UI
            self.refresh_subject_list()
            self.update_summary()
            self.clear_subject_form()
            
            self.log_message(f"✅ Removed subject: {subject_name}")
    
    def clear_all_subjects(self):
        """Clear all subjects"""
        if not self.subjects:
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to remove ALL subjects?"):
            self.subjects.clear()
            self.evaluator.subjects.clear()
            self.refresh_subject_list()
            self.update_summary()
            self.clear_subject_form()
            self.log_message("✅ Cleared all subjects")
    
    def refresh_subject_list(self):
        """Refresh the subject listbox"""
        self.subject_listbox.delete(0, tk.END)
        for subject in self.subjects:
            student_count = len(subject.student_pdfs)
            display_text = f"{subject.name} - {student_count} student sheet(s)"
            self.subject_listbox.insert(tk.END, display_text)
        
        # Update count displays
        count_text = f"Total Subjects: {len(self.subjects)}"
        self.subject_count_display.config(text=count_text)
        self.subject_count_label.config(text=f"Subjects: {len(self.subjects)}")
    
    def on_subject_select(self, event):
        """Handle subject selection"""
        selection = self.subject_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_subject_index = index
            subject = self.subjects[index]
            
            # Populate form
            self.subject_name_var.set(subject.name)
            self.master_pdf_var.set(subject.master_pdf_path)
            
            # Populate student PDFs listbox
            self.student_pdfs_listbox.delete(0, tk.END)
            for pdf_path in subject.student_pdfs:
                self.student_pdfs_listbox.insert(tk.END, pdf_path)
    
    def clear_subject_form(self):
        """Clear the subject form"""
        self.subject_name_var.set("")
        self.master_pdf_var.set("")
        self.student_pdfs_listbox.delete(0, tk.END)
        self.current_subject_index = -1
    
    def update_summary(self):
        """Update evaluation summary"""
        total_subjects = len(self.subjects)
        total_students = sum([len(s.student_pdfs) for s in self.subjects])
        total_sheets = total_students
        
        summary_text = f"""📊 EVALUATION SUMMARY
{'='*40}

Subjects: {total_subjects}
Total Answer Sheets: {total_sheets}

Subjects List:
"""
        for subject in self.subjects:
            summary_text += f"  • {subject.name}: {len(subject.student_pdfs)} students\n"
        
        summary_text += f"\n{'='*40}"
        
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary_text)
        self.summary_text.config(state='disabled')
    
    def browse_master_pdf(self):
        """Browse for master PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select Master Answer Sheet",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.master_pdf_var.set(file_path)
    
    def import_subjects_csv(self):
        """Import subjects from CSV file"""
        file_path = filedialog.askopenfilename(
            title="Import Subjects from CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            success, message = self.evaluator.load_subjects_from_csv(file_path)
            if success:
                # Update local subjects list
                self.subjects = self.evaluator.subjects.copy()
                self.refresh_subject_list()
                self.update_summary()
                messagebox.showinfo("Success", message)
                self.log_message(f"✅ {message}")
            else:
                messagebox.showerror("Error", message)
                self.log_message(f"❌ {message}")
    
    def export_subjects_csv(self):
        """Export subjects to CSV file"""
        if not self.subjects:
            messagebox.showwarning("Warning", "No subjects to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Subjects to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            success, message = self.evaluator.save_subjects_to_csv(file_path)
            if success:
                messagebox.showinfo("Success", message)
                self.log_message(f"✅ {message}")
            else:
                messagebox.showerror("Error", message)
                self.log_message(f"❌ {message}")
    
    def start_evaluation(self):
        """Start the evaluation process in a separate thread"""
        if not self.subjects:
            messagebox.showerror("Error", "Please add at least one subject")
            return
        
        # Validate all subjects
        valid_subjects = []
        for subject in self.subjects:
            if not os.path.exists(subject.master_pdf_path):
                self.log_message(f"⚠️ Warning: Master PDF not found for {subject.name}")
                continue
            
            valid_pdfs = [p for p in subject.student_pdfs if os.path.exists(p)]
            if not valid_pdfs:
                self.log_message(f"⚠️ Warning: No valid student PDFs for {subject.name}")
                continue
            
            subject.student_pdfs = valid_pdfs
            valid_subjects.append(subject)
        
        if not valid_subjects:
            messagebox.showerror("Error", "No valid subjects to evaluate")
            return
        
        # Update evaluator settings
        self.evaluator.use_ocr = self.use_ocr.get()
        self.evaluator.fair_evaluator.semantic_enabled = self.use_semantic.get() and SEMANTIC_AVAILABLE
        
        # Disable controls during evaluation
        self.toggle_controls(False)
        self.progress_bar['value'] = 0
        
        # Log start message
        self.log_message("\n" + "="*70, "header")
        self.log_message("🚀 STARTING FAIR MULTI-SUBJECT EVALUATION", "header")
        self.log_message("="*70, "header")
        self.log_message(f"📚 Total Subjects: {len(valid_subjects)}", "info")
        self.log_message(f"📄 Total Answer Sheets: {sum([len(s.student_pdfs) for s in valid_subjects])}", "info")
        self.log_message(f"🔍 OCR Enabled: {self.use_ocr.get()}", "info")
        self.log_message(f"🧠 Semantic NLP: {'Enabled' if self.evaluator.fair_evaluator.semantic_enabled else 'Disabled'}", "info")
        self.log_message("="*70, "header")
        
        # Update evaluator
        self.evaluator.subjects = valid_subjects
        
        # Start evaluation in separate thread
        thread = threading.Thread(target=self.run_evaluation)
        thread.daemon = True
        thread.start()
    
    def run_evaluation(self):
        """Run the evaluation process"""
        try:
            # Run evaluation with progress updates
            def update_progress(value):
                self.root.after(0, lambda: self.progress_bar.config(value=value))
            
            results, detailed_feedback = self.evaluator.evaluate_all_subjects(
                self.log_text,
                update_progress
            )
            
            # Store detailed feedback for email sending
            self.last_detailed_feedback = detailed_feedback
            self.last_results = results
            
            # Send emails if requested
            if self.send_emails.get():
                self.root.after(0, lambda: self.log_message("\n📧 Sending results emails...", "info"))
                success_count, fail_count = self.evaluator.send_emails(
                    results,
                    detailed_feedback,
                    self.log_text,
                    update_progress
                )
                
                self.root.after(0, lambda: self.log_message(f"\n📧 Email Summary:", "header"))
                self.root.after(0, lambda: self.log_message(f"  ✅ Successfully sent: {success_count}", "success"))
                self.root.after(0, lambda: self.log_message(f"  ❌ Failed to send: {fail_count}", "error"))
            
            # Enable controls
            self.root.after(0, lambda: self.toggle_controls(True))
            
            # Show success message
            eval_method = "Semantic NLP" if self.evaluator.fair_evaluator.semantic_enabled else "Standard"
            self.root.after(0, lambda: messagebox.showinfo(
                "✅ Evaluation Complete",
                f"Fair evaluation completed successfully!\n\n"
                f"📊 Subjects evaluated: {len(self.subjects)}\n"
                f"📄 Answer sheets processed: {len(results)}\n"
                f"🧠 Evaluation method: {eval_method}\n"
                f"📁 Results saved to: {self.evaluator.consolidated_results_file}\n\n"
                f"Check the Results Analytics tab for detailed statistics."
            ))
            
            # Update status
            self.root.after(0, lambda: self.status_bar.config(
                text=f"✅ Evaluation completed - {datetime.now().strftime('%H:%M:%S')}"
            ))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"\n❌ Evaluation failed: {error_msg}", "error"))
            self.root.after(0, lambda: self.toggle_controls(True))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Evaluation failed:\n{error_msg}"))
            self.root.after(0, lambda: self.status_bar.config(text="❌ Evaluation failed"))
    
    def send_emails_only(self):
        """Send emails for existing results"""
        if not hasattr(self, 'last_results') or not self.last_results:
            messagebox.showinfo("Info", "Please run evaluation first to generate results.")
            return
        
        if not hasattr(self, 'last_detailed_feedback'):
            self.last_detailed_feedback = {}
        
        # Disable controls during email sending
        self.toggle_controls(False)
        self.progress_bar['value'] = 0
        
        # Start email sending in separate thread
        thread = threading.Thread(target=self.run_email_sending)
        thread.daemon = True
        thread.start()
    
    def run_email_sending(self):
        """Run email sending process"""
        try:
            def update_progress(value):
                self.root.after(0, lambda: self.progress_bar.config(value=value))
            
            self.root.after(0, lambda: self.log_message("\n" + "="*70, "header"))
            self.root.after(0, lambda: self.log_message("📧 SENDING RESULTS EMAILS", "header"))
            self.root.after(0, lambda: self.log_message("="*70, "header"))
            
            success_count, fail_count = self.evaluator.send_emails(
                self.last_results,
                self.last_detailed_feedback,
                self.log_text,
                update_progress
            )
            
            self.root.after(0, lambda: self.log_message(f"\n📧 Email Summary:", "header"))
            self.root.after(0, lambda: self.log_message(f"  ✅ Successfully sent: {success_count}", "success"))
            self.root.after(0, lambda: self.log_message(f"  ❌ Failed to send: {fail_count}", "error"))
            
            # Enable controls
            self.root.after(0, lambda: self.toggle_controls(True))
            
            self.root.after(0, lambda: messagebox.showinfo(
                "✅ Email Sending Complete",
                f"Emails sent successfully!\n\n"
                f"✅ Success: {success_count}\n"
                f"❌ Failed: {fail_count}"
            ))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"\n❌ Email sending failed: {error_msg}", "error"))
            self.root.after(0, lambda: self.toggle_controls(True))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Email sending failed:\n{error_msg}"))
    
    def browse_pdf_file(self):
        """Browse for PDF file for OCR processing"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_input_path.set(file_path)
            self.pdf_log_message(f"📄 Selected PDF: {os.path.basename(file_path)}")
    
    def browse_pdf_folder(self):
        """Browse for folder containing PDFs for OCR processing"""
        folder_path = filedialog.askdirectory(title="Select Folder with PDFs")
        if folder_path:
            self.pdf_input_path.set(folder_path)
            self.pdf_log_message(f"📂 Selected folder: {folder_path}")
    
    def process_pdfs_ocr(self):
        """Process PDFs with OCR in separate thread"""
        input_path = self.pdf_input_path.get()
        if not input_path:
            messagebox.showerror("Error", "Please select a PDF file or folder")
            return
        
        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Selected path does not exist")
            return
        
        # Disable controls
        self.toggle_pdf_controls(False)
        
        self.pdf_log_message("\n" + "="*70)
        self.pdf_log_message("🔄 STARTING PDF OCR PROCESSING")
        self.pdf_log_message("="*70)
        self.pdf_log_message(f"📂 Input: {input_path}")
        self.pdf_log_message(f"📁 Output: {OUTPUT_DIR}")
        self.pdf_log_message("="*70)
        
        # Start processing in separate thread
        thread = threading.Thread(target=self.run_pdf_processing, args=(input_path,))
        thread.daemon = True
        thread.start()
    
    def run_pdf_processing(self, input_path):
        """Run PDF processing with OCR"""
        try:
            pdf_processor = MultiSubjectPDFProcessor(NVIDIA_API_KEY)
            
            if os.path.isfile(input_path):
                # Process single file
                self.root.after(0, lambda: self.pdf_log_message(f"\n📄 Processing file: {os.path.basename(input_path)}"))
                
                # Extract text with OCR
                text = pdf_processor.extract_text_with_ocr(input_path, self.pdf_log_text)
                
                if text:
                    # Save extracted text as PDF
                    output_filename = f"{os.path.splitext(os.path.basename(input_path))[0]}_extracted.pdf"
                    output_path = os.path.join(OUTPUT_DIR, output_filename)
                    
                    if pdf_processor.create_searchable_pdf(text, output_path):
                        self.root.after(0, lambda: self.pdf_log_message(f"✅ Created searchable PDF: {output_filename}"))
                    else:
                        self.root.after(0, lambda: self.pdf_log_message("❌ Failed to create PDF"))
            else:
                # Process folder
                self.root.after(0, lambda: self.pdf_log_message(f"\n📂 Processing folder: {input_path}"))
                
                pdf_files = glob.glob(os.path.join(input_path, "*.pdf")) + \
                           glob.glob(os.path.join(input_path, "*.PDF"))
                
                self.root.after(0, lambda: self.pdf_log_message(f"📄 Found {len(pdf_files)} PDF file(s)"))
                
                success_count = 0
                for i, pdf_file in enumerate(pdf_files, 1):
                    self.root.after(0, lambda i=i, pdf_file=pdf_file: self.pdf_log_message(
                        f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_file)}"
                    ))
                    
                    text = pdf_processor.extract_text_with_ocr(pdf_file, self.pdf_log_text)
                    
                    if text:
                        output_filename = f"{os.path.splitext(os.path.basename(pdf_file))[0]}_extracted.pdf"
                        output_path = os.path.join(OUTPUT_DIR, output_filename)
                        
                        if pdf_processor.create_searchable_pdf(text, output_path):
                            self.root.after(0, lambda: self.pdf_log_message(f"  ✅ Created: {output_filename}"))
                            success_count += 1
                        else:
                            self.root.after(0, lambda: self.pdf_log_message(f"  ❌ Failed to create PDF"))
            
            self.root.after(0, lambda: self.pdf_log_message("\n" + "="*70))
            self.root.after(0, lambda: self.pdf_log_message("🎉 PDF OCR Processing Complete!"))
            self.root.after(0, lambda: self.pdf_log_message(f"✅ Successfully processed: {success_count if 'success_count' in locals() else 1} file(s)"))
            self.root.after(0, lambda: self.pdf_log_message("="*70))
            
            # Enable controls
            self.root.after(0, lambda: self.toggle_pdf_controls(True))
            
            # Show success message
            self.root.after(0, lambda: messagebox.showinfo(
                "✅ Success",
                f"PDF processing completed successfully!\n\n"
                f"Output saved to: {OUTPUT_DIR}"
            ))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.pdf_log_message(f"\n❌ Processing failed: {error_msg}"))
            self.root.after(0, lambda: self.toggle_pdf_controls(True))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Processing failed:\n{error_msg}"))
    
    def test_email_connection(self):
        """Test email connection"""
        try:
            email_sender = EmailSender(self.sender_email_var.get(), self.app_password_var.get())
            success, message = email_sender.test_connection()
            
            if success:
                messagebox.showinfo("✅ Success", "Email connection test successful!")
            else:
                messagebox.showerror("❌ Error", message)
        except Exception as e:
            messagebox.showerror("❌ Error", f"Test failed: {str(e)}")
    
    def save_settings(self):
        """Save system settings"""
        global SENDER_EMAIL, APP_PASSWORD, NVIDIA_API_KEY, OUTPUT_DIR
        
        SENDER_EMAIL = self.sender_email_var.get()
        APP_PASSWORD = self.app_password_var.get()
        NVIDIA_API_KEY = self.ocr_api_key_var.get()
        OUTPUT_DIR = self.output_dir_var.get()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        
        messagebox.showinfo("✅ Success", "Settings saved successfully!")
        self.log_message("✅ System settings updated")
    
    def open_results_folder(self):
        """Open the results folder"""
        if os.path.exists(OUTPUT_DIR):
            os.startfile(OUTPUT_DIR)  # Windows
            # For macOS: os.system(f'open "{OUTPUT_DIR}"')
            # For Linux: os.system(f'xdg-open "{OUTPUT_DIR}"')
        else:
            messagebox.showinfo("Info", "Results folder does not exist yet.")
    
    def clear_log(self):
        """Clear the evaluation log"""
        self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """Save the evaluation log to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(OUTPUT_DIR, f"evaluation_log_{timestamp}.txt")
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("✅ Success", f"Log saved to:\n{log_file}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to save log: {str(e)}")
    
    def log_message(self, message, tag=None):
        """Add message to evaluation log with optional tag"""
        self.log_text.insert(tk.END, message + "\n", tag if tag else "info")
        self.log_text.see(tk.END)
    
    def pdf_log_message(self, message):
        """Add message to PDF processing log"""
        self.pdf_log_text.insert(tk.END, message + "\n")
        self.pdf_log_text.see(tk.END)
    
    def toggle_controls(self, enabled):
        """Enable/disable evaluation controls"""
        if enabled:
            self.status_bar.config(text="✅ Ready")
            self.progress_bar['value'] = 100
        else:
            self.status_bar.config(text="⏳ Processing...")
            self.progress_bar['value'] = 0
    
    def toggle_pdf_controls(self, enabled):
        """Enable/disable PDF processing controls"""
        # This would disable PDF processing buttons in a full implementation
        pass


def main():
    """Main function to run the application"""
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure custom styles
    style.configure('Accent.TButton', 
                   font=('Arial', 11, 'bold'),
                   background='#3498db',
                   foreground='white',
                   borderwidth=0,
                   focusthickness=3,
                   focuscolor='none')
    style.map('Accent.TButton',
             background=[('active', '#2980b9')])
    
    style.configure('Accent.Horizontal.TProgressbar',
                   background='#27ae60',
                   troughcolor='#ecf0f1',
                   borderwidth=0,
                   thickness=20)
    
    # Create output directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Create and run the application
    app = MultiSubjectGUI(root)
    
    # Set window icon (if available)
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()