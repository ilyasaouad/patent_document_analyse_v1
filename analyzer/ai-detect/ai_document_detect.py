import os
import glob

class ai_detect_analyse:
    def __init__(self, input_dir: str):
        """
        Initialize the analyzer with the directory containing output documents.
        """
        self.input_dir = input_dir
        self.documents = []
        self._load_documents()

    def _load_documents(self):
        """
        Loads all markdown files from the specified input directory.
        Finds all readied md files (like description_only.md, claims_from_description.md, etc.)
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
                print(f"Successfully loaded {os.path.basename(file_path)} for analysis")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                
        print(f"Loaded {len(self.documents)} document(s) in total ready for deeper analysis.")

    def run_analysis(self):
        """
        Placeholder method for the deeper AI analysis logic on the cleanly extracted documents.
        """
        if not self.documents:
            print("No documents loaded to analyze.")
            return
            
        print(f"\n--- Starting deeper analysis on {len(self.documents)} document(s) ---")
        for doc in self.documents:
            # Insert logic here to pass through an LLM, extract issues, validate claims, etc.
            print(f"Analyzing {doc['file_name']} (length: {len(doc['content'])} characters)")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    analyzer_dir = os.path.dirname(current_dir)
    document_dir = os.path.join(analyzer_dir, "document_text_output")
    
    print(f"Starting Deep AI Analysis looking in: {document_dir}")
    analyzer = ai_detect_analyse(input_dir=document_dir)
    analyzer.run_analysis()
