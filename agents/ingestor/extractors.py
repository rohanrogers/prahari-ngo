"""
Multimodal extraction logic for the Ingestor Agent.
Handles WhatsApp .txt, PDF, images, Excel/CSV using Gemini multimodal.
"""

import re
import json
import logging
import io
from typing import Optional

import pandas as pd

from .prompts import (
    INGESTOR_SYSTEM_PROMPT,
    WHATSAPP_PARSE_INSTRUCTION,
    PDF_PARSE_INSTRUCTION,
    IMAGE_PARSE_INSTRUCTION,
    EXCEL_PARSE_INSTRUCTION,
)
from .schemas import ExtractedVolunteer, ExtractionResult

logger = logging.getLogger(__name__)


def extract_from_whatsapp(text: str) -> ExtractionResult:
    """
    Extract volunteers from WhatsApp .txt export.
    Format: [DD/MM/YY, HH:MM:SS] Name: message
    
    Uses a two-step approach:
    1. Pre-parse to identify potential volunteer messages (contains skills/phone/offers)
    2. Send relevant messages to Gemini for structured extraction
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.gemini_client import generate_text
    
    # Step 1: Pre-filter WhatsApp messages to reduce token usage
    lines = text.strip().split("\n")
    relevant_lines = []
    
    # WhatsApp message pattern
    msg_pattern = re.compile(r'\[?\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\]?\s*-?\s*([^:]+):\s*(.*)')
    
    # Skill/offer keywords that signal a volunteer
    offer_keywords = [
        r'help', r'volunteer', r'available', r'can\s+(?:drive|cook|swim|help)',
        r'boat', r'vehicle', r'medical', r'nurse', r'doctor', r'ready',
        r'count me in', r'i am in', r'i\'m in', r'sign me up',
        r'phone', r'contact', r'\+91', r'\d{10}',
        r'first aid', r'rescue', r'food', r'shelter',
        r'location', r'area', r'district',
    ]
    offer_pattern = re.compile('|'.join(offer_keywords), re.IGNORECASE)
    
    for line in lines:
        match = msg_pattern.match(line)
        if match:
            message_text = match.group(2)
            if offer_pattern.search(message_text) or offer_pattern.search(line):
                relevant_lines.append(line)
        elif relevant_lines and not re.match(r'\[?\d{1,2}[/\-]', line):
            # Continuation of previous message
            relevant_lines[-1] += " " + line.strip()
    
    if not relevant_lines:
        return ExtractionResult(
            volunteers=[],
            reasoning="No volunteer offers detected in WhatsApp export",
            raw_text_preview=text[:200],
        )
    
    # Step 2: Send filtered messages to Gemini
    filtered_text = "\n".join(relevant_lines)
    
    prompt = f"""{WHATSAPP_PARSE_INSTRUCTION}

--- INPUT DATA ---
{filtered_text}
--- END DATA ---

Extract all volunteers as JSON. Remember: only extract people who are OFFERING help."""
    
    try:
        response = generate_text(
            prompt=prompt,
            system_instruction=INGESTOR_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        )
        
        data = json.loads(response)
        volunteers = [ExtractedVolunteer(**v) for v in data.get("volunteers", [])]
        
        return ExtractionResult(
            volunteers=volunteers,
            reasoning=data.get("reasoning", ""),
            raw_text_preview=filtered_text[:200],
        )
    except Exception as e:
        logger.error(f"WhatsApp extraction failed: {e}")
        return ExtractionResult(
            volunteers=[],
            reasoning=f"Extraction failed: {str(e)}",
            raw_text_preview=filtered_text[:200],
            errors=[str(e)],
        )


def extract_from_pdf(file_path: str) -> ExtractionResult:
    """
    Extract volunteers from PDF files.
    Uses PyMuPDF for text extraction + Gemini for structured parsing.
    Falls back to Gemini multimodal for scanned/image PDFs.
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.gemini_client import generate_text, generate_multimodal, upload_file
    
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if len(text.strip()) > 50:
            # Text-based PDF — use text extraction
            prompt = f"""{PDF_PARSE_INSTRUCTION}

--- PDF TEXT CONTENT ---
{text}
--- END CONTENT ---

Extract all volunteers as JSON."""
            
            response = generate_text(
                prompt=prompt,
                system_instruction=INGESTOR_SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
            )
        else:
            # Scanned PDF — use multimodal
            file_part = upload_file(file_path, mime_type="application/pdf")
            prompt = f"""{PDF_PARSE_INSTRUCTION}

This appears to be a scanned document. Use OCR to extract the content.
Extract all volunteers as JSON."""
            
            response = generate_multimodal(
                parts=[file_part, prompt],
                system_instruction=INGESTOR_SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
            )
        
        data = json.loads(response)
        volunteers = [ExtractedVolunteer(**v) for v in data.get("volunteers", [])]
        
        return ExtractionResult(
            volunteers=volunteers,
            reasoning=data.get("reasoning", ""),
            raw_text_preview=text[:200] if text else "(scanned PDF)",
        )
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ExtractionResult(errors=[str(e)])


def extract_from_image(file_path: str) -> ExtractionResult:
    """
    Extract volunteers from images (handwritten registers, printed forms, badges).
    Uses Gemini multimodal for OCR + structured extraction.
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.gemini_client import generate_multimodal, upload_file
    
    try:
        file_part = upload_file(file_path)
        
        prompt = f"""{IMAGE_PARSE_INSTRUCTION}

Extract all volunteers visible in this image as JSON."""
        
        response = generate_multimodal(
            parts=[file_part, prompt],
            system_instruction=INGESTOR_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        )
        
        data = json.loads(response)
        volunteers = [ExtractedVolunteer(**v) for v in data.get("volunteers", [])]
        
        return ExtractionResult(
            volunteers=volunteers,
            reasoning=data.get("reasoning", ""),
            raw_text_preview="(image input)",
        )
    except Exception as e:
        logger.error(f"Image extraction failed: {e}")
        return ExtractionResult(errors=[str(e)])


def extract_from_excel(file_path: str) -> ExtractionResult:
    """
    Extract volunteers from Excel/CSV files.
    Uses Pandas for initial parsing, Gemini for schema inference if needed.
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.gemini_client import generate_text
    
    try:
        # Read the file
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        
        # Convert to text for Gemini (first 100 rows to limit tokens)
        sample = df.head(100)
        csv_text = sample.to_csv(index=False)
        
        prompt = f"""{EXCEL_PARSE_INSTRUCTION}

--- SPREADSHEET DATA (first {len(sample)} rows) ---
Columns: {', '.join(df.columns.tolist())}

{csv_text}
--- END DATA ---

Total rows in file: {len(df)}
Extract all volunteers as JSON."""
        
        response = generate_text(
            prompt=prompt,
            system_instruction=INGESTOR_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        )
        
        data = json.loads(response)
        volunteers = [ExtractedVolunteer(**v) for v in data.get("volunteers", [])]
        
        return ExtractionResult(
            volunteers=volunteers,
            reasoning=data.get("reasoning", ""),
            raw_text_preview=csv_text[:200],
        )
    except Exception as e:
        logger.error(f"Excel/CSV extraction failed: {e}")
        return ExtractionResult(errors=[str(e)])


def extract_from_text(text: str) -> ExtractionResult:
    """
    Generic text extraction — for demo/test endpoint.
    Accepts any raw text and attempts volunteer extraction.
    """
    # Auto-detect if it's WhatsApp format
    whatsapp_pattern = re.compile(r'\[?\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}')
    if whatsapp_pattern.search(text[:100]):
        return extract_from_whatsapp(text)
    
    # Otherwise, generic extraction
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.gemini_client import generate_text
    
    try:
        prompt = f"""The following is raw text data that may contain volunteer information.
Extract all volunteer records you can find.

--- INPUT ---
{text}
--- END INPUT ---

Extract all volunteers as JSON."""
        
        response = generate_text(
            prompt=prompt,
            system_instruction=INGESTOR_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
        )
        
        data = json.loads(response)
        volunteers = [ExtractedVolunteer(**v) for v in data.get("volunteers", [])]
        
        return ExtractionResult(
            volunteers=volunteers,
            reasoning=data.get("reasoning", ""),
            raw_text_preview=text[:200],
        )
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return ExtractionResult(errors=[str(e)])
