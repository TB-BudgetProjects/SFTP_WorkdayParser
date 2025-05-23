import xml.etree.ElementTree as ET
import csv
import os
import configparser
from datetime import datetime

# Initialize config parser and read config file
config = configparser.ConfigParser()
# Assume config.ini is in the parent directory of 'Parsing Scripts'
# Correctly define config_file_path relative to the script's location to find config.ini in the parent
script_dir = os.path.dirname(__file__)
config_file_path = os.path.join(script_dir, '..', 'config.ini')
config.read(config_file_path)

# Get base paths from config, ensuring they are absolute or correctly relative to config.ini's location
config_base_dir = os.path.dirname(os.path.abspath(config_file_path))
xml_dir = os.path.join(config_base_dir, config['Paths']['workday_xml_downloads'])
csv_dir = os.path.join(config_base_dir, config['Paths']['parsed_csvs'])

# Define the input XML file (misnamed as .csv) and output CSV file using resolved paths
xml_input_file_name = 'position_compensation.csv' # Original filename
csv_output_file_name = 'parsed_position_compensation.csv' # Original filename

xml_input_file = os.path.join(xml_dir, xml_input_file_name)
csv_output_file = os.path.join(csv_dir, csv_output_file_name)

# Create output directory if it doesn't exist
os.makedirs(csv_dir, exist_ok=True)

# Define namespace for the Position Other Compensation report
NAMESPACE = {'wd': 'urn:com.workday.report/RPT-INTF-S111-CSN-PositionOtherCompensation'}

# Register namespace for ET to handle it correctly, especially for .find() and .findall()
ET.register_namespace('wd', NAMESPACE['wd'])

# Helper function to safely get text from an XML element
def get_text(element, path, default=''):
    try:
        return element.find(path, NAMESPACE).text
    except AttributeError:
        return default

# Helper function to safely get an attribute from an XML element
def get_attribute(element, path, attribute_name, default=''):
    try:
        target_element = element if path == '.' else element.find(path, NAMESPACE)
        if target_element is not None:
            # Construct the attribute key in the format {namespace}name if it's a namespaced attribute
            # For wd:Descriptor, it would be f"{{{NAMESPACE['wd']}}}Descriptor"
            # However, common attributes like 'wd:type' are often directly accessible if the namespace is registered globally
            # For simplicity, assuming direct access after global registration or non-namespaced attributes for now.
            # If wd:Descriptor fails, this will need adjustment to f"{{{NAMESPACE['wd']}}}{attribute_name}"
            attr_value = target_element.get(f"{{{NAMESPACE['wd']}}}{attribute_name}")
            return attr_value if attr_value is not None else default
        return default
    except AttributeError:
        return default

# Helper function to get text of a <wd:ID> element with a specific wd:type
def get_typed_id_text(element, path_to_parent_of_ids, id_type_value, default=''):
    try:
        parent_of_ids = element.find(path_to_parent_of_ids, NAMESPACE)
        if parent_of_ids is not None:
            for id_elem in parent_of_ids.findall('wd:ID', NAMESPACE):
                if id_elem.get(f"{{{NAMESPACE['wd']}}}type") == id_type_value:
                    return id_elem.text if id_elem.text is not None else default
        return default
    except AttributeError:
        return default

# Define the headers for the CSV file
headers = [
    'Position_ID', 'Employee_ID',
    'Job_Family_Group_Descriptor', 'Job_Family_Group_WID', 'Job_Family_Group_Job_Family_ID',
    'CF_Staffing_Status_Descriptor', 'CF_Staffing_Status_WID', 'CF_Staffing_Status_Staffing_Interface_Status_for_CRF_ID',
    'CF_JobCode', 'Terminated_based_on_report_date',
    'Compensation_Element_Descriptor', 'Compensation_Element_WID', 'Compensation_Element_Compensation_Element_ID',
    'Annualized_Amount',
    'Updated_Date'
]

def parse_xml_data(xml_path, file_modification_date):
    """Parses the XML data and returns a list of rows.
    Returns None if there is a FileNotFoundError or ET.ParseError.
    """
    all_rows_data = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for report_entry in root.findall('wd:Report_Entry', NAMESPACE):
            worker_group_data = {}
            worker_group_element = report_entry.find('wd:Worker_group', NAMESPACE)
            
            if worker_group_element is not None:
                worker_group_data['Position_ID'] = get_text(worker_group_element, 'wd:Position_ID')
                worker_group_data['Employee_ID'] = get_text(worker_group_element, 'wd:Employee_ID')
                
                job_family_group_el = worker_group_element.find('wd:Job_Family_Group', NAMESPACE)
                if job_family_group_el is not None:
                    worker_group_data['Job_Family_Group_Descriptor'] = get_attribute(job_family_group_el, '.', 'Descriptor')
                    worker_group_data['Job_Family_Group_WID'] = get_typed_id_text(job_family_group_el, '.', 'WID')
                    worker_group_data['Job_Family_Group_Job_Family_ID'] = get_typed_id_text(job_family_group_el, '.', 'Job_Family_ID')
                
                cf_staffing_status_el = worker_group_element.find('wd:CF-Staffing_Status', NAMESPACE)
                if cf_staffing_status_el is not None:
                    worker_group_data['CF_Staffing_Status_Descriptor'] = get_attribute(cf_staffing_status_el, '.', 'Descriptor')
                    worker_group_data['CF_Staffing_Status_WID'] = get_typed_id_text(cf_staffing_status_el, '.', 'WID')
                    worker_group_data['CF_Staffing_Status_Staffing_Interface_Status_for_CRF_ID'] = get_typed_id_text(cf_staffing_status_el, '.', 'Staffing_Interface_Status_for_CRF_ID')

                worker_group_data['CF_JobCode'] = get_text(worker_group_element, 'wd:CF-JobCode')
                worker_group_data['Terminated_based_on_report_date'] = get_text(worker_group_element, 'wd:Terminated__based_on_report_date_')
            
            worker_group_data['Updated_Date'] = file_modification_date

            # Iterate through each Compensation_Plan_Assignments for the current Worker_group
            comp_assignments_found = False
            for comp_assignment_el in report_entry.findall('wd:Compensation_Plan_Assignments', NAMESPACE):
                comp_assignments_found = True
                current_row = worker_group_data.copy() # Start with common worker_group data
                
                comp_element_el = comp_assignment_el.find('wd:Compensation_Element', NAMESPACE)
                if comp_element_el is not None:
                    current_row['Compensation_Element_Descriptor'] = get_attribute(comp_element_el, '.', 'Descriptor')
                    current_row['Compensation_Element_WID'] = get_typed_id_text(comp_element_el, '.', 'WID')
                    current_row['Compensation_Element_Compensation_Element_ID'] = get_typed_id_text(comp_element_el, '.', 'Compensation_Element_ID')
                
                current_row['Annualized_Amount'] = get_text(comp_assignment_el, 'wd:Annualized_Amount')
                
                all_rows_data.append(current_row)
            
            # If a Worker_group exists but has no Compensation_Plan_Assignments, add it with empty comp fields
            if worker_group_element is not None and not comp_assignments_found:
                empty_comp_row = worker_group_data.copy()
                for header in headers:
                    if header not in empty_comp_row: # Add placeholders for comp-specific fields
                        empty_comp_row[header] = ''
                # Updated_Date is already in empty_comp_row
                all_rows_data.append(empty_comp_row)
        return all_rows_data

    except FileNotFoundError:
        print(f"Error: The input XML file '{xml_path}' was not found.")
        # Create empty CSV with headers if XML is not found
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers) # headers now includes Updated_Date
        return None # Indicate error
    except ET.ParseError as e:
        print(f"Error: Could not parse XML from '{xml_path}'. Details: {e}")
        # Create empty CSV with headers if XML is not parseable
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers) # headers now includes Updated_Date
        return None # Indicate error

# Main script execution
if __name__ == '__main__':
    if not os.path.exists(xml_input_file):
        print(f"Error: The input XML file '{xml_input_file}' was not found.")
        # Ensure headers (including Updated_Date) are written if file doesn't exist
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
    all_rows_data = parse_xml_data(xml_input_file, formatted_mod_date) # Call the parsing function

    # Write the collected data to the CSV file
    if all_rows_data is not None: # Check if parsing was successful (not None)
        if all_rows_data: # Check if list is not empty
            try:
                with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=headers)
                    writer.writeheader()
                    for data_row in all_rows_data:
                        # Ensure all headers are present in the row, with defaults if missing
                        row_to_write = {header: data_row.get(header, '') for header in headers}
                        writer.writerow(row_to_write)
                print(f"Data successfully parsed into '{csv_output_file}'")
            except IOError as e:
                print(f"Error writing to CSV file '{csv_output_file}'. Details: {e}")
        elif os.path.exists(xml_input_file): # Input file existed but no data was parsed
            print(f"XML file '{xml_input_file}' was parsed, but no data records were extracted. CSV will contain headers only.")
            # Ensure CSV with headers (including Updated_Date) is created
            with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(headers)
    # If parse_xml_data returned None, it means an error occurred and an empty CSV with headers was already created.
    # No further action needed in that case.