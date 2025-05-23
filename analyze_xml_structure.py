import xml.etree.ElementTree as ET
from collections import defaultdict
import argparse

def analyze_xml(xml_file_path):
    """
    Analyzes the structure of an XML file, identifying unique tags,
    their attributes, and their parent-child relationships.

    Args:
        xml_file_path (str): The path to the XML file.
    """
    print(f"Analyzing XML structure for: {xml_file_path}\n")

    unique_tags = set()
    tag_attributes = defaultdict(set)
    # {tag: {'parents': set(), 'children': set()}}
    tag_hierarchy = defaultdict(lambda: {'parents': set(), 'children': set()})
    namespaces = {} # To store URI: prefix

    try:
        # Use iterparse to capture namespace information and element events
        # iterparse yields (event, elem_or_root) tuples
        # 'start-ns' event provides (prefix, uri)
        # 'start' event provides the element when its opening tag is encountered
        # 'end' event provides the element when its closing tag is encountered

        path_context = [] # To keep track of current parent

        for event, elem_or_ns in ET.iterparse(xml_file_path, events=('start', 'end', 'start-ns')):
            if event == 'start-ns':
                prefix, uri = elem_or_ns
                namespaces[uri] = prefix if prefix else 'DEFAULT'
            elif event == 'start':
                tag_name = elem_or_ns.tag
                unique_tags.add(tag_name)

                for attr_name in elem_or_ns.attrib:
                    tag_attributes[tag_name].add(attr_name)

                if path_context:
                    parent_tag_name = path_context[-1]
                    tag_hierarchy[tag_name]['parents'].add(parent_tag_name)
                    tag_hierarchy[parent_tag_name]['children'].add(tag_name)
                
                path_context.append(tag_name)
                elem_or_ns.clear() # Free memory for very large files

            elif event == 'end':
                if path_context and path_context[-1] == elem_or_ns.tag:
                    path_context.pop()
                elem_or_ns.clear() # Free memory for very large files


    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {e}")
        return
    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
        return

    print("--- Namespaces Discovered (URI: Suggested Prefix) ---")
    if namespaces:
        for uri, prefix in namespaces.items():
            print(f"  {uri}: {prefix}")
    else:
        print("  No namespaces declared with 'start-ns' events (or file is empty/not XML).")
    print("\n--- Unique Element Tags ---")
    for tag in sorted(list(unique_tags)):
        print(f"  {tag}")

    print("\n--- Tag Attributes ---")
    for tag in sorted(tag_attributes.keys()):
        print(f"  Tag: {tag}")
        if tag_attributes[tag]:
            for attr in sorted(list(tag_attributes[tag])):
                print(f"    - Attribute: {attr}")
        else:
            print("    - (No attributes)")

    print("\n--- Tag Hierarchy (Parent-Child Relationships) ---")
    for tag in sorted(tag_hierarchy.keys()):
        print(f"  Tag: {tag}")
        parents = sorted(list(tag_hierarchy[tag]['parents']))
        children = sorted(list(tag_hierarchy[tag]['children']))
        if parents:
            print(f"    Parents: {', '.join(parents)}")
        else:
            print("    Parents: (None - likely root or parsing context issue)")
        if children:
            print(f"    Children: {', '.join(children)}")
        else:
            print("    Children: (None - leaf node)")
        print("-" * 20)
    
    print("\nAnalysis complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze XML file structure.")
    parser.add_argument("xml_file", help="Path to the XML file to analyze.")
    args = parser.parse_args()

    analyze_xml(args.xml_file)