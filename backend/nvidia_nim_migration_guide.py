# ============================================================
# NVIDIA NIM OCR API — Migration Guide & Updated Code
# Replace OCR.space with NVIDIA NIM (vision-language model)
# ============================================================

"""
WHAT IS NVIDIA NIM OCR?
───────────────────────
NVIDIA NIM (NVIDIA Inference Microservices) provides hosted AI models
via a simple OpenAI-compatible REST API. For OCR / document reading,
we use the vision-language model:

    Model:    nvidia/llama-3.2-11b-vision-instruct   (free tier available)
    Endpoint: https://integrate.api.nvidia.com/v1/chat/completions

It accepts base64-encoded images (PNG/JPEG) and returns text — much
more accurate than OCR.space for handwritten answer sheets.


HOW TO GET YOUR NVIDIA NIM API KEY
────────────────────────────────────
1. Go to  https://build.nvidia.com/
2. Click  "Sign In" → create a free account
3. Go to  https://build.nvidia.com/nvidia/llama-3_2-11b-vision-instruct
4. Click  "Get API Key"  button (top right)
5. Copy the key — it looks like:  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
6. Paste it into NVIDIA_API_KEY below


PACKAGES REQUIRED
──────────────────
pip install requests PyPDF2 pdf2image pillow

Also install poppler (needed by pdf2image):
  Windows: https://github.com/oschwartz10612/poppler-windows/releases
           Extract and add bin/ to your PATH
  Linux:   sudo apt-get install poppler-utils
  macOS:   brew install poppler


CHANGES SUMMARY (4 places in your s10__1_.py)
──────────────────────────────────────────────
1. CONFIGURATION section  (line ~42)
   → Replace OCR_API_KEY with NVIDIA_API_KEY

2. IMPORTS section  (line ~1)
   → Add:  from pdf2image import convert_from_path
           from PIL import Image
           import io

3. MultiSubjectPDFProcessor.__init__  (line ~538)
   → Accept nvidia_api_key instead of ocr_api_key

4. MultiSubjectPDFProcessor.extract_text_with_ocr  (line ~603)
   → Replace entire method with NVIDIA NIM version below

5. extract_text_from_pdf  (line ~1092)
   → Update the OCR_API_KEY check to NVIDIA_API_KEY
"""


# ============================================================
# CHANGE 1 — Replace in CONFIGURATION section (line ~42)
# ============================================================

OLD_CONFIG = """
# ========================================
# CONFIGURATION
# ========================================
OCR_API_KEY = "K83661332788957"
SENDER_EMAIL = "nitesh.t.mulam2004@gmail.com"
APP_PASSWORD = "gxdd zdyh gfym mlcq"
OUTPUT_DIR = "extracted_pdfs"
"""

NEW_CONFIG = """
# ========================================
# CONFIGURATION
# ========================================
NVIDIA_API_KEY = "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"   # ← Paste your NVIDIA NIM key here
SENDER_EMAIL   = "nitesh.t.mulam2004@gmail.com"
APP_PASSWORD   = "gxdd zdyh gfym mlcq"
OUTPUT_DIR     = "extracted_pdfs"
"""


# ============================================================
# CHANGE 2 — Add to IMPORTS section (top of file, line ~25)
# ============================================================

NEW_IMPORTS = """
# Add these after existing imports
from pdf2image import convert_from_path   # pip install pdf2image
from PIL import Image                     # pip install pillow
import io
"""


# ============================================================
# CHANGE 3 — Replace MultiSubjectPDFProcessor.__init__
# ============================================================

OLD_INIT = """
def __init__(self, api_key):
    self.api_key = api_key
    self.log_messages = []
"""

NEW_INIT = """
def __init__(self, nvidia_api_key):
    self.nvidia_api_key = nvidia_api_key   # NVIDIA NIM key
    self.log_messages = []
    
    # NVIDIA NIM endpoint and model
    self.nvidia_url   = "https://integrate.api.nvidia.com/v1/chat/completions"
    self.nvidia_model = "nvidia/llama-3.2-11b-vision-instruct"
    self.nvidia_headers = {
        "Authorization": f"Bearer {self.nvidia_api_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
"""


# ============================================================
# CHANGE 4 — Replace extract_text_with_ocr method entirely
# ============================================================

NEW_OCR_METHOD = '''
    def pdf_page_to_base64(self, image):
        """Convert a PIL Image to base64 JPEG string for NVIDIA NIM"""
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def extract_text_from_image_nvidia(self, image, page_num, log_widget=None):
        """
        Send a single page image to NVIDIA NIM vision model and get extracted text.
        Uses llama-3.2-11b-vision-instruct which is excellent at reading
        handwritten and printed text from answer sheets.
        """
        try:
            img_b64 = self.pdf_page_to_base64(image)

            payload = {
                "model": self.nvidia_model,
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
                                "text": (
                                    "You are an expert OCR system for exam answer sheets. "
                                    "Extract ALL text from this image EXACTLY as written. "
                                    "Preserve question numbers (Q1, Q2, Q1a, Q2b etc.). "
                                    "Preserve paragraph structure. "
                                    "Do NOT summarize, correct spelling, or add commentary. "
                                    "Output ONLY the raw extracted text."
                                )
                            }
                        ]
                    }
                ],
                "max_tokens":  2048,
                "temperature": 0.0,   # Zero temp = deterministic = better accuracy
                "top_p":       1.0,
                "stream":      False,
            }

            response = requests.post(
                self.nvidia_url,
                headers=self.nvidia_headers,
                json=payload,
                timeout=90   # Vision models can take longer
            )

            if response.status_code != 200:
                self.log(
                    f"⚠️ NVIDIA NIM error page {page_num}: "
                    f"HTTP {response.status_code} — {response.text[:200]}",
                    log_widget
                )
                return ""

            result = response.json()

            # Extract text from response
            choices = result.get("choices", [])
            if not choices:
                self.log(f"⚠️ No choices returned for page {page_num}", log_widget)
                return ""

            extracted = choices[0].get("message", {}).get("content", "").strip()
            return extracted

        except requests.exceptions.Timeout:
            self.log(f"⏱️ Timeout on page {page_num} — retrying once…", log_widget)
            try:
                time.sleep(3)
                response = requests.post(
                    self.nvidia_url,
                    headers=self.nvidia_headers,
                    json=payload,
                    timeout=120
                )
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            except Exception as retry_err:
                self.log(f"❌ Retry failed page {page_num}: {retry_err}", log_widget)
                return ""

        except Exception as e:
            self.log(f"❌ NVIDIA NIM error page {page_num}: {e}", log_widget)
            return ""

    def extract_text_with_ocr(self, pdf_path, log_widget=None):
        """
        Extract text from PDF using NVIDIA NIM Vision Model.
        Converts each PDF page to an image, sends to NVIDIA NIM,
        and combines all extracted text.
        
        REPLACES the old OCR.space API method.
        """
        try:
            self.log(
                f"🔄 Starting NVIDIA NIM OCR for {os.path.basename(pdf_path)}",
                log_widget
            )

            # ── Step 1: Convert PDF pages to images ──────────────────────
            self.log("📸 Converting PDF pages to images…", log_widget)
            try:
                images = convert_from_path(
                    pdf_path,
                    dpi=200,           # 200 DPI = good balance of quality vs speed
                    fmt="jpeg",
                    thread_count=2,
                )
            except Exception as conv_err:
                self.log(f"❌ PDF→Image conversion failed: {conv_err}", log_widget)
                self.log(
                    "💡 Make sure poppler is installed: "
                    "Windows→ add poppler/bin to PATH | "
                    "Linux→ sudo apt install poppler-utils | "
                    "Mac→ brew install poppler",
                    log_widget
                )
                return None

            total_pages = len(images)
            self.log(f"📄 {total_pages} page(s) found — sending to NVIDIA NIM…", log_widget)

            # ── Step 2: Send each page to NVIDIA NIM ─────────────────────
            all_text = ""

            for page_num, image in enumerate(images, start=1):
                self.log(
                    f"🧠 Processing page {page_num}/{total_pages} with NVIDIA NIM…",
                    log_widget
                )

                page_text = self.extract_text_from_image_nvidia(image, page_num, log_widget)

                if page_text:
                    all_text += f"\\n\\n--- Page {page_num} ---\\n{page_text}"
                    self.log(
                        f"✅ Page {page_num}: extracted {len(page_text)} characters",
                        log_widget
                    )
                else:
                    self.log(f"⚠️ Page {page_num}: no text extracted", log_widget)

                # Rate limiting: NVIDIA free tier allows ~10 req/min
                if page_num < total_pages:
                    time.sleep(2)

            if not all_text.strip():
                self.log("❌ No text extracted from any page", log_widget)
                return None

            # ── Step 3: Clean and structure extracted text ────────────────
            all_text = re.sub(r"\\s+", " ", all_text)
            all_text = re.sub(r"(Q\\d+[a-zA-Z]?)", r"\\n\\1:", all_text)

            self.log(
                f"✅ NVIDIA NIM OCR complete. Total characters: {len(all_text)}",
                log_widget
            )
            return all_text.strip()

        except Exception as e:
            self.log(f"❌ NVIDIA NIM OCR failed: {str(e)}", log_widget)
            return None
'''


# ============================================================
# CHANGE 5 — Update extract_text_from_pdf (line ~1092)
# ============================================================

OLD_CHECK = """
        # If PyPDF2 fails or text is too short, use OCR
        if self.use_ocr and OCR_API_KEY:
            self.log(f"  🔄 Using OCR for {source_name}", log_widget)
"""

NEW_CHECK = """
        # If PyPDF2 fails or text is too short, use NVIDIA NIM OCR
        if self.use_ocr and NVIDIA_API_KEY:
            self.log(f"  🔄 Using NVIDIA NIM OCR for {source_name}", log_widget)
"""


# ============================================================
# CHANGE 6 — Update MultiSubjectFairEvaluator.__init__
#            (wherever pdf_processor is created)
# ============================================================

OLD_PROCESSOR_INIT = """
self.pdf_processor = MultiSubjectPDFProcessor(OCR_API_KEY)
"""

NEW_PROCESSOR_INIT = """
self.pdf_processor = MultiSubjectPDFProcessor(NVIDIA_API_KEY)
"""


# ============================================================
# CHANGE 7 — Settings UI (optional but recommended)
#            In create_settings_tab, update the label and variable
# ============================================================

OLD_SETTINGS_LABEL = """
ttk.Label(settings_frame, text="OCR API Key (ocr.space):", ...)
self.ocr_api_key_var = tk.StringVar(value=OCR_API_KEY)
"""

NEW_SETTINGS_LABEL = """
ttk.Label(settings_frame, text="NVIDIA NIM API Key:", ...)
self.nvidia_api_key_var = tk.StringVar(value=NVIDIA_API_KEY)
# Also update save_settings() to save: NVIDIA_API_KEY = self.nvidia_api_key_var.get()
"""

print("""
╔══════════════════════════════════════════════════════════════╗
║        MIGRATION COMPLETE — 7 CHANGES REQUIRED              ║
╠══════════════════════════════════════════════════════════════╣
║  1. Config      → Replace OCR_API_KEY with NVIDIA_API_KEY   ║
║  2. Imports     → Add pdf2image, PIL, io                     ║
║  3. __init__    → Accept nvidia_api_key, set headers         ║
║  4. OCR method  → Full replacement (NVIDIA NIM vision API)   ║
║  5. use_ocr     → Check NVIDIA_API_KEY instead of OCR_API_KEY║
║  6. Processor   → Pass NVIDIA_API_KEY to constructor         ║
║  7. Settings UI → Update label & variable name               ║
╚══════════════════════════════════════════════════════════════╝

Install command:
  pip install pdf2image pillow requests

Get your key at:
  https://build.nvidia.com/nvidia/llama-3_2-11b-vision-instruct
""")
