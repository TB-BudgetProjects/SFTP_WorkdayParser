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
xml_input_file_name = 'worktag_grant.csv'  # Original filename
csv_output_file_name = 'parsed_worktag_grant.csv'  # Original filename

xml_input_file = os.path.join(xml_dir, xml_input_file_name)
csv_output_file = os.path.join(csv_dir, csv_output_file_name)

# Create output directory if it doesn't exist
os.makedirs(csv_dir, exist_ok=True)

# Define namespace for the report
# !!! IMPORTANT: Verify if this namespace is correct for worktag_grant.csv !!!
NAMESPACE = {'wd': 'urn:com.workday.report/intf-s111-c04'}

# Register namespace for ET to handle it correctly
ET.register_namespace('wd', NAMESPACE['wd'])

# Helper function to safely get text from an XML element
def get_text(element, path, default=''):
    if element is None: return default
    try:
        node = element.find(path, NAMESPACE)
        return node.text if node is not None and node.text is not None else default
    except AttributeError:
        return default

# Helper function to safely get an attribute from an XML element
def get_attribute(element, path, attribute_name, default=''):
    if element is None: return default
    try:
        target_element = element if path == '.' else element.find(path, NAMESPACE)
        if target_element is not None:
            attr_value = target_element.get(f"{{{NAMESPACE['wd']}}}{attribute_name}")
            return attr_value if attr_value is not None else default
        return default
    except AttributeError:
        return default

# Helper function to get text of a <wd:ID> element with a specific wd:type
def get_typed_id_text(element, path_to_parent_of_ids, id_type_value, default=''):
    if element is None: return default
    try:
        parent_of_ids = element.find(path_to_parent_of_ids, NAMESPACE)
        if parent_of_ids is not None:
            for id_elem in parent_of_ids.findall('wd:ID', NAMESPACE):
                if id_elem.get(f"{{{NAMESPACE['wd']}}}type") == id_type_value:
                    return id_elem.text if id_elem.text is not None else default
        return default
    except AttributeError:
        return default

# Define the headers for the CSV file based on worktag_grant.csv structure
headers = [
    'Code_Description_Descriptor', 'Code_Description_WID', 'Code_Description_Grant_ID',
    'Code',
    'Parent',
    'Grant_Description',
    'Grant_Cost_Center_Descriptor', 'Grant_Cost_Center_WID', 'Grant_Cost_Center_Organization_Reference_ID', 'Grant_Cost_Center_Cost_Center_Reference_ID',
    'Included_in_Grant_Hierarchies_Descriptor', 'Included_in_Grant_Hierarchies_WID', 'Included_in_Grant_Hierarchies_Grant_Hierarchy_ID',
    'Institution_Hierarchy_Node_Grants_Descriptor', 'Institution_Hierarchy_Node_Grants_WID', 'Institution_Hierarchy_Node_Grants_Grant_Hierarchy_ID',
    'Unit_Descriptor', 'Unit_WID', 'Unit_Organization_Reference_ID', 'Unit_Custom_Organization_Reference_ID',
    'Worktag_Fund_Descriptor', 'Worktag_Fund_WID', 'Worktag_Fund_ID',
    'Worktag_Function_Descriptor', 'Worktag_Function_WID', 'Worktag_Function_Organization_Reference_ID', 'Worktag_Function_Custom_Organization_Reference_ID',
    'Worktag_Unit_Descriptor', 'Worktag_Unit_WID', 'Worktag_Unit_Organization_Reference_ID', 'Worktag_Unit_Custom_Organization_Reference_ID',
    'Worktag_Cost_Center_Descriptor', 'Worktag_Cost_Center_WID', 'Worktag_Cost_Center_Organization_Reference_ID', 'Worktag_Cost_Center_Cost_Center_Reference_ID',
    'Grant_Manager_Descriptor', 'Grant_Manager_WID', 'Grant_Manager_Employee_ID',
    'Grant_Accountant_Descriptor', 'Grant_Accountant_WID', 'Grant_Accountant_Employee_ID',
    'Grant_Owner_Descriptor', 'Grant_Owner_WID', 'Grant_Owner_Employee_ID',
    'Has_Program', 'Has_Grant_Cost_Center', 'Has_Program_Cost_Center',
    'Company_Descriptor', 'Company_WID', 'Company_Organization_Reference_ID', 'Company_Company_Reference_ID',
    'Owner_Descriptor', 'Owner_WID', 'Owner_Employee_ID',
    'Inactive',
    'Fund_Code',
    'Function_Code',
    'Unit_Code',
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
            row_data = {}

            # Initialize all possible fields to empty strings to ensure consistent CSV columns
            for header in headers:
                row_data[header] = ''
            
            row_data['Updated_Date'] = file_modification_date

            # Code_Description
            cd_el = report_entry.find('wd:Code_Description', NAMESPACE)
            row_data['Code_Description_Descriptor'] = get_attribute(cd_el, '.', 'Descriptor')
            row_data['Code_Description_WID'] = get_typed_id_text(cd_el, '.', 'WID')
            row_data['Code_Description_Grant_ID'] = get_typed_id_text(cd_el, '.', 'Grant_ID')

            row_data['Code'] = get_text(report_entry, 'wd:Code')
            row_data['Parent'] = get_text(report_entry, 'wd:Parent')
            row_data['Grant_Description'] = get_text(report_entry, 'wd:Grant_Description')

            # Grant_Cost_Center
            gcc_el = report_entry.find('wd:Grant_Cost_Center', NAMESPACE)
            row_data['Grant_Cost_Center_Descriptor'] = get_attribute(gcc_el, '.', 'Descriptor')
            row_data['Grant_Cost_Center_WID'] = get_typed_id_text(gcc_el, '.', 'WID')
            row_data['Grant_Cost_Center_Organization_Reference_ID'] = get_typed_id_text(gcc_el, '.', 'Organization_Reference_ID')
            row_data['Grant_Cost_Center_Cost_Center_Reference_ID'] = get_typed_id_text(gcc_el, '.', 'Cost_Center_Reference_ID')

            # Included_in_Grant_Hierarchies
            iigh_el = report_entry.find('wd:Included_in_Grant_Hierarchies', NAMESPACE)
            row_data['Included_in_Grant_Hierarchies_Descriptor'] = get_attribute(iigh_el, '.', 'Descriptor')
            row_data['Included_in_Grant_Hierarchies_WID'] = get_typed_id_text(iigh_el, '.', 'WID')
            row_data['Included_in_Grant_Hierarchies_Grant_Hierarchy_ID'] = get_typed_id_text(iigh_el, '.', 'Grant_Hierarchy_ID')

            # Institution_Hierarchy_Node_-_Grants
            ihng_el = report_entry.find('wd:Institution_Hierarchy_Node_-_Grants', NAMESPACE)
            row_data['Institution_Hierarchy_Node_Grants_Descriptor'] = get_attribute(ihng_el, '.', 'Descriptor')
            row_data['Institution_Hierarchy_Node_Grants_WID'] = get_typed_id_text(ihng_el, '.', 'WID')
            row_data['Institution_Hierarchy_Node_Grants_Grant_Hierarchy_ID'] = get_typed_id_text(ihng_el, '.', 'Grant_Hierarchy_ID')

            # Unit (Top-level)
            unit_el = report_entry.find('wd:Unit', NAMESPACE)
            row_data['Unit_Descriptor'] = get_attribute(unit_el, '.', 'Descriptor')
            row_data['Unit_WID'] = get_typed_id_text(unit_el, '.', 'WID')
            row_data['Unit_Organization_Reference_ID'] = get_typed_id_text(unit_el, '.', 'Organization_Reference_ID')
            row_data['Unit_Custom_Organization_Reference_ID'] = get_typed_id_text(unit_el, '.', 'Custom_Organization_Reference_ID')

            # Worktags
            for worktag_el in report_entry.findall('wd:Worktags', NAMESPACE):
                descriptor = get_attribute(worktag_el, '.', 'Descriptor')
                if descriptor:
                    if descriptor.startswith('Fund:'):
                        row_data['Worktag_Fund_Descriptor'] = descriptor
                        row_data['Worktag_Fund_WID'] = get_typed_id_text(worktag_el, '.', 'WID')
                        row_data['Worktag_Fund_ID'] = get_typed_id_text(worktag_el, '.', 'Fund_ID')
                    elif descriptor.startswith('Function:'):
                        row_data['Worktag_Function_Descriptor'] = descriptor
                        row_data['Worktag_Function_WID'] = get_typed_id_text(worktag_el, '.', 'WID')
                        row_data['Worktag_Function_Organization_Reference_ID'] = get_typed_id_text(worktag_el, '.', 'Organization_Reference_ID')
                        row_data['Worktag_Function_Custom_Organization_Reference_ID'] = get_typed_id_text(worktag_el, '.', 'Custom_Organization_Reference_ID')
                    elif descriptor.startswith('Unit:'):
                        row_data['Worktag_Unit_Descriptor'] = descriptor
                        row_data['Worktag_Unit_WID'] = get_typed_id_text(worktag_el, '.', 'WID')
                        row_data['Worktag_Unit_Organization_Reference_ID'] = get_typed_id_text(worktag_el, '.', 'Organization_Reference_ID')
                        row_data['Worktag_Unit_Custom_Organization_Reference_ID'] = get_typed_id_text(worktag_el, '.', 'Custom_Organization_Reference_ID')
                    elif descriptor.startswith('Cost Center:'):
                        row_data['Worktag_Cost_Center_Descriptor'] = descriptor
                        row_data['Worktag_Cost_Center_WID'] = get_typed_id_text(worktag_el, '.', 'WID')
                        row_data['Worktag_Cost_Center_Organization_Reference_ID'] = get_typed_id_text(worktag_el, '.', 'Organization_Reference_ID')
                        row_data['Worktag_Cost_Center_Cost_Center_Reference_ID'] = get_typed_id_text(worktag_el, '.', 'Cost_Center_Reference_ID')

            # Grant_Manager
            gm_el = report_entry.find('wd:Grant_Manager', NAMESPACE)
            row_data['Grant_Manager_Descriptor'] = get_attribute(gm_el, '.', 'Descriptor')
            row_data['Grant_Manager_WID'] = get_typed_id_text(gm_el, '.', 'WID')
            row_data['Grant_Manager_Employee_ID'] = get_typed_id_text(gm_el, '.', 'Employee_ID')

            # Grant_Accountant
            ga_el = report_entry.find('wd:Grant_Accountant', NAMESPACE)
            row_data['Grant_Accountant_Descriptor'] = get_attribute(ga_el, '.', 'Descriptor')
            row_data['Grant_Accountant_WID'] = get_typed_id_text(ga_el, '.', 'WID')
            row_data['Grant_Accountant_Employee_ID'] = get_typed_id_text(ga_el, '.', 'Employee_ID')

            # Grant_Owner
            go_el = report_entry.find('wd:Grant_Owner', NAMESPACE)
            row_data['Grant_Owner_Descriptor'] = get_attribute(go_el, '.', 'Descriptor')
            row_data['Grant_Owner_WID'] = get_typed_id_text(go_el, '.', 'WID')
            row_data['Grant_Owner_Employee_ID'] = get_typed_id_text(go_el, '.', 'Employee_ID')

            row_data['Has_Program'] = get_text(report_entry, 'wd:Has_Program')
            row_data['Has_Grant_Cost_Center'] = get_text(report_entry, 'wd:Has_Grant_Cost_Center')
            row_data['Has_Program_Cost_Center'] = get_text(report_entry, 'wd:Has_Program_Cost_Center')

            # Company
            comp_el = report_entry.find('wd:Company', NAMESPACE)
            row_data['Company_Descriptor'] = get_attribute(comp_el, '.', 'Descriptor')
            row_data['Company_WID'] = get_typed_id_text(comp_el, '.', 'WID')
            row_data['Company_Organization_Reference_ID'] = get_typed_id_text(comp_el, '.', 'Organization_Reference_ID')
            row_data['Company_Company_Reference_ID'] = get_typed_id_text(comp_el, '.', 'Company_Reference_ID')

            # Owner (General)
            owner_el = report_entry.find('wd:Owner', NAMESPACE)
            row_data['Owner_Descriptor'] = get_attribute(owner_el, '.', 'Descriptor')
            row_data['Owner_WID'] = get_typed_id_text(owner_el, '.', 'WID')
            row_data['Owner_Employee_ID'] = get_typed_id_text(owner_el, '.', 'Employee_ID')

            row_data['Inactive'] = get_text(report_entry, 'wd:Inactive')
            row_data['Fund_Code'] = get_text(report_entry, 'wd:Fund_group/wd:Fund_Code')
            row_data['Function_Code'] = get_text(report_entry, 'wd:Function_group/wd:Function_Code')
            row_data['Unit_Code'] = get_text(report_entry, 'wd:Unit_group/wd:Unit_Code')
            
            all_rows_data.append(row_data)
        
        return all_rows_data

    except FileNotFoundError:
        print(f"Error: The input XML file '{xml_path}' was not found.")
        # Create CSV with headers only if XML is not found
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers)
        return None
    except ET.ParseError as e:
        print(f"Error: Could not parse XML from '{xml_path}'. Details: {e}")
        # Create CSV with headers only if XML parsing fails
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers)
        return None

# Main script execution
if __name__ == '__main__':
    if not os.path.exists(xml_input_file):
        print(f"Error: The input XML file '{xml_input_file}' was not found.")
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
    all_rows_data = parse_xml_data(xml_input_file, formatted_mod_date)

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
        # If XML was parsed but no data was found, still create CSV with headers
        elif os.path.exists(xml_input_file): 
            print(f"XML file '{xml_input_file}' was parsed, but no data records were extracted. CSV will contain headers only.")
            with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(headers)
    # If parse_xml_data returned None, it means an error occurred and an empty CSV with headers was already created.
    # No further action needed in that case.