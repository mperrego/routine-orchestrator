import os
import sys

def main():
    # 1. Determine the directory of the script
    # This ensures the .txt file lands next to the orchestrator
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, "testscript_output.txt")

    message = "Success! The Routine Orchestrator successfully executed this script."

    try:
        # 2. Write to the text file
        with open(output_path, "w") as f:
            f.write(message)
        
        # 3. Print to the shell (IDLE or Command Line)
        print("\n" + "="*40)
        print(message)
        print(f"File saved to: {output_path}")
        print("="*40 + "\n")
        
        # Exit with code 0 (Success)
        sys.exit(0)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Exit with code 1 (Failure)
        sys.exit(1)

if __name__ == "__main__":
    main()
