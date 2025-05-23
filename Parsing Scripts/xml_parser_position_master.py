import xml.etree.ElementTree as ET
import json
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
xml_input_file_name = 'position_master.csv' # Original filename
csv_output_file_name = 'parsed_position_master.csv' # Original filename

xml_input_file = os.path.join(xml_dir, xml_input_file_name)
csv_output_file = os.path.join(csv_dir, csv_output_file_name)

# Create output directory if it doesn't exist
os.makedirs(csv_dir, exist_ok=True)

# Define namespace for the report - Reverted to original
NAMESPACE = {'wd': 'urn:com.workday.report/RPT-INTF-S111-(NSHE)_CSN-PositionMaster'}

# --- Helper Functions ---
def get_text(element, path, ns, default=None):
    """Safely get text from an XML element."""
    try:
        return element.find(path, ns).text
    except AttributeError:
        return default

def get_attribute(element, path, attribute_qname, ns, default=None):
    """Safely get an attribute from an XML element."""
    try:
        return element.find(path, ns).get(attribute_qname)
    except AttributeError:
        return default

def get_typed_id_text(element, path_to_parent_of_ids, id_type_value, ns, default=None):
    """
    Safely gets the text of a <wd:ID> element that has a specific wd:type attribute.
    """
    try:
        parent_of_ids = element.find(path_to_parent_of_ids, ns)
        if parent_of_ids is not None:
            for id_elem in parent_of_ids.findall('wd:ID', ns):
                if id_elem.get(f"{{{NAMESPACE['wd']}}}type") == id_type_value:
                    if id_elem.text:
                        return id_elem.text
        return default
    except AttributeError:
        return default

def get_multiple_typed_id_texts_from_parent(parent_element, id_type_value, ns):
    """
    Safely gets the text of all <wd:ID> child elements of a given parent_element
    that have a specific wd:type attribute. Returns a list of texts.
    """
    texts = []
    if parent_element is not None:
        for id_elem in parent_element.findall('wd:ID', ns):
            if id_elem.get(f"{{{NAMESPACE['wd']}}}type") == id_type_value:
                if id_elem.text:
                    texts.append(id_elem.text)
    return texts if texts else [None] # Return list with None if no matching IDs found

def get_all_field_names():
    """
    Returns a predefined list of all possible field names based on the analysis.
    This ensures that every record dictionary has the same set of keys.
    """
    return [
        'Unit_Descriptor', 'Unit_ID_WID', 'Unit_ID_Organization_Reference_ID', 'Unit_ID_Custom_Organization_Reference_ID',
        'PositionManagement_Position_ID', 'PositionManagement_Job_Code', 'PositionManagement_Position_Title',
        'PositionManagement_Open_Position_Title', 'PositionManagement_FTE',
        'PositionManagement_CF_Worker_Comp_Step_Descriptor', 'PositionManagement_CF_Worker_Comp_Step_ID_WID',
        'PositionManagement_CF_Worker_Comp_Step_ID_Compensation_Step_ID', 'PositionManagement_CF_CompGradeRefID',
        'PositionManagement_Staffing_Status_Descriptor', 'PositionManagement_Staffing_Status_ID_WID',
        'PositionManagement_Staffing_Status_ID_Staffing_Interface_Status_for_CRF_ID',
        'EmployeeID', 'Cost_Center_Descriptor', 'Cost_Center_ID_WID', 'Cost_Center_ID_Organization_Reference_ID',
        'Cost_Center_ID_Cost_Center_Reference_ID', 'CF_CostCenterID',
        'Worker_Is_Classified', 'Worker_Last_Name', 'Worker_First_Name', 'Worker_Work_Email', 'Worker_BusinessTitle',
        'Worker_CF_TenureStatus', 'Worker_Worker_Compensation_Grade_Descriptor',
        'Worker_Worker_Compensation_Grade_ID_WID', 'Worker_Worker_Compensation_Grade_ID_Compensation_Grade_ID',
        'Worker_CF_Worker_Comp_Grade_WID', 'Worker_Worker_Compensation_Grade_Profile_Descriptor',
        'Worker_Worker_Compensation_Grade_Profile_ID_WID', 'Worker_Worker_Compensation_Grade_Profile_ID_Compensation_Grade_Profile_ID',
        'Worker_CF_Worker_Comp_Grade_Prof_WID', 'Worker_SeniorityDate', 'Worker_OriginalHireDate',
        'Worker_ContinuousServiceDate', 'Worker_Eff_Date_CurrentPosition', 'Worker_LastPayIncreaseDate',
        'Worker_Position_Worker_Type_Descriptor', 'Worker_Position_Worker_Type_ID_WID',
        'Worker_Position_Worker_Type_ID_Employee_Type_ID', 'Worker_Medicare_Flag',
        'Eligibility_Rules_Descriptor', 'Eligibility_Rules_ID_WID',
        'Default_Compensation_Grade_group_Compensation_Grade_Descriptor',
        'Default_Compensation_Grade_group_Compensation_Grade_ID_WID',
        'Default_Compensation_Grade_group_Compensation_Grade_ID_Compensation_Grade_ID',
        'Default_Compensation_Grade_group_WID', 'Default_Compensation_Grade_group_Profiles_Serialized',
        'Default_Compensation_Grade_Profile_group_CF_CompGradeProf_WID',
        'PositionJob_Job_Family_Group_Descriptor', 'PositionJob_Job_Family_Group_ID_WID',
        'PositionJob_Job_Family_Group_ID_Job_Family_ID', 'PositionJob_CF_IsWorkerEmpty',
        'PositionJob_CF_Step', 'PositionJob_CF_MeritStep', 'PositionJob_CF_MeritDate',
        'PositionRestrictions_RetirementCodeOld', 'PositionRestrictions_Health_Insurance_Yr1_Flag',
        'PositionRestrictions_Health_Insurance_Yr2_Flag', 'PositionRestrictions_Partial_Flag',
        'PositionRestrictions_Retirement_Flag', 'PositionRestrictions_Workers_Comp_Flag',
        'PositionRestrictions_Personnel_Assessment_Flag', 'PositionRestrictions_Unemployment_Flag',
        'PositionRestrictions_GroupInsFlag', 'PositionRestrictions_Medicare_Flag_OLD',
        'PositionRestrictions_FICA_Flag', 'PositionRestrictions_AG_Tort_Flag',
        'PositionRestrictions_Employee_Bond_Flag', 'PositionRestrictions_Merit_Increase_Flag',
        'Retirement_Savings_Election_group_RetirementCode_Descriptor',
        'Retirement_Savings_Election_group_RetirementCode_ID_WID',
        'Retirement_Savings_Election_group_RetirementCode_ID_Defined_Contribution_Plan_ID',
        'Retirement_Savings_Election_group_RetirementCode_ID_Benefit_Plan_ID',
        'Retirement_Savings_Election_group_Employer_Contribution_Percentage',
        'Retirement_Savings_Election_group_Elected',
        'Updated_Date'
    ]

def parse_workday_xml(xml_file_path, file_modification_date):
    """
    Parses the Workday XML file and returns a list of dictionaries,
    where each dictionary represents a flattened Report_Entry.
    """
    all_records = []
    field_names = get_all_field_names() # Get the master list of field names

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for report_entry in root.findall('wd:Report_Entry', NAMESPACE):
            record = {name: None for name in field_names} # Initialize record with all possible keys
            record['Updated_Date'] = file_modification_date # Add modification date

            # --- Unit ---
            unit_element = report_entry.find('wd:Unit', NAMESPACE)
            if unit_element is not None:
                record['Unit_Descriptor'] = unit_element.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                record['Unit_ID_WID'] = get_typed_id_text(unit_element, '.', 'WID', NAMESPACE)
                record['Unit_ID_Organization_Reference_ID'] = get_typed_id_text(unit_element, '.', 'Organization_Reference_ID', NAMESPACE)
                record['Unit_ID_Custom_Organization_Reference_ID'] = get_typed_id_text(unit_element, '.', 'Custom_Organization_Reference_ID', NAMESPACE)

            # --- PositionManagement ---
            pm_element = report_entry.find('wd:PositionManagement', NAMESPACE)
            if pm_element is not None:
                record['PositionManagement_Position_ID'] = get_text(pm_element, 'wd:Position_ID', NAMESPACE)
                record['PositionManagement_Job_Code'] = get_text(pm_element, 'wd:Job_Code', NAMESPACE)
                record['PositionManagement_Position_Title'] = get_text(pm_element, 'wd:Position_Title', NAMESPACE)
                record['PositionManagement_Open_Position_Title'] = get_text(pm_element, 'wd:Open_Position_Title', NAMESPACE)
                record['PositionManagement_FTE'] = get_text(pm_element, 'wd:FTE', NAMESPACE)
                record['PositionManagement_CF_CompGradeRefID'] = get_text(pm_element, 'wd:CF-CompGradeRefID', NAMESPACE)

                cf_worker_comp_step = pm_element.find('wd:CF-Worker_Comp_Step', NAMESPACE)
                if cf_worker_comp_step is not None:
                    record['PositionManagement_CF_Worker_Comp_Step_Descriptor'] = cf_worker_comp_step.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['PositionManagement_CF_Worker_Comp_Step_ID_WID'] = get_typed_id_text(cf_worker_comp_step, '.', 'WID', NAMESPACE)
                    record['PositionManagement_CF_Worker_Comp_Step_ID_Compensation_Step_ID'] = get_typed_id_text(cf_worker_comp_step, '.', 'Compensation_Step_ID', NAMESPACE)
                
                staffing_status = pm_element.find('wd:Staffing_Status', NAMESPACE)
                if staffing_status is not None:
                    record['PositionManagement_Staffing_Status_Descriptor'] = staffing_status.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['PositionManagement_Staffing_Status_ID_WID'] = get_typed_id_text(staffing_status, '.', 'WID', NAMESPACE)
                    record['PositionManagement_Staffing_Status_ID_Staffing_Interface_Status_for_CRF_ID'] = get_typed_id_text(staffing_status, '.', 'Staffing_Interface_Status_for_CRF_ID', NAMESPACE)

            # --- EmployeeID ---
            record['EmployeeID'] = get_text(report_entry, 'wd:EmployeeID', NAMESPACE)

            # --- Cost_Center ---
            cc_element = report_entry.find('wd:Cost_Center', NAMESPACE)
            if cc_element is not None:
                record['Cost_Center_Descriptor'] = cc_element.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                record['Cost_Center_ID_WID'] = get_typed_id_text(cc_element, '.', 'WID', NAMESPACE)
                record['Cost_Center_ID_Organization_Reference_ID'] = get_typed_id_text(cc_element, '.', 'Organization_Reference_ID', NAMESPACE)
                record['Cost_Center_ID_Cost_Center_Reference_ID'] = get_typed_id_text(cc_element, '.', 'Cost_Center_Reference_ID', NAMESPACE)
            
            record['CF_CostCenterID'] = get_text(report_entry, 'wd:CF-CostCenterID', NAMESPACE)


            # --- Worker ---
            worker_element = report_entry.find('wd:Worker', NAMESPACE)
            if worker_element is not None:
                record['Worker_Is_Classified'] = get_text(worker_element, 'wd:Is_Classified', NAMESPACE)
                record['Worker_Last_Name'] = get_text(worker_element, 'wd:Last_Name', NAMESPACE)
                record['Worker_First_Name'] = get_text(worker_element, 'wd:First_Name', NAMESPACE)
                record['Worker_Work_Email'] = get_text(worker_element, 'wd:Work_Email', NAMESPACE)
                record['Worker_BusinessTitle'] = get_text(worker_element, 'wd:BusinessTitle', NAMESPACE)
                record['Worker_CF_TenureStatus'] = get_text(worker_element, 'wd:CF-TenureStatus', NAMESPACE)
                record['Worker_SeniorityDate'] = get_text(worker_element, 'wd:SeniorityDate', NAMESPACE)
                record['Worker_OriginalHireDate'] = get_text(worker_element, 'wd:OriginalHireDate', NAMESPACE)
                record['Worker_ContinuousServiceDate'] = get_text(worker_element, 'wd:ContinuousServiceDate', NAMESPACE)
                record['Worker_Eff_Date_CurrentPosition'] = get_text(worker_element, 'wd:Eff_Date_CurrentPosition', NAMESPACE)
                record['Worker_LastPayIncreaseDate'] = get_text(worker_element, 'wd:LastPayIncreaseDate', NAMESPACE)
                record['Worker_Medicare_Flag'] = get_text(worker_element, 'wd:Medicare_Flag', NAMESPACE)
                record['Worker_CF_Worker_Comp_Grade_WID'] = get_text(worker_element, 'wd:CF_-_Worker_Comp_Grade_WID', NAMESPACE) # Note the underscore in XML tag
                record['Worker_CF_Worker_Comp_Grade_Prof_WID'] = get_text(worker_element, 'wd:CF_-_Worker_Comp_Grade_Prof_WID', NAMESPACE) # Note the underscore

                wcg_element = worker_element.find('wd:Worker_Compensation_Grade', NAMESPACE)
                if wcg_element is not None:
                    record['Worker_Worker_Compensation_Grade_Descriptor'] = wcg_element.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['Worker_Worker_Compensation_Grade_ID_WID'] = get_typed_id_text(wcg_element, '.', 'WID', NAMESPACE)
                    record['Worker_Worker_Compensation_Grade_ID_Compensation_Grade_ID'] = get_typed_id_text(wcg_element, '.', 'Compensation_Grade_ID', NAMESPACE)

                wcgp_element = worker_element.find('wd:Worker_Compensation_Grade_Profile', NAMESPACE)
                if wcgp_element is not None:
                    record['Worker_Worker_Compensation_Grade_Profile_Descriptor'] = wcgp_element.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['Worker_Worker_Compensation_Grade_Profile_ID_WID'] = get_typed_id_text(wcgp_element, '.', 'WID', NAMESPACE)
                    record['Worker_Worker_Compensation_Grade_Profile_ID_Compensation_Grade_Profile_ID'] = get_typed_id_text(wcgp_element, '.', 'Compensation_Grade_Profile_ID', NAMESPACE)

                pwt_element = worker_element.find('wd:Position_Worker_Type', NAMESPACE)
                if pwt_element is not None:
                    record['Worker_Position_Worker_Type_Descriptor'] = pwt_element.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['Worker_Position_Worker_Type_ID_WID'] = get_typed_id_text(pwt_element, '.', 'WID', NAMESPACE)
                    record['Worker_Position_Worker_Type_ID_Employee_Type_ID'] = get_typed_id_text(pwt_element, '.', 'Employee_Type_ID', NAMESPACE)
            
            # --- Eligibility_Rules ---
            er_element = report_entry.find('wd:Eligibility_Rules', NAMESPACE)
            if er_element is not None:
                record['Eligibility_Rules_Descriptor'] = er_element.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                record['Eligibility_Rules_ID_WID'] = get_typed_id_text(er_element, '.', 'WID', NAMESPACE)

            # --- Default_Compensation_Grade_group ---
            dcg_group_element = report_entry.find('wd:Default_Compensation_Grade_group', NAMESPACE)
            if dcg_group_element is not None:
                record['Default_Compensation_Grade_group_WID'] = get_text(dcg_group_element, 'wd:WID', NAMESPACE)
                
                comp_grade_elem = dcg_group_element.find('wd:Compensation_Grade', NAMESPACE)
                if comp_grade_elem is not None:
                    record['Default_Compensation_Grade_group_Compensation_Grade_Descriptor'] = comp_grade_elem.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['Default_Compensation_Grade_group_Compensation_Grade_ID_WID'] = get_typed_id_text(comp_grade_elem, '.', 'WID', NAMESPACE)
                    record['Default_Compensation_Grade_group_Compensation_Grade_ID_Compensation_Grade_ID'] = get_typed_id_text(comp_grade_elem, '.', 'Compensation_Grade_ID', NAMESPACE)

                profiles = []
                for profile_elem in dcg_group_element.findall('wd:Compensation_Grade_Profiles', NAMESPACE):
                    profile_data = {
                        'Descriptor': profile_elem.get(f"{{{NAMESPACE['wd']}}}Descriptor"),
                        'ID_WID': get_typed_id_text(profile_elem, '.', 'WID', NAMESPACE),
                        'ID_Compensation_Grade_Profile_ID': get_typed_id_text(profile_elem, '.', 'Compensation_Grade_Profile_ID', NAMESPACE)
                    }
                    profiles.append(profile_data)
                if profiles:
                    record['Default_Compensation_Grade_group_Profiles_Serialized'] = json.dumps(profiles)
            
            # --- Default_Compensation_Grade_Profile_group ---
            dcgp_group_element = report_entry.find('wd:Default_Compensation_Grade_Profile_group', NAMESPACE)
            if dcgp_group_element is not None:
                record['Default_Compensation_Grade_Profile_group_CF_CompGradeProf_WID'] = get_text(dcgp_group_element, 'wd:CF-CompGradeProf-WID', NAMESPACE)

            # --- PositionJob ---
            pj_element = report_entry.find('wd:PositionJob', NAMESPACE)
            if pj_element is not None:
                record['PositionJob_CF_IsWorkerEmpty'] = get_text(pj_element, 'wd:CF-IsWorkerEmpty', NAMESPACE)
                record['PositionJob_CF_Step'] = get_text(pj_element, 'wd:CF-Step', NAMESPACE)
                record['PositionJob_CF_MeritStep'] = get_text(pj_element, 'wd:CF-MeritStep', NAMESPACE)
                record['PositionJob_CF_MeritDate'] = get_text(pj_element, 'wd:CF-MeritDate', NAMESPACE)
                
                job_family_group = pj_element.find('wd:Job_Family_Group', NAMESPACE)
                if job_family_group is not None:
                    record['PositionJob_Job_Family_Group_Descriptor'] = job_family_group.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['PositionJob_Job_Family_Group_ID_WID'] = get_typed_id_text(job_family_group, '.', 'WID', NAMESPACE)
                    record['PositionJob_Job_Family_Group_ID_Job_Family_ID'] = get_typed_id_text(job_family_group, '.', 'Job_Family_ID', NAMESPACE)

            # --- PositionRestrictions ---
            pr_element = report_entry.find('wd:PositionRestrictions', NAMESPACE)
            if pr_element is not None:
                record['PositionRestrictions_RetirementCodeOld'] = get_text(pr_element, 'wd:RetirementCodeOld', NAMESPACE)
                record['PositionRestrictions_Health_Insurance_Yr1_Flag'] = get_text(pr_element, 'wd:Health_Insurance_Yr1_Flag', NAMESPACE)
                record['PositionRestrictions_Health_Insurance_Yr2_Flag'] = get_text(pr_element, 'wd:Health_Insurance_Yr2_Flag', NAMESPACE)
                record['PositionRestrictions_Partial_Flag'] = get_text(pr_element, 'wd:Partial_Flag', NAMESPACE)
                record['PositionRestrictions_Retirement_Flag'] = get_text(pr_element, 'wd:Retirement_Flag', NAMESPACE)
                record['PositionRestrictions_Workers_Comp_Flag'] = get_text(pr_element, 'wd:Workers_Comp_Flag', NAMESPACE)
                record['PositionRestrictions_Personnel_Assessment_Flag'] = get_text(pr_element, 'wd:Personnel_Assessment_Flag', NAMESPACE)
                record['PositionRestrictions_Unemployment_Flag'] = get_text(pr_element, 'wd:Unemployment_Flag', NAMESPACE)
                record['PositionRestrictions_GroupInsFlag'] = get_text(pr_element, 'wd:GroupInsFlag', NAMESPACE)
                record['PositionRestrictions_Medicare_Flag_OLD'] = get_text(pr_element, 'wd:Medicare_Flag-OLD', NAMESPACE) # XML tag has hyphen
                record['PositionRestrictions_FICA_Flag'] = get_text(pr_element, 'wd:FICA_Flag', NAMESPACE)
                record['PositionRestrictions_AG_Tort_Flag'] = get_text(pr_element, 'wd:AG_Tort_Flag', NAMESPACE)
                record['PositionRestrictions_Employee_Bond_Flag'] = get_text(pr_element, 'wd:Employee_Bond_Flag', NAMESPACE)
                record['PositionRestrictions_Merit_Increase_Flag'] = get_text(pr_element, 'wd:Merit_Increase_Flag', NAMESPACE)

            # --- Retirement_Savings_Election_group ---
            rse_group_element = report_entry.find('wd:Retirement_Savings_Election_group', NAMESPACE)
            if rse_group_element is not None:
                record['Retirement_Savings_Election_group_Employer_Contribution_Percentage'] = get_text(rse_group_element, 'wd:Employer_Contribution_Percentage', NAMESPACE)
                record['Retirement_Savings_Election_group_Elected'] = get_text(rse_group_element, 'wd:Elected', NAMESPACE)
                
                ret_code_elem = rse_group_element.find('wd:RetirementCode', NAMESPACE)
                if ret_code_elem is not None:
                    record['Retirement_Savings_Election_group_RetirementCode_Descriptor'] = ret_code_elem.get(f"{{{NAMESPACE['wd']}}}Descriptor")
                    record['Retirement_Savings_Election_group_RetirementCode_ID_WID'] = get_typed_id_text(ret_code_elem, '.', 'WID', NAMESPACE)
                    record['Retirement_Savings_Election_group_RetirementCode_ID_Defined_Contribution_Plan_ID'] = get_typed_id_text(ret_code_elem, '.', 'Defined_Contribution_Plan_ID', NAMESPACE)
                    record['Retirement_Savings_Election_group_RetirementCode_ID_Benefit_Plan_ID'] = get_typed_id_text(ret_code_elem, '.', 'Benefit_Plan_ID', NAMESPACE)
            
            all_records.append(record)

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None
    except FileNotFoundError:
        print(f"Error: File not found at {xml_file_path}")
        return None
    
    return all_records

def write_to_csv(data, csv_file_path, field_names):
    """Writes the list of dictionaries to a CSV file."""
    if not data:
        print("No data to write to CSV.")
        return

    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        print(f"Successfully wrote {len(data)} records to {csv_file_path}")
    except IOError as e:
        print(f"Error writing to CSV: {e}")


if __name__ == '__main__':
    # The xml_input_file is already defined globally using config.ini
    # No need for alternative path checks if config.ini is set up correctly.
    
    if not os.path.exists(xml_input_file):
        print(f"Error: The input XML file '{xml_input_file}' as defined in config.ini was not found.")
        # Create CSV with headers only if XML is not found, then exit
        field_names_for_csv = get_all_field_names()
        try:
            with open(csv_output_file, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=field_names_for_csv)
                writer.writeheader()
            print(f"Created empty CSV '{csv_output_file}' with headers because input file was not found.")
        except IOError as e:
            print(f"Error writing empty CSV '{csv_output_file}'. Details: {e}")
        exit()
                
    print(f"Attempting to parse: {os.path.abspath(xml_input_file)}")

    # Get and format the file modification date
    try:
        timestamp = os.path.getmtime(xml_input_file)
        formatted_mod_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except Exception as e:
        print(f"Warning: Could not retrieve or format modification date for {xml_input_file}. Error: {e}")
        formatted_mod_date = '' # Default to empty if there's an error
    
    print(f"Using file modification date: {formatted_mod_date if formatted_mod_date else 'N/A'}")
    parsed_data = parse_workday_xml(xml_input_file, formatted_mod_date) # Pass formatted_mod_date

    if parsed_data:
        print(f"\nSuccessfully parsed {len(parsed_data)} records.")
        if len(parsed_data) > 0:
            print("\nSample of the first record (JSON format):")
            print(json.dumps(parsed_data[0], indent=4))

            # -- Optional: Write to CSV --
            # Define the output CSV file path
            output_csv_file = csv_output_file # Path relative to the script's location
            # Get all field names from the first record (assuming all records have the same structure)
            # or use the predefined list from get_all_field_names() for consistency
            field_names_for_csv = get_all_field_names()
            write_to_csv(parsed_data, output_csv_file, field_names_for_csv)
    else:
        print("Parsing failed or no records found.")