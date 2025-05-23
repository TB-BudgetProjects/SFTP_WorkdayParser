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
xml_input_file_name = 'worktag_program.csv' # Original filename
csv_output_file_name = 'parsed_worktag_program.csv' # Original filename

xml_input_file = os.path.join(xml_dir, xml_input_file_name)
csv_output_file = os.path.join(csv_dir, csv_output_file_name)

# Create output directory if it doesn't exist
os.makedirs(csv_dir, exist_ok=True)

# Define namespace for the report
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

# Define the headers for the CSV file
headers = [
    'Code_Description', 'Cost_Center_Parent', 'Code', 'Program_Name',
    'Parent_Cost_Center_Descriptor', 'Parent_Cost_Center_WID', 'Parent_Cost_Center_Organization_Reference_ID', 'Parent_Cost_Center_Cost_Center_Reference_ID',
    'Included_in_Program_Hierarchies_Descriptor', 'Included_in_Program_Hierarchies_WID', 'Included_in_Program_Hierarchies_Program_Hierarchy_ID',
    'Unit_Descriptor', 'Unit_WID', 'Unit_Organization_Reference_ID', 'Unit_Custom_Organization_Reference_ID',
    'Fund_Descriptor', 'Fund_WID', 'Fund_Fund_ID',
    'Related_Function_for_Program_Descriptor', 'Related_Function_for_Program_WID', 'Related_Function_for_Program_Organization_Reference_ID', 'Related_Function_for_Program_Custom_Organization_Reference_ID',
    'Program_Manager_Descriptor', 'Program_Manager_WID', 'Program_Manager_Employee_ID',
    'Owner_Descriptor', 'Owner_WID', 'Owner_Employee_ID',
    'Inactive', 'Fund_Code', 'Function_Code', 'Unit_Code',
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
            # Initialize all headers to ensure consistent CSV output
            for header in headers:
                row_data[header] = ''
            row_data['Updated_Date'] = file_modification_date

            row_data['Code_Description'] = get_text(report_entry, 'wd:Code_Description')
            row_data['Cost_Center_Parent'] = get_text(report_entry, 'wd:Cost_Center_group/wd:Parent')
            row_data['Code'] = get_text(report_entry, 'wd:Code')
            row_data['Program_Name'] = get_text(report_entry, 'wd:Program_Name')

            pcc_el = report_entry.find('wd:Parent_Cost_Center', NAMESPACE)
            row_data['Parent_Cost_Center_Descriptor'] = get_attribute(pcc_el, '.', 'Descriptor')
            row_data['Parent_Cost_Center_WID'] = get_typed_id_text(pcc_el, '.', 'WID')
            row_data['Parent_Cost_Center_Organization_Reference_ID'] = get_typed_id_text(pcc_el, '.', 'Organization_Reference_ID')
            row_data['Parent_Cost_Center_Cost_Center_Reference_ID'] = get_typed_id_text(pcc_el, '.', 'Cost_Center_Reference_ID')

            iph_el = report_entry.find('wd:Included_in_Program_Hierarchies', NAMESPACE)
            row_data['Included_in_Program_Hierarchies_Descriptor'] = get_attribute(iph_el, '.', 'Descriptor')
            row_data['Included_in_Program_Hierarchies_WID'] = get_typed_id_text(iph_el, '.', 'WID')
            row_data['Included_in_Program_Hierarchies_Program_Hierarchy_ID'] = get_typed_id_text(iph_el, '.', 'Program_Hierarchy_ID')

            unit_el = report_entry.find('wd:Unit', NAMESPACE)
            row_data['Unit_Descriptor'] = get_attribute(unit_el, '.', 'Descriptor')
            row_data['Unit_WID'] = get_typed_id_text(unit_el, '.', 'WID')
            row_data['Unit_Organization_Reference_ID'] = get_typed_id_text(unit_el, '.', 'Organization_Reference_ID')
            row_data['Unit_Custom_Organization_Reference_ID'] = get_typed_id_text(unit_el, '.', 'Custom_Organization_Reference_ID')

            fund_el = report_entry.find('wd:Fund', NAMESPACE)
            row_data['Fund_Descriptor'] = get_attribute(fund_el, '.', 'Descriptor')
            row_data['Fund_WID'] = get_typed_id_text(fund_el, '.', 'WID')
            row_data['Fund_Fund_ID'] = get_typed_id_text(fund_el, '.', 'Fund_ID')
            
            rffp_el = report_entry.find('wd:Related_Function_for_Program', NAMESPACE)
            row_data['Related_Function_for_Program_Descriptor'] = get_attribute(rffp_el, '.', 'Descriptor')
            row_data['Related_Function_for_Program_WID'] = get_typed_id_text(rffp_el, '.', 'WID')
            row_data['Related_Function_for_Program_Organization_Reference_ID'] = get_typed_id_text(rffp_el, '.', 'Organization_Reference_ID')
            row_data['Related_Function_for_Program_Custom_Organization_Reference_ID'] = get_typed_id_text(rffp_el, '.', 'Custom_Organization_Reference_ID')

            pm_el = report_entry.find('wd:Program_Manager', NAMESPACE)
            row_data['Program_Manager_Descriptor'] = get_attribute(pm_el, '.', 'Descriptor')
            row_data['Program_Manager_WID'] = get_typed_id_text(pm_el, '.', 'WID')
            row_data['Program_Manager_Employee_ID'] = get_typed_id_text(pm_el, '.', 'Employee_ID')

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
        with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(headers)
        return None
    except ET.ParseError as e:
        print(f"Error: Could not parse XML from '{xml_path}'. Details: {e}")
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
        formatted_mod_date = ''

    print(f"Attempting to parse XML data from: {os.path.abspath(xml_input_file)}")
    print(f"Using file modification date: {formatted_mod_date if formatted_mod_date else 'N/A'}")
    all_rows_data = parse_xml_data(xml_input_file, formatted_mod_date)

    # Write the collected data to the CSV file
    if all_rows_data is not None:
        if all_rows_data:
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
        elif os.path.exists(xml_input_file):
            print(f"XML file '{xml_input_file}' was parsed, but no data records were extracted. CSV will contain headers only.")
            with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(headers)
    # If parse_xml_data returned None, it means an error occurred and an empty CSV with headers was already created.
    # No further action needed in that case.