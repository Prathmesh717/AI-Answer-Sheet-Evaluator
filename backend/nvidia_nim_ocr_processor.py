# ============================================================
#  DROP-IN REPLACEMENT — MultiSubjectPDFProcessor
#  Uses NVIDIA NIM (llama-3.2-11b-vision) instead of OCR.space
#
#  HOW TO USE:
#  1. pip install pdf2image pillow
#  2. Install poppler (see bottom of this file)
#  3. Replace your ENTIRE MultiSubjectPDFProcessor class
#     in s10__1_.py with this class below
#  4. In CONFIGURATION section change:
#       OCR_API_KEY = "K83661332788957"
#     to:
#       NVIDIA_API_KEY = "nvapi-YOUR_KEY_HERE"
#  5. In extract_text_from_pdf() change:
#       if self.use_ocr and OCR_API_KEY:
#     to:
#       if self.use_ocr and NVIDIA_API_KEY:
#  6. Wherever MultiSubjectPDFProcessor is created, change:
#       self.pdf_processor = MultiSubjectPDFProcessor(OCR_API_KEY)
#     to:
#       self.pdf_processor = MultiSubjectPDFProcessor(NVIDIA_API_KEY)
# ============================================================

import os
import re
import base64
import time
import json
import tempfile
import io
import requests
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter

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


class MultiSubjectPDFProcessor:
    """
    Handles PDF text extraction for multiple subjects.
    
    OCR Backend: NVIDIA NIM — llama-3.2-11b-vision-instruct
    Endpoint:    https://integrate.api.nvidia.com/v1/chat/completions
    
    Far superior to OCR.space for:
      ✅ Handwritten answer sheets
      ✅ Low-quality scans
      ✅ Mixed printed/handwritten text
      ✅ Complex layouts with tables/diagrams
    """

    # ── NVIDIA NIM Configuration ──────────────────────────────────
    NVIDIA_URL   = "https://integrate.api.nvidia.com/v1/chat/completions"
    NVIDIA_MODEL = "nvidia/llama-3.2-11b-vision-instruct"

    # OCR prompt — tuned for exam answer sheets
    OCR_PROMPT = (
        "You are a precise OCR engine for university exam answer sheets. "
        "Your only job is to extract ALL text exactly as written on the page. "
        "Rules:\n"
        "1. Preserve question labels exactly: Q1, Q2, Q1a, Q1b, Q2a etc.\n"
        "2. Preserve every word the student wrote — do NOT fix spelling.\n"
        "3. Preserve paragraph breaks using newlines.\n"
        "4. If text is unclear, write [illegible] — do NOT guess.\n"
        "5. Do NOT add any commentary, explanation, or summary.\n"
        "6. Output ONLY the raw text from the image — nothing else."
    )

    def __init__(self, nvidia_api_key: str):
        """
        Parameters
        ----------
        nvidia_api_key : str
            Your NVIDIA NIM API key.
            Get one free at: https://build.nvidia.com/
            Format: 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
        """
        self.nvidia_api_key = nvidia_api_key
        self.log_messages   = []

        self._headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

        # Validate dependencies on init
        if not PDF2IMAGE_AVAILABLE:
            print("❌ pdf2image missing — OCR will not work. Run: pip install pdf2image")
        if not PIL_AVAILABLE:
            print("❌ Pillow missing — OCR will not work. Run: pip install pillow")

    # ── Logging ───────────────────────────────────────────────────

    def log(self, message: str, widget=None):
        """Log message to console and optionally to a Tkinter widget."""
        import tkinter as tk
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        print(entry)
        self.log_messages.append(entry)
        if widget:
            try:
                widget.insert(tk.END, entry + "\n")
                widget.see(tk.END)
            except Exception:
                pass

    # ── PyPDF2 text extraction (fast path) ───────────────────────

    def extract_pdf_text(self, pdf_path: str) -> str:
        """
        Fast path: extract text from a digital/typed PDF using PyPDF2.
        Falls back to NVIDIA NIM OCR if text is too short (scanned PDF).
        """
        text = ""
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            self.log(f"✗ PyPDF2 error reading {pdf_path}: {e}")
        return text

    # ── Image helpers ─────────────────────────────────────────────

    def _image_to_base64_jpeg(self, image) -> str:
        """Convert a PIL Image to a base64-encoded JPEG string."""
        buf = io.BytesIO()
        # Ensure RGB (no alpha channel which JPEG doesn't support)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def _resize_if_too_large(self, image, max_pixels: int = 1_500_000):
        """
        Resize image if it exceeds max_pixels.
        NVIDIA NIM has a ~20MB base64 limit per request.
        """
        w, h = image.size
        if w * h > max_pixels:
            ratio  = (max_pixels / (w * h)) ** 0.5
            new_w  = int(w * ratio)
            new_h  = int(h * ratio)
            image  = image.resize((new_w, new_h), Image.LANCZOS)
        return image

    # ── NVIDIA NIM single-page OCR ────────────────────────────────

    def _ocr_single_page_nvidia(self, image, page_num: int, log_widget=None) -> str:
        """
        Send one page image to NVIDIA NIM vision model and return extracted text.
        
        Parameters
        ----------
        image    : PIL.Image  — the page rendered as an image
        page_num : int        — used for logging only
        
        Returns
        -------
        str — extracted text, or "" on failure
        """
        image   = self._resize_if_too_large(image)
        img_b64 = self._image_to_base64_jpeg(image)

        payload = {
            "model": self.NVIDIA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.OCR_PROMPT
                        }
                    ]
                }
            ],
            "max_tokens":  2048,
            "temperature": 0.0,   # 0 = most deterministic / accurate
            "top_p":       1.0,
            "stream":      False,
        }

        # ── First attempt ──────────────────────────────────────────
        for attempt in range(1, 3):   # max 2 attempts
            try:
                resp = requests.post(
                    self.NVIDIA_URL,
                    headers=self._headers,
                    json=payload,
                    timeout=90
                )

                if resp.status_code == 200:
                    data    = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        text = choices[0].get("message", {}).get("content", "").strip()
                        return text
                    else:
                        self.log(f"⚠️ Page {page_num}: empty choices in response", log_widget)
                        return ""

                elif resp.status_code == 429:
                    # Rate limited — wait and retry
                    wait = 15 * attempt
                    self.log(f"⏳ Rate limited. Waiting {wait}s before retry…", log_widget)
                    time.sleep(wait)
                    continue

                elif resp.status_code == 401:
                    self.log(
                        "❌ NVIDIA NIM: Invalid API key (HTTP 401). "
                        "Check your NVIDIA_API_KEY in configuration.",
                        log_widget
                    )
                    return ""

                else:
                    self.log(
                        f"⚠️ Page {page_num} attempt {attempt}: "
                        f"HTTP {resp.status_code} — {resp.text[:300]}",
                        log_widget
                    )
                    if attempt == 1:
                        time.sleep(5)
                    continue

            except requests.exceptions.Timeout:
                self.log(
                    f"⏱️ Page {page_num} attempt {attempt}: Request timed out.",
                    log_widget
                )
                if attempt == 1:
                    time.sleep(5)
                continue

            except Exception as e:
                self.log(f"❌ Page {page_num} attempt {attempt}: {e}", log_widget)
                return ""

        return ""   # Both attempts failed

    # ── Main OCR entry point ──────────────────────────────────────

    def extract_text_with_ocr(self, pdf_path: str, log_widget=None) -> str | None:
        """
        Extract text from a PDF using NVIDIA NIM Vision Model.

        Process:
          1. Convert each PDF page → high-res JPEG image (via pdf2image / poppler)
          2. Send each page to NVIDIA NIM llama-3.2-11b-vision-instruct
          3. Combine all page texts
          4. Clean and structure for downstream parsing

        Returns
        -------
        str  — combined extracted text
        None — if extraction failed entirely
        """
        if not PDF2IMAGE_AVAILABLE or not PIL_AVAILABLE:
            self.log(
                "❌ Cannot run NVIDIA NIM OCR: pdf2image or Pillow not installed.\n"
                "   Run: pip install pdf2image pillow",
                log_widget
            )
            return None

        if not self.nvidia_api_key or self.nvidia_api_key == "nvapi-YOUR_KEY_HERE":
            self.log(
                "❌ NVIDIA_API_KEY is not set. "
                "Get your key at https://build.nvidia.com/ and set it in the configuration.",
                log_widget
            )
            return None

        self.log(
            f"🚀 NVIDIA NIM OCR starting for: {os.path.basename(pdf_path)}",
            log_widget
        )

        # ── Step 1: PDF → Images ──────────────────────────────────
        self.log("📸 Converting PDF pages to images (200 DPI)…", log_widget)
        try:
            images = convert_from_path(
                pdf_path,
                dpi=200,
                fmt="jpeg",
                thread_count=2,
            )
        except Exception as e:
            self.log(
                f"❌ PDF to image conversion failed: {e}\n"
                "   Ensure poppler is installed:\n"
                "   • Windows: https://github.com/oschwartz10612/poppler-windows\n"
                "     Extract and add the bin/ folder to your system PATH\n"
                "   • Linux:   sudo apt-get install poppler-utils\n"
                "   • macOS:   brew install poppler",
                log_widget
            )
            return None

        total = len(images)
        self.log(f"📄 {total} page(s) found. Sending to NVIDIA NIM…", log_widget)

        # ── Step 2: OCR each page ─────────────────────────────────
        all_text_parts = []

        for page_num, image in enumerate(images, start=1):
            self.log(
                f"🧠 NVIDIA NIM processing page {page_num}/{total}…",
                log_widget
            )

            page_text = self._ocr_single_page_nvidia(image, page_num, log_widget)

            if page_text:
                all_text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                self.log(
                    f"  ✅ Page {page_num}: {len(page_text)} characters extracted",
                    log_widget
                )
            else:
                self.log(f"  ⚠️ Page {page_num}: no text extracted", log_widget)

            # Rate limiting: NVIDIA free tier = ~10 requests/min
            # 2-second delay keeps us well within limits
            if page_num < total:
                time.sleep(2)

        # ── Step 3: Combine and clean ─────────────────────────────
        if not all_text_parts:
            self.log("❌ No text was extracted from any page.", log_widget)
            return None

        combined = "\n\n".join(all_text_parts)

        # Normalise whitespace
        combined = re.sub(r"[ \t]+", " ", combined)
        combined = re.sub(r"\n{3,}", "\n\n", combined)

        # Re-format question numbers to new lines (Q1: Q1a: etc.)
        combined = re.sub(r"(Q\d+[a-zA-Z]?)", r"\n\1:", combined)

        self.log(
            f"✅ NVIDIA NIM OCR complete. "
            f"Total: {len(combined)} characters from {total} page(s).",
            log_widget
        )
        return combined.strip()

    # ── PDF split helper (kept for compatibility) ─────────────────

    def split_pdf_into_chunks(self, pdf_path: str, pages_per_chunk: int = 3) -> list:
        """
        Split PDF into smaller chunk files.
        (Kept for backward compatibility — NVIDIA NIM method doesn't use chunks,
         it processes page-by-page via pdf2image directly.)
        """
        try:
            reader     = PdfReader(pdf_path)
            total      = len(reader.pages)
            if total <= pages_per_chunk:
                return [pdf_path]

            chunks   = []
            temp_dir = tempfile.mkdtemp()

            for start in range(0, total, pages_per_chunk):
                end    = min(start + pages_per_chunk, total)
                writer = PdfWriter()
                for pg in range(start, end):
                    writer.add_page(reader.pages[pg])
                chunk_path = os.path.join(temp_dir, f"chunk_{start // pages_per_chunk + 1}.pdf")
                with open(chunk_path, "wb") as out:
                    writer.write(out)
                chunks.append(chunk_path)

            return chunks
        except Exception as e:
            self.log(f"❌ Error splitting PDF: {e}")
            return [pdf_path]

    # ── Searchable PDF creation (unchanged) ──────────────────────

    def create_searchable_pdf(self, text_content: str, output_path: str) -> bool:
        """Create a searchable PDF from extracted text using ReportLab."""
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
                bottomMargin=0.75 * inch,
            )
            styles    = getSampleStyleSheet()
            txt_style = ParagraphStyle(
                "ExtractedText",
                parent=styles["Normal"],
                fontSize=11,
                leading=14,
                alignment=TA_LEFT,
                wordWrap="CJK",
            )
            story = []
            for line in text_content.split("\n"):
                if line.strip():
                    story.append(Paragraph(line.strip(), txt_style))
                    story.append(Spacer(1, 6))

            if story:
                doc.build(story)
                return True
            return False

        except ImportError:
            self.log("⚠️ ReportLab not installed. Run: pip install reportlab")
            return False
        except Exception as e:
            self.log(f"❌ Error creating PDF: {e}")
            return False


# ============================================================
#  QUICK TEST — run this file directly to verify your key
# ============================================================
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  NVIDIA NIM OCR — Quick Test")
    print("=" * 60)

    # ── Put your key here for testing ──
    TEST_KEY = "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"

    if TEST_KEY == "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":
        print("❌ Please set TEST_KEY to your actual NVIDIA NIM API key.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python nvidia_ocr_processor.py path/to/test.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    processor = MultiSubjectPDFProcessor(nvidia_api_key=TEST_KEY)

    print(f"\n🔍 Testing OCR on: {pdf_path}\n")
    text = processor.extract_text_with_ocr(pdf_path)

    if text:
        print("\n" + "=" * 60)
        print("EXTRACTED TEXT (first 1000 chars):")
        print("=" * 60)
        print(text[:1000])
        print(f"\n✅ Total extracted: {len(text)} characters")
    else:
        print("\n❌ OCR failed — check logs above for details.")
