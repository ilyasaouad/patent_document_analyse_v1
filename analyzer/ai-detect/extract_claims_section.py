import os
import glob
import re
import requests
import json

class ClaimsExtractor:
    def __init__(self, input_dir: str):
        self.input_dir = input_dir
        self.documents = []
        self._load_documents()

    def _load_documents(self):
        """
        Loads all markdown files to check if claims are missing.
        """
        if not os.path.isdir(self.input_dir):
            print(f"Error: Directory '{self.input_dir}' does not exist.")
            return

        search_pattern = os.path.join(self.input_dir, "*.md")
        md_files = glob.glob(search_pattern)
        
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.documents.append({
                        "file_name": os.path.basename(file_path),
                        "file_path": file_path,
                        "content": content
                    })
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                
        # Trigger the extraction process
        self.extract_if_missing()

    def extract_if_missing(self):
        """
        Check if 'claims.md' or 'claims_from_description.md' is among the loaded documents.
        If not, attempt to extract the claims section from 'description.md'.
        """
        has_claims = any(doc['file_name'] in ['claims.md', 'claims_from_description.md'] for doc in self.documents)
        if has_claims:
            return
            
        # Claims are missing, look for description.md
        desc_doc = next((doc for doc in self.documents if doc['file_name'] == 'description.md'), None)
        if not desc_doc:
            return  # No description to extract from
            
        # --- AUTOMATED BACKEND DECISION LOGIC ---
        # 0. Clean isolated OCR margin line numbers (e.g., 5, 10, 15) out of the entire document
        orig_text = self._clean_margin_numbers(desc_doc['content'])
        orig_len = len(orig_text)
        
        # 1. Attempt Regex Extraction first (Fast and exact)
        final_claims, final_remaining = self._extract_claims_regex(orig_text)
        
        # Evaluate if Regex did a good job:
        # - It must have found something (> 50 chars)
        # - It shouldn't have accidentally grabbed the entire document (< 90% of original length)
        is_regex_good = final_claims and len(final_claims) > 50 and len(final_claims) < (orig_len * 0.9)
        
        if not is_regex_good:
            print("Regex extraction failed or seemed invalid. Automatically triggering LLM fallback...")
            # 2. If Regex is bad, execute the heavy LLM extraction
            llm_claims, llm_remaining = self._extract_claims_llm_fallback(orig_text)
            
            # If LLM extracted something, we trust it over the failed Regex
            if llm_claims and len(llm_claims) > 50:
                final_claims = llm_claims
                final_remaining = llm_remaining
                print("LLM extraction accepted.")
            else:
                print("LLM extraction also failed. Reverting to whatever Regex found (if anything).")
        else:
            print("Regex extraction successfully validated. Bypassing LLM.")
            
        # --- Save the Final Decided Outputs ---
        if final_claims:
            claims_file_name = "claims_from_description.md"
            claims_file_path = os.path.join(self.input_dir, claims_file_name)
            
            desc_only_file_name = "description_only.md"
            desc_only_file_path = os.path.join(self.input_dir, desc_only_file_name)
            
            try:
                # Write the definitive claims
                with open(claims_file_path, 'w', encoding='utf-8') as f:
                    f.write(final_claims)
                    
                # Write the remaining description
                with open(desc_only_file_path, 'w', encoding='utf-8') as f:
                    f.write(final_remaining)
                    
                # Delete the original description.md so downstream analysis only reads the split files
                orig_desc_path = desc_doc['file_path']
                if os.path.exists(orig_desc_path):
                    os.remove(orig_desc_path)
                
                print(f"Successfully saved definitive backend claims to {claims_file_name}")
                print(f"Updated description saved as {desc_only_file_name}")
            except Exception as e:
                print(f"Error saving updated files: {e}")

    def _clean_margin_numbers(self, text: str) -> str:
        """
        Cleans OCR margin line numbers (like 1, 5, 10, 15) that get accidentally scattered 
        throughout the text during OCR, taking care NOT to delete actual Claim numbers (like '1. A method').
        """
        # 1. Remove standalone numbers on their own lines (e.g., just '15' or '\n10\n')
        cleaned = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # 2. Remove OCR margin numbers stuck inside markdown headers (e.g., '# 5 DESCRIPTION' -> '# DESCRIPTION')
        cleaned = re.sub(r'^(#+)\s*\d+\s+', r'\1 ', cleaned, flags=re.MULTILINE)
        
        # 3. Remove numbers at the start of a normal text line WITHOUT a period.
        # This prevents deleting actual Claim numbers ('1. A method') or section numbers ('1.1 Overview').
        # It matches things like "35 The system uses" and deletes the "35 ".
        cleaned = re.sub(r'^\s*\d+\s+(?=[A-Za-z])', '', cleaned, flags=re.MULTILINE)
        
        # 4. Clean up the blank spaces/newlines left behind from deleting standalone numbers
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()

    def _extract_claims_regex(self, text: str) -> tuple[str, str]:
        """
        Detects and extracts the claims section from the description text using standard regular expressions.
        Returns a tuple: (extracted_claims_text, remaining_description_text)
        """
        pattern = re.compile(r'^(#*\s*(?:PATENT\s+)?CLAIMS?|PATENTKRAV|KRAV)\s*$', re.IGNORECASE | re.MULTILINE)
        
        match = pattern.search(text)
        if not match:
            return "", text
            
        start_idx = match.start()
        
        end_pattern = re.compile(r'^(#+\s*ABSTRACT|SAMMENDRAG)\s*$', re.IGNORECASE | re.MULTILINE)
        end_match = end_pattern.search(text, match.end())
        
        if end_match:
            end_idx = end_match.start()
            claims_text = text[start_idx:end_idx].strip()
            rest_of_text = (text[:start_idx] + "\n\n" + text[end_idx:]).strip()
            return claims_text, rest_of_text
        else:
            claims_text = text[start_idx:].strip()
            rest_of_text = text[:start_idx].strip()
            return claims_text, rest_of_text
            
    def _extract_claims_llm_fallback(self, text: str) -> tuple[str, str]:
        """
        Method using a local Ollama LLM (gpt-oss:120b-cloud) to test LLM extraction.
        """
        print("\n--- [DEBUG: LLM EXTRACTION] ---")
        print("Starting LLM extraction logic (Model: gpt-oss:120b-cloud)...")
        
        url = "http://localhost:11434/api/generate"
        print(f"Target API Endpoint: {url}")
        
        prompt = (
            "You are an expert patent document analyzer. "
            "I will provide you with the text of a patent description. "
            "Your task is to identify and extract ONLY the 'Claims' or 'Patent Claims' section of the patent. "
            "Please return ONLY the exact extracted claims text. Do not add any preamble, explanations, or conversational text. "
            f"\n\n--- Patent Description ---\n{text}"
        )
        
        payload = {
            "model": "gpt-oss:120b-cloud",
            "prompt": prompt,
            "stream": False
        }
        
        print(f"Sending prompt payload of length: {len(prompt)} characters.")
        
        try:
            # We use a relatively high timeout as local LLM inference on large models can take time
            print("Awaiting response from Ollama (this might take a few moments depending on the model size)...")
            response = requests.post(url, json=payload, timeout=300)
            
            print(f"Ollama API Status Code: {response.status_code}")
            
            if response.status_code == 200:
                claims_text = response.json().get("response", "").strip()
                print(f"Received LLM response. Length: {len(claims_text)} characters.")
                
                if not claims_text:
                    print("LLM returned an empty string.")
                    return "", text
                    
                print(f"Preview of LLM Output:\n{claims_text[:150]}...\n")
                
                # Try to perfectly strip it from the original text if it matched line-for-line
                if claims_text in text:
                    print("Success! LLM output perfectly matched a substring in the original description. Separating cleanly.")
                    rest_of_text = text.replace(claims_text, "").strip()
                    print("--- [END DEBUG] ---\n")
                    return claims_text, rest_of_text
                    
                # If LLM slightly reformatted the text, try to find the start and end via fuzzy boundaries
                print("LLM output is not an exact 1-to-1 matching substring. Attempting fuzzy boundary detection...")
                start_substring = claims_text[:50]
                end_substring = claims_text[-50:]
                start_idx = text.find(start_substring)
                end_idx = text.rfind(end_substring)
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    print(f"Fuzzy match successful: Found mapped boundaries at Start Index [{start_idx}] and End Index [{end_idx + len(end_substring)}].")
                    # Found exact bounds in the original text, yielding perfect extraction
                    exact_claims = text[start_idx:end_idx + len(end_substring)]
                    rest_of_text = (text[:start_idx] + "\n\n" + text[end_idx + len(end_substring):]).strip()
                    print("--- [END DEBUG] ---\n")
                    return exact_claims, rest_of_text
                
                # Absolute fallback: return LLM's raw text, leave original text intact
                print("Warning: Could not perfectly map the LLM's generated text back into the original description string.")
                print("Fallback triggered: Saving LLM text as claims, but leaving description_only.md fully intact (un-split).")
                print("--- [END DEBUG] ---\n")
                return claims_text, text
            else:
                print(f"Ollama API returned an error: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to Ollama fallback API: {e}")
            
        print("LLM extraction completely failed. Returning original un-split text.")
        print("--- [END DEBUG] ---\n")
        return "", text

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    analyzer_dir = os.path.dirname(current_dir)
    document_dir = os.path.join(analyzer_dir, "document_text_output")
    print(f"Running ClaimsExtractor on: {document_dir}")
    extractor = ClaimsExtractor(input_dir=document_dir)
