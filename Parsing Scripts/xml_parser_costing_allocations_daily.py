import xml.etree.ElementTree as ET
import csv
import os
import configparser
from datetime import datetime

# Initialize config parser and read config file
config = configparser.ConfigParser()
# Assume config.ini is in the parent directory of 'Parsing Scripts'
config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
config.read(config_file_path)

# Get base paths from config, ensuring they are absolute or correctly relative to config.ini's location
config_base_dir = os.path.dirname(os.path.abspath(config_file_path))
xml_dir = os.path.join(config_base_dir, config['Paths']['workday_xml_downloads'])
csv_dir = os.path.join(config_base_dir, config['Paths']['parsed_csvs'])

# Define the input XML file (misnamed as .csv) and output CSV file using resolved paths
xml_input_file_name = 'position_costing_allocations_daily.csv' # Original filename
csv_output_file_name = 'parsed_position_costing_allocations_daily.csv' # Original filename

xml_input_file = os.path.join(xml_dir, xml_input_file_name)
csv_output_file = os.path.join(csv_dir, csv_output_file_name)

# Create output directory if it doesn't exist
os.makedirs(csv_dir, exist_ok=True)

# Define namespace for the report - Reverted to original presumed value
NAMESPACE = {'wd': 'urn:com.workday.report/RPT-INTF-S111B-(NSHE)_CSN_PositionFunding-Actuals'} 

# Register namespace
ET.register_namespace('wd', NAMESPACE['wd'])

# Define the headers for the CSV file
headers = [
    'Position_ID', 'Employee_ID', 'Active_Status', 'Worker_Company_ID',
    'CF-FormattedEffectiveDate', 'FYStartDate', 'FYEndDate',
    'CF-Ledger', 'Earning_Code', 'CF-WorktagDriverCode-Combo', 'CF-WorktagDriverCode',
    'CAllocation_StartDate', 'Distribution_Percent', 'Costing_Company_Reference_ID', 'Allocation_WID',
    'Updated_Date'
]

def parse_funding_actuals_xml(xml_path, file_modification_date):
    """
    Parses the Workday Position Funding Actuals XML file.
    """
    all_rows = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"Error: The file {xml_path} was not found.")
        return None
    except ET.ParseError as e:
        print(f"Error: The file {xml_path} could not be parsed. It might not be valid XML. Details: {e}")
        return None

    for report_entry in root.findall('wd:Report_Entry', NAMESPACE):
        worker_data = {}
        worker_element = report_entry.find('wd:Worker', NAMESPACE)
        if worker_element is not None:
            worker_data['Position_ID'] = worker_element.findtext('wd:Position_ID', default='', namespaces=NAMESPACE)
            worker_data['Employee_ID'] = worker_element.findtext('wd:Employee_ID', default='', namespaces=NAMESPACE)
            worker_data['Active_Status'] = worker_element.findtext('wd:Active_Status', default='', namespaces=NAMESPACE)
            worker_data['Worker_Company_ID'] = worker_element.findtext('wd:Company_ID', default='', namespaces=NAMESPACE) # From Worker/Company_ID
            worker_data['CF-FormattedEffectiveDate'] = worker_element.findtext('wd:CF-FormattedEffectiveDate', default='', namespaces=NAMESPACE)
            worker_data['FYStartDate'] = worker_element.findtext('wd:FYStartDate', default='', namespaces=NAMESPACE)
            worker_data['FYEndDate'] = worker_element.findtext('wd:FYEndDate', default='', namespaces=NAMESPACE)
        else: # Initialize with defaults if worker_element is not found
            for header_key in ['Position_ID', 'Employee_ID', 'Active_Status', 'Worker_Company_ID', 'CF-FormattedEffectiveDate', 'FYStartDate', 'FYEndDate']:
                worker_data[header_key] = ''
        
        worker_data['Updated_Date'] = file_modification_date

        allocation_details_elements = report_entry.findall('wd:AllocationDetails', NAMESPACE)
        if allocation_details_elements:
            for alloc_detail in allocation_details_elements:
                current_row_data = worker_data.copy() # Start with worker data

                current_row_data['CF-Ledger'] = alloc_detail.findtext('wd:CF-Ledger', default='', namespaces=NAMESPACE)
                
                earning_type_element = alloc_detail.find('wd:EarningType', NAMESPACE)
                if earning_type_element is not None:
                    current_row_data['Earning_Code'] = earning_type_element.findtext(".//wd:ID[@wd:type='Earning_Code']", default='', namespaces=NAMESPACE)
                else:
                    current_row_data['Earning_Code'] = ''
                
                current_row_data['CF-WorktagDriverCode-Combo'] = alloc_detail.findtext('wd:CF-WorktagDriverCode-Combo', default='', namespaces=NAMESPACE)
                current_row_data['CF-WorktagDriverCode'] = alloc_detail.findtext('wd:CF-WorktagDriverCode', default='', namespaces=NAMESPACE)
                current_row_data['CAllocation_StartDate'] = alloc_detail.findtext('wd:CAllocation_StartDate', default='', namespaces=NAMESPACE)
                current_row_data['Distribution_Percent'] = alloc_detail.findtext('wd:Distribution_Percent', default='', namespaces=NAMESPACE)
                
                costing_company_element = alloc_detail.find('wd:Costing_Company', NAMESPACE)
                if costing_company_element is not None:
                    current_row_data['Costing_Company_Reference_ID'] = costing_company_element.findtext(".//wd:ID[@wd:type='Company_Reference_ID']", default='', namespaces=NAMESPACE)
                else:
                    current_row_data['Costing_Company_Reference_ID'] = ''
                
                current_row_data['Allocation_WID'] = alloc_detail.findtext('wd:WID', default='', namespaces=NAMESPACE) # WID directly under AllocationDetails
                
                all_rows.append([current_row_data.get(header, '') for header in headers])
        else:
            # If there are no allocation details, write a row with worker data and empty allocation fields
            current_row_data = worker_data.copy()
            for header_key in ['CF-Ledger', 'Earning_Code', 'CF-WorktagDriverCode-Combo', 'CF-WorktagDriverCode', 'CAllocation_StartDate', 'Distribution_Percent', 'Costing_Company_Reference_ID', 'Allocation_WID']:
                current_row_data[header_key] = ''
            # Updated_Date is already in current_row_data from worker_data.copy()
            all_rows.append([current_row_data.get(header, '') for header in headers])
    return all_rows

def write_to_csv(data_rows, csv_path, column_headers):
    """Writes the list of rows to a CSV file."""
    if not data_rows and data_rows is not None: # Check if it's an empty list, but not None (which means parsing error)
        print("No data records to write to CSV, but headers will be written.")
    elif data_rows is None:
        print(f"Skipping CSV write due to parsing error. Empty/header-only CSV will be created if specified in main.")
        # To ensure an empty CSV with headers is created on error by main logic
        with open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(column_headers)
        return

    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(column_headers) # Write headers first
            if data_rows: # Only write data if it exists
                 # DEBUG: Print information about data_rows
                 print(f"DEBUG: Attempting to write {len(data_rows)} rows to CSV.")
                 if len(data_rows) > 0:
                     print(f"DEBUG: First data row content: {data_rows[0]}")
                 if len(data_rows) > 1:
                     print(f"DEBUG: Second data row content: {data_rows[1]}")
                 # END DEBUG
                 writer.writerows(data_rows)
        print(f"Data parsed successfully into {csv_path}")
    except IOError as e:
        print(f"Error writing to CSV {csv_path}: {e}")


if __name__ == '__main__':
    # Check for input file existence
    if not os.path.exists(xml_input_file):
        print(f"Error: The input XML file '{xml_input_file}' was not found.")
        print(f"Please ensure the file exists in the same directory as the script or provide an absolute path.")
        # Create an empty CSV with headers if XML is not found
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers)
        exit()
                
    # Get and format the file modification date
    try:
        timestamp = os.path.getmtime(xml_input_file)
        formatted_mod_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Warning: Could not retrieve or format modification date for {xml_input_file}. Error: {e}")
        formatted_mod_date = '' # Default to empty if there's an error
                
    print(f"Attempting to parse XML data from: {os.path.abspath(xml_input_file)}")
    print(f"Using file modification date: {formatted_mod_date if formatted_mod_date else 'N/A'}")
    parsed_rows = parse_funding_actuals_xml(xml_input_file, formatted_mod_date)

    # parse_funding_actuals_xml returns None on error, or a list (possibly empty) on success.
    if parsed_rows is not None: # Indicates parsing was attempted and didn't hit a major file/parse error
        if not parsed_rows:
            print("XML parsed successfully, but no <Report_Entry> items were found or processed.")
        else:
            print(f"Successfully processed {len(parsed_rows)} data rows.")
        # Write to CSV (will write headers even if parsed_rows is empty)
        write_to_csv(parsed_rows, csv_output_file, headers)
    else:
        # Error messages are printed within parse_funding_actuals_xml or for file not found.
        # write_to_csv handles creating an empty/header-only CSV if parsed_rows is None
        print(f"CSV file '{csv_output_file}' created with headers only, due to parsing errors or no input file.")
        # Ensure an empty CSV with headers is created if not already handled by write_to_csv for None case
        if not os.path.exists(csv_output_file):
             with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(headers)