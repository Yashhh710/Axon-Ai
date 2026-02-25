import os
import re
import sys
import subprocess
import json
from groq import Groq
from dotenv import load_dotenv

# Load neural config
load_dotenv()

class AxonFullStackWriter:
    """
    AXON AI - High-Fidelity Code Synthesis Engine
    Generates, extracts, and deploys fully functional codebases.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("\n❌ Error: GROQ_API_KEY missing.")
            print("Please add 'GROQ_API_KEY=your_key' to your .env file.")
            sys.exit(1)
            
        self.client = Groq(api_key=self.api_key)
        # Fallback list for maximum reliability
        self.models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    def _get_completion(self, prompt):
        """Internal call with multi-model fallback logic"""
        system_prompt = (
            "You are the AXON Code Synthesis Engine. Your purpose is to generate ONLY "
            "fully functional, production-ready code. \n"
            "RULES:\n"
            "1. Output valid code blocks only.\n"
            "2. If multiple files are needed, use blocks with filenames: 'File: path/to/file.ext'\n"
            "3. Include all imports and logic. Zero placeholders.\n"
            "4. No conversational preamble."
        )

        for model in self.models:
            try:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2, # High precision
                    max_tokens=4096
                )
                return completion.choices[0].message.content, model
            except Exception as e:
                err = str(e)
                if "429" in err or "400" in err or "model_decommissioned" in err:
                    print(f"⚠️ {model} limited/unavailable. Failing over...")
                    continue
                else:
                    return f"Error: {err}", None
        return "Error: All neural links offline.", None

    def extract_and_save(self, neural_output, target_dir="synthesis_output"):
        """Extracts files from output and saves them locally"""
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Pattern to find File names and code blocks
        # Matches: File: filename.py \n ```python ... ```
        file_pattern = r"File:\s*([^\n`]+)\s*[\n\r]*```(?:\w+)?\n(.*?)\n```"
        matches = re.findall(file_pattern, neural_output, re.DOTALL)

        if not matches:
            # Fallback: Just look for any code block and save as 'generated_code.txt'
            simple_block = re.search(r"```(?:\w+)?\n(.*?)\n```", neural_output, re.DOTALL)
            if simple_block:
                content = simple_block.group(1)
                matches = [("generated_output.txt", content)]
            else:
                return False, "No code blocks found in synthesis stream."

        saved_files = []
        for filename, content in matches:
            filename = filename.strip()
            filepath = os.path.join(target_dir, filename)
            
            # Ensure subdirectories exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content.strip())
            saved_files.append(filepath)
            
        return True, saved_files

    def run_synthesis(self):
        print("\n" + "="*50)
        print("   AXON AI - FULL STACK CODE SYNTHESIS ENGINE   ")
        print("="*50 + "\n")
        
        while True:
            prompt = input("🚀 What should I build? (Project prompt): ").strip()
            if prompt.lower() in ['exit', 'quit', 'q']: break
            
            project_name = input("📁 Project Folder Name [synthesis_out]: ").strip() or "synthesis_out"
            
            print(f"\n[NEURAL] Synchronizing with AXON clusters...")
            raw_output, used_model = self._get_completion(prompt)
            
            if raw_output.startswith("Error"):
                print(f"❌ {raw_output}")
                continue

            print(f"[NEURAL] Synthesis complete via {used_model}. Deploying files...")
            
            success, result = self.extract_and_save(raw_output, project_name)
            
            if success:
                print(f"\n✅ PROJECT DEPLOYED: ./{project_name}/")
                for f in result:
                    print(f"   📄 {os.path.basename(f)}")
                
                # Check for requirements.txt to offer installation
                req_path = os.path.join(project_name, "requirements.txt")
                if os.path.exists(req_path):
                    install = input(f"\n📦 'requirements.txt' detected. Install dependencies? (y/n): ").lower()
                    if install == 'y':
                        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path])
            else:
                print(f"❌ Deployment failed: {result}")
            
            print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    try:
        engine = AxonFullStackWriter()
        engine.run_synthesis()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Engine shutdown safely.")
