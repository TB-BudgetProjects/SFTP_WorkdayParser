import os
import configparser
import pysftp  # Requires: pip install pysftp

def upload_parsed_csvs_to_sftp():
    """
    Connects to an SFTP server using credentials from config.ini,
    and uploads all files from the local 'Parsed CSVs/' directory
    to the '/parsed_csv_uploads/' directory on the SFTP server.
    """
    config = configparser.ConfigParser()
    config_file_path = 'config.ini'  # Assumes config.ini is in the same directory as this script

    if not os.path.exists(config_file_path):
        print(f"ERROR: Configuration file '{config_file_path}' not found.")
        return

    try:
        config.read(config_file_path)
    except configparser.Error as e_cfg_read:
        print(f"ERROR: Could not read or parse config.ini: {e_cfg_read}")
        return

    # Validate sections and keys
    if not config.has_section('Paths') or not config.has_section('SFTP'):
        print("ERROR: Missing 'Paths' or 'SFTP' section in config.ini.")
        return

    paths_config = config['Paths']
    sftp_config = config['SFTP']

    required_paths_keys = ['parsed_csvs']
    required_sftp_keys = ['Hostname', 'Port', 'Username', 'Password']

    missing_paths_keys = [key for key in required_paths_keys if key not in paths_config]
    missing_sftp_keys = [key for key in required_sftp_keys if key not in sftp_config]

    if missing_paths_keys:
        print(f"ERROR: Missing key(s) in [Paths] section of config.ini: {', '.join(missing_paths_keys)}")
        return
    if missing_sftp_keys:
        print(f"ERROR: Missing key(s) in [SFTP] section of config.ini: {', '.join(missing_sftp_keys)}")
        return

    local_parsed_csv_dir = paths_config['parsed_csvs']
    sftp_host = sftp_config['Hostname']
    sftp_user = sftp_config['Username']
    sftp_pass = sftp_config['Password']
    try:
        sftp_port = int(sftp_config['Port'])
    except ValueError:
        print(f"ERROR: SFTP Port '{sftp_config['Port']}' in config.ini is not a valid number.")
        return

    remote_upload_dir = '/parsed_csv_uploads/'  # As specified by the user

    if not os.path.isdir(local_parsed_csv_dir):
        print(f"ERROR: Local directory for parsed CSVs '{local_parsed_csv_dir}' not found or is not a directory.")
        print("Please ensure it exists and contains the CSV files to upload.")
        return

    local_files_to_upload = [
        f for f in os.listdir(local_parsed_csv_dir)
        if os.path.isfile(os.path.join(local_parsed_csv_dir, f))
    ]

    if not local_files_to_upload:
        print(f"No files found in local directory '{local_parsed_csv_dir}' to upload.")
        return

    print(f"Found {len(local_files_to_upload)} file(s) in '{local_parsed_csv_dir}' for upload.")

    cnopts = pysftp.CnOpts()
    # See download_sftp_files.py for notes on host key checking.

    print(f"Attempting to connect to SFTP server: {sftp_host} on port {sftp_port} as user '{sftp_user}'...")

    try:
        with pysftp.Connection(host=sftp_host, username=sftp_user, password=sftp_pass, port=sftp_port, cnopts=cnopts) as sftp:
            print(f"Successfully connected to SFTP server.")

            print(f"Ensuring remote directory '{remote_upload_dir}' exists...")
            if not sftp.exists(remote_upload_dir):
                print(f"Remote directory '{remote_upload_dir}' does not exist. Attempting to create it.")
                try:
                    sftp.makedirs(remote_upload_dir) 
                    print(f"Successfully created remote directory: {remote_upload_dir}")
                except Exception as e_mkdir_remote:
                    print(f"ERROR: Could not create remote directory '{remote_upload_dir}'. Please create it manually. Details: {e_mkdir_remote}")
                    return 
            elif not sftp.isdir(remote_upload_dir):
                print(f"ERROR: The remote path '{remote_upload_dir}' exists but is not a directory.")
                return
            else:
                print(f"Remote directory '{remote_upload_dir}' confirmed.")

            sftp.cwd(remote_upload_dir)
            print(f"Changed remote directory to: {sftp.pwd}")
            
            uploaded_count = 0
            error_count = 0

            for file_name in local_files_to_upload:
                local_file_path = os.path.join(local_parsed_csv_dir, file_name)
                remote_file_path = file_name # Will be relative to the current remote directory (remote_upload_dir)
                
                print(f"  Uploading '{local_file_path}' to '{sftp.pwd}/{remote_file_path}'...")
                try:
                    sftp.put(local_file_path, remote_file_path)
                    print(f"    Successfully uploaded '{file_name}'.")
                    uploaded_count += 1
                except Exception as e_file:
                    print(f"    ERROR uploading '{file_name}': {e_file}")
                    error_count += 1
            
            print("\nUpload summary:")
            print(f"  Successfully uploaded: {uploaded_count} file(s)")
            print(f"  Errors during upload: {error_count} file(s)")

    except pysftp.ConnectionException as e_conn:
        print(f"SFTP Connection Error: {e_conn}")
    except pysftp.CredentialException:
        print(f"SFTP Authentication Error for user '{sftp_user}'. Verify credentials in config.ini.")
    except pysftp.SSHException as e_ssh:
        print(f"SFTP SSH Protocol Error: {e_ssh}")
    except Exception as e_general:
        print(f"An unexpected error occurred: {e_general}")

if __name__ == '__main__':
    print("--- SFTP Parsed File Upload Script ---")
    print("IMPORTANT: Review security notes in download_sftp_files.py regarding host keys and password storage.")
    
    upload_parsed_csvs_to_sftp()
    
    print("\n--- SFTP upload process finished. ---") 