import os
import configparser
import pysftp  # Requires: pip install pysftp
import stat    # For checking if an item is a file or directory

def download_all_files_from_sftp_root():
    """
    Connects to an SFTP server using credentials from config.ini,
    navigates to the root directory, and downloads all files found there
    to the local 'Workday XML Downloads/' directory.
    """
    config = configparser.ConfigParser()
    config_file_path = 'config.ini'  # Assumes config.ini is in the same directory as this script

    if not os.path.exists(config_file_path):
        print(f"ERROR: Configuration file '{config_file_path}' not found.")
        print("Please ensure config.ini exists in the script's directory.")
        return

    try:
        config.read(config_file_path)
    except configparser.Error as e_cfg_read:
        print(f"ERROR: Could not read or parse config.ini: {e_cfg_read}")
        return

    # Validate sections and keys from config.ini
    if not config.has_section('Paths') or not config.has_section('SFTP'):
        print("ERROR: Missing 'Paths' or 'SFTP' section in config.ini.")
        print("Please ensure both sections and their required keys are present.")
        return

    paths_config = config['Paths']
    sftp_config = config['SFTP']

    required_paths_keys = ['workday_xml_downloads']
    required_sftp_keys = ['Hostname', 'Port', 'Username', 'Password']

    missing_paths_keys = [key for key in required_paths_keys if key not in paths_config]
    missing_sftp_keys = [key for key in required_sftp_keys if key not in sftp_config]

    if missing_paths_keys:
        print(f"ERROR: Missing key(s) in [Paths] section of config.ini: {', '.join(missing_paths_keys)}")
        return
    if missing_sftp_keys:
        print(f"ERROR: Missing key(s) in [SFTP] section of config.ini: {', '.join(missing_sftp_keys)}")
        return

    local_download_dir = paths_config['workday_xml_downloads']
    sftp_host = sftp_config['Hostname']
    sftp_user = sftp_config['Username']
    sftp_pass = sftp_config['Password']
    
    try:
        sftp_port = int(sftp_config['Port'])
    except ValueError:
        print(f"ERROR: SFTP Port '{sftp_config['Port']}' in config.ini is not a valid number.")
        return
        
    remote_target_dir = '/'  # Root directory on the SFTP server

    # Ensure local download directory exists
    try:
        os.makedirs(local_download_dir, exist_ok=True)
        abs_local_download_dir = os.path.abspath(local_download_dir)
        print(f"Local download directory: {abs_local_download_dir}")
    except OSError as e_mkdir:
        print(f"ERROR: Could not create local download directory '{local_download_dir}': {e_mkdir}")
        return

    # SFTP connection options.
    # By default, pysftp performs host key checking using your system's known_hosts file.
    # If the server's host key is not known, the connection will fail for security.
    cnopts = pysftp.CnOpts()
    # If you must disable host key checking (NOT RECOMMENDED - SECURITY RISK), uncomment below:
    # cnopts.hostkeys = None 
    # print("WARNING: Host key checking is disabled! This is a security risk.")

    print(f"Attempting to connect to SFTP server: {sftp_host} on port {sftp_port} as user '{sftp_user}'...")

    try:
        with pysftp.Connection(host=sftp_host, username=sftp_user, password=sftp_pass, port=sftp_port, cnopts=cnopts) as sftp:
            print(f"Successfully connected to SFTP server.")
            
            print(f"Changing remote directory to: '{remote_target_dir}'")
            sftp.cwd(remote_target_dir)
            print(f"Current remote directory: {sftp.pwd}")

            print(f"Listing items in remote directory '{sftp.pwd}'...")
            remote_items = sftp.listdir_attr()
            
            downloaded_count = 0
            skipped_count = 0
            error_count = 0

            if not remote_items:
                print("No files or directories found in the remote root directory.")
            else:
                print(f"Found {len(remote_items)} items. Attempting to download files...")
                for item_attr in remote_items:
                    item_name = item_attr.filename
                    # remote_item_path = item_name # Path is relative to current remote directory

                    # Check if the item is a regular file (not a directory, symlink, etc.)
                    if stat.S_ISREG(item_attr.st_mode):
                        local_item_path = os.path.join(local_download_dir, item_name)
                        
                        print(f"  Downloading '{item_name}' to '{local_item_path}'...")
                        try:
                            sftp.get(item_name, local_item_path) # item_name is relative to sftp.pwd
                            print(f"    Successfully downloaded '{item_name}'.")
                            downloaded_count += 1
                        except Exception as e_file:
                            print(f"    ERROR downloading '{item_name}': {e_file}")
                            error_count += 1
                    else:
                        print(f"  Skipping non-file item: '{item_name}' (Type: {stat.S_IFMT(item_attr.st_mode)})")
                        skipped_count += 1
            
            print("\nDownload summary:")
            print(f"  Successfully downloaded: {downloaded_count} file(s)")
            print(f"  Skipped (non-files): {skipped_count} item(s)")
            print(f"  Errors during download: {error_count} file(s)")

    except pysftp.ConnectionException as e_conn:
        print(f"SFTP Connection Error: {e_conn}")
        print("Troubleshooting tips:")
        print("- Check your SFTP server details (Hostname, Port) in config.ini.")
        print("- Verify your network connection and firewall settings.")
        print("- Ensure the SFTP server is running and accessible.")
        print("- If this is the first time connecting, the server's host key might not be in your system's 'known_hosts' file.")
        print("  You may need to connect once manually with an SFTP client to accept the host key, or investigate cnopts for host key management.")
    except pysftp.CredentialException: # Avoid printing the exception itself which might echo credentials
        print(f"SFTP Authentication Error for user '{sftp_user}'.")
        print("Please verify your SFTP username and password in config.ini.")
    except pysftp.SSHException as e_ssh:
        print(f"SFTP SSH Protocol Error: {e_ssh}")
        print("This could be due to various SSH issues, including host key problems, incompatible ciphers, or server-side SSH configuration.")
    except Exception as e_general:
        print(f"An unexpected error occurred: {e_general}")

if __name__ == '__main__':
    print("--- SFTP File Download Script ---")
    print("IMPORTANT:")
    print("1. Ensure you have the 'pysftp' library installed (e.g., via 'pip install pysftp').")
    print("2. For security, this script relies on your system's 'known_hosts' file for SFTP server verification.")
    print("   If the server's host key is not known, the connection may fail. Connect manually once if needed.")
    print("3. The SFTP password in config.ini is stored in plain text.")
    print("   Ensure config.ini file permissions are restricted to prevent unauthorized access.\n")
    
    download_all_files_from_sftp_root()
    
    print("\n--- SFTP download process finished. ---") 