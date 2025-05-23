import subprocess
import sys
import os

# List of parser scripts to execute
# Note: Ensure these filenames are exact and exist in the "Parsing Scripts" folder
PARSER_SCRIPTS = [
    "xml_parser_costing_allocations_daily.py",
    "xml_parser_position_master.py",
    "xml_parser_position_compensation.py",
    "xml_parser_worktag_grant.py",
    "xml_parser_worktag_program.py"
]

def run_script(script_name):
    """Executes a single parsing script and prints its output."""
    script_path = os.path.join(os.path.dirname(__file__), script_name) # Assumes script is in the same directory
    
    if not os.path.exists(script_path):
        print(f"--- ERROR: Script not found: {script_name} at {script_path} ---")
        return False

    print(f"--- Running {script_name} ---")
    try:
        # sys.executable ensures we use the same Python interpreter that's running this script
        # cwd is set to the directory of this script, which should allow child scripts to find config.ini
        process = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False, # Do not raise an exception on non-zero exit codes
            cwd=os.path.dirname(__file__) # Set current working directory for the child script
        )
        
        if process.stdout:
            print("Output:")
            print(process.stdout)
        if process.stderr:
            print("Errors:")
            print(process.stderr)
        
        if process.returncode == 0:
            print(f"--- {script_name} completed successfully ---")
            return True
        else:
            print(f"--- {script_name} failed with return code {process.returncode} ---")
            return False
            
    except Exception as e:
        print(f"--- An exception occurred while trying to run {script_name}: {e} ---")
        return False

if __name__ == "__main__":
    print("Starting execution of all parsing scripts...")
    all_successful = True
    
    for script in PARSER_SCRIPTS:
        print("\n" + "="*50 + "\n")
        if not run_script(script):
            all_successful = False
            
    print("\n" + "="*50)
    if all_successful:
        print("All parsing scripts completed successfully.")
    else:
        print("Some parsing scripts failed. Please check the output above for details.")