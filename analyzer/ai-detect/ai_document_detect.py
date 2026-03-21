import os
import glob
import re

class ai_detect_analyse:
    def __init__(self, input_dir: str):
        """
        Initialize the analyzer with the directory containing output documents.
        
        Args:
            input_dir (str): Path to the directory containing markdown files 
                             (e.g., 'document_text_output').
        """
        self.input_dir = input_dir
        self.documents = []
        self._load_documents()

    def _load_documents(self):
        """
        Loads all markdown files from the specified input directory.
        Since there could be 1, 2, or 3 md files, it will dynamically find and read all of them.
        """
        if not os.path.isdir(self.input_dir):
            print(f"Error: Directory '{self.input_dir}' does not exist.")
            return

        # Search for all markdown files in the input directory
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
                print(f"Successfully loaded {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                
        # After loading all available md files, check if claims are missing
        self._ensure_claims_exist()

        print(f"Loaded {len(self.documents)} document(s) in total for analysis.")

    def _ensure_claims_exist(self):
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
            
        extracted_claims, remaining_desc = self._extract_claims_text(desc_doc['content'])
        
        if extracted_claims:
            # Save the claims document
            claims_file_name = "claims_from_description.md"
            claims_file_path = os.path.join(self.input_dir, claims_file_name)
            
            # Save the rest of the description
            desc_only_file_name = "description_only.md"
            desc_only_file_path = os.path.join(self.input_dir, desc_only_file_name)
            
            try:
                # Write extracted claims
                with open(claims_file_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_claims)
                    
                # Write the remaining description
                with open(desc_only_file_path, 'w', encoding='utf-8') as f:
                    f.write(remaining_desc)
                    
                # Delete the original description.md
                orig_desc_path = desc_doc['file_path']
                if os.path.exists(orig_desc_path):
                    os.remove(orig_desc_path)
                
                # Update the loaded documents list
                self.documents.remove(desc_doc)
                
                self.documents.append({
                    "file_name": claims_file_name,
                    "file_path": claims_file_path,
                    "content": extracted_claims
                })
                
                self.documents.append({
                    "file_name": desc_only_file_name,
                    "file_path": desc_only_file_path,
                    "content": remaining_desc
                })
                
                print(f"Successfully extracted claims from description and saved as {claims_file_name}")
                print(f"Updated description saved as {desc_only_file_name}")
            except Exception as e:
                print(f"Error saving updated files: {e}")

    def _extract_claims_text(self, text: str) -> tuple[str, str]:
        """
        Detects and extracts the claims section from the description text.
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

    def run_analysis(self):
        """
        Placeholder method for the deeper analysis logic.
        """
        if not self.documents:
            print("No documents loaded to analyze.")
            return
            
        print(f"\n--- Starting analysis on {len(self.documents)} document(s) ---")
        for doc in self.documents:
            # Here you will implement your deeper analysis logic
            print(f"Analyzing {doc['file_name']} (length: {len(doc['content'])} characters)")


if __name__ == "__main__":
    # Example usage:
    # Assuming this script is run from within the specific directory structure:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level (to analyzer) and then into document_text_output
    analyzer_dir = os.path.dirname(current_dir)
    document_dir = os.path.join(analyzer_dir, "document_text_output")
    
    print(f"Looking for documents in: {document_dir}")
    analyzer = ai_detect_analyse(input_dir=document_dir)
    analyzer.run_analysis()
