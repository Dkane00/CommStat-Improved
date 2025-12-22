# V BrevityBeta0.9.1. Building on BrevityBeta0.9 getting ready for Brevity1 release
# 0.9.1 bug fix to allow keyed code to decode if "A-Unknown" selected for station status. 
# 0.9.1 allow the enter key to trigger the brevity search
# 0.9.1 corrected 1 dropdown not reflecting file if brevity entered 
# 0.9.1 #out a section preventing the "Y" code from being used in menu 5.



import tkinter as tk
from tkinter import ttk, messagebox
import re
import json
import traceback
import os
import glob
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")
# Global variables
positions = {}
updating_menus = False
emergency_list_mapping = {}
current_file = None

def show_status_message(message, timeout=5000):
    try:
        status_bar.config(state="normal")
        status_bar.delete("1.0", tk.END)
        status_bar.insert(tk.END, message)
        status_bar.config(state="disabled")
        if timeout:
            root.after(timeout, lambda: [status_bar.config(state="normal"), status_bar.delete("1.0", tk.END), status_bar.config(state="disabled")])
    except NameError:
        logging.debug(f"Cannot show status message '{message}'")
    except Exception as e:
        logging.debug(f"Error in show_status_message: {str(e)}")

def get_json_files():
    global emergency_list_mapping
    emergency_list_mapping = {}
    brevity_dir = os.path.dirname(os.path.abspath(__file__)) # Use script's directory
    logging.info(f"Scanning directory {brevity_dir} for JSON files")
    if not os.path.exists(brevity_dir):
        logging.error(f"Directory {brevity_dir} does not exist")
        return emergency_list_mapping
    files = sorted(glob.glob(os.path.join(brevity_dir, "[0-9]-*.json")))
    logging.info(f"Found files: {files}")
    if not files:
        logging.warning("No JSON files found matching pattern [0-9]-*.json")
        return emergency_list_mapping
    for file_path in files:
        filename = os.path.basename(file_path)
        logging.debug(f"Processing file: {filename}")
        if not re.match(r'^[0-9]-.*\.json$', filename, flags=re.IGNORECASE):
            logging.debug(f"Skipping {filename}: does not match pattern [0-9]-*.json")
            continue
        prefix = filename[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if validate_json_structure(data):
                if prefix in emergency_list_mapping:
                    logging.warning(f"Skipping duplicate emergency prefix {prefix} in {filename}")
                    continue
                emergency_list_mapping[prefix] = filename
                logging.info(f"Mapped emergency file {filename} to prefix {prefix}")
            else:
                logging.warning(f"Ignoring {filename} due to invalid JSON structure")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {filename}: {str(e)}")
        except PermissionError:
            logging.error(f"Permission denied accessing {filename}")
        except Exception as e:
            logging.error(f"Error processing {filename}: {str(e)}")
    logging.info(f"emergency_list_mapping = {emergency_list_mapping}")
    return emergency_list_mapping

def validate_json_structure(data):
    required_keys = ["emergency_type", "public_reaction", "station_response", "shared_impacts",
                     "emergency_group_order", "impact_group_order", "group_descriptions", "status_codes"]
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        logging.warning(f"Missing required keys in JSON: {missing_keys}")
        return False
    if "A" not in data["emergency_type"]:
        logging.warning("Missing required code 'A' in emergency_type")
        return False
    if "A" not in data["status_codes"]:
        logging.warning("Missing required code 'A' in status_codes")
        return False
    return True

def generate_description(parts, severity_code, list_id, code, status_code, secondary_code, emergency_group, impact_group):
    station_group = "Unknown"
    for group_name, group in positions["station_response"].items():
        if isinstance(group, dict) and "items" in group and severity_code in group.get("items", []):
            station_group = group_name
            break
    public_group = "Unknown"
    for group_name, group in positions["public_reaction"].items():
        if isinstance(group, dict) and "items" in group and secondary_code in group.get("items", []):
            public_group = group_name
            break
    status_group = "Unknown"
    for group_name, group in positions["status_codes"].items():
        if group_name.startswith("***") and status_code in group.get("items", []):
            status_group = group_name
            break
    impact_group = "Unknown"
    impacts = positions.get("shared_impacts", {})
    if isinstance(impacts, dict):
        for group, sub_impacts in impacts.items():
            if group.startswith("***") and isinstance(sub_impacts, dict) and "items" in sub_impacts:
                if parts[1] and parts[1] in [impacts[code]["name"] for code in sub_impacts["items"] if code in impacts]:
                    impact_group = group
                    break
    gui_titles = positions.get("gui_titles", {})
    station_group_clean = re.sub(r'^\w\s+', '', station_group.replace('*** ', '').replace(' ***', ''))
    return (
        f"Brevity Code: {code}{' ' * 20}File: {emergency_list_mapping.get(list_id, 'Unknown')}\n"
        f"{gui_titles.get('emergency', 'Event:')} {emergency_group.replace('*** ', '').replace(' ***', '')}: {parts[0] or 'Unknown'}\n"
        f"{gui_titles.get('status', 'Status or Target:')} {status_group.replace('*** ', '').replace(' ***', '')}: {parts[4] or 'Unknown'}\n"
        f"{gui_titles.get('primary', 'Impact:')} {impact_group.replace('*** ', '').replace(' ***', '')}: {parts[1] or 'Unknown'}\n"
        f"{gui_titles.get('secondary', 'Response:')} {public_group.replace('*** ', '').replace(' ***', '')}: {parts[2] or 'Unknown'}\n"
        f"{gui_titles.get('severity', 'Station Status:')} {station_group_clean}: {parts[3] or 'Unknown'}"
    )

def generate_narrative(parts, emergency_code, primary_code, secondary_code, severity_code, status_code, code, list_id):
    emergency_group = "Unknown"
    for group, sub_emergencies in positions["emergency_type"].items():
        if group.startswith("***") and emergency_code in sub_emergencies:
            emergency_group = group
            break
        elif group == emergency_code:
            emergency_group = "Unknown"
            break
    impact_group = "Unknown"
    impacts = positions.get("shared_impacts", {})
    if isinstance(impacts, dict):
        for group, sub_impacts in impacts.items():
            if isinstance(sub_impacts, dict) and "items" in sub_impacts:
                if primary_code in sub_impacts["items"] and primary_code in impacts:
                    impact_group = group
                    break
            elif primary_code in sub_impacts:
                impact_group = group
                break
    public_group = "Unknown"
    for group_name, group in positions["public_reaction"].items():
        if isinstance(group, dict) and "items" in group and secondary_code in group.get("items", []):
            public_group = group_name
            break
    station_group = "Unknown"
    for group, sub_response in positions.get("station_response", {}).items():
        if isinstance(sub_response, dict) and "items" in sub_response:
            if severity_code in sub_response["items"] and severity_code in positions["station_response"]:
                station_group = group
                break
    status_group = "Unknown"
    for group_name, group in positions["status_codes"].items():
        if group_name.startswith("***") and status_code in group.get("items", []):
            status_group = group_name
            break
    emergency_desc = positions.get("group_descriptions", {}).get(emergency_group, "No event group description available.")
    impact_desc = positions.get("group_descriptions", {}).get(impact_group, "No impact group description available.")
    public_desc = positions["public_reaction"].get(public_group, {}).get("description", "No response group description available.")
    station_desc = positions["station_response"].get(station_group, {}).get("description", "No station status group description available.")
    status_desc = positions["status_codes"].get(status_group, {}).get("description", "No status group description available.")
    gui_titles = positions.get("gui_titles", {})
    narrative = (
        f"Brevity Code: {code} ({emergency_list_mapping.get(list_id, 'Unknown')})\n\n"
        f"{gui_titles.get('emergency', 'Event:').rstrip(':')} Group: {emergency_group.replace('*** ', '').replace(' ***', '')}\n"
        f"{emergency_desc}\n\n"
        f"{gui_titles.get('status', 'Status or Target:').rstrip(':')} Group: {status_group.replace('*** ', '').replace(' ***', '')}\n"
        f"{status_desc}\n\n"
        f"{gui_titles.get('primary', 'Impact:').rstrip(':')} Group: {impact_group.replace('*** ', '').replace(' ***', '')}\n"
        f"{impact_desc}\n\n"
        f"{gui_titles.get('secondary', 'Response:').rstrip(':')} Group: {public_group.replace('*** ', '').replace(' ***', '')}\n"
        f"{public_desc}\n\n"
        f"{gui_titles.get('severity', 'Station Status:').rstrip(':')} Group: {station_group.replace('*** ', '').replace(' ***', '')}\n"
        f"{station_desc}"
    )
    return narrative

def load_selected_file(list_id):
    global positions, current_file
    filename = emergency_list_mapping.get(list_id)
    if not filename:
        logging.warning("No valid JSON files available")
        return
    if filename == current_file:
        logging.debug(f"File {filename} already loaded, skipping")
        return
    brevity_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(brevity_dir, filename)
    logging.info(f"Attempting to load {filename} from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not validate_json_structure(data):
            logging.warning(f"Invalid JSON structure in {filename}")
            return
        positions = data
        current_file = filename
        # Only update GUI elements if they are defined
        if 'label_select' in globals():
            gui_titles = positions.get("gui_titles", {})
            label_select.config(text=gui_titles.get("select_list", "1. Select List:"))
            label_emergency.config(text=gui_titles.get("emergency", "2. Event:"))
            label_status.config(text=gui_titles.get("status", "3. Status/Target:"))
            label_primary.config(text=gui_titles.get("primary", "4. Impact:"))
            label_secondary.config(text=gui_titles.get("secondary", "5. Response:"))
            label_severity.config(text=gui_titles.get("severity", "6. Station/Location:"))
            list_var.set(filename)
            emergency_var.set("Select Code")
            status_var.set("Select Code")
            primary_var.set("Select Code")
            secondary_var.set("Select Code")
            severity_var.set("Select Code")
            output_text.delete("1.0", tk.END)
            narrative_text.config(state="normal")
            narrative_text.delete("1.0", tk.END)
            narrative_text.config(state="disabled")
            first_emergency_code = sorted([k for k in positions["emergency_type"].keys() if not k.startswith("***")])[0] if positions["emergency_type"] else "A"
            update_menus(first_emergency_code)
            root.update()
            show_status_message(f"Loaded {filename}", 5000)
    except FileNotFoundError:
        logging.error(f"File not found: {filename}")
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in {filename}: {str(e)}")
    except Exception as e:
        logging.error(f"Error loading {filename}: {str(e)}")

def validate_code_input(new_value):
    if len(new_value) > 6:
        return False
    return bool(re.match(r'^[0-9]?[A-Za-z]?[A-Za-z]?[A-Za-z]*$', new_value))

def decode_code(event=None, decode_entry=None, output_text=None, narrative_text=None, list_var=None, emergency_var=None, status_var=None, primary_var=None, secondary_var=None, severity_var=None):
    if decode_entry is None:
        decode_entry = globals().get('decode_entry')
    if output_text is None:
        output_text = globals().get('output_text')
    if narrative_text is None:
        narrative_text = globals().get('narrative_text')
    if list_var is None:
        list_var = globals().get('list_var')
    if emergency_var is None:
        emergency_var = globals().get('emergency_var')
    if status_var is None:
        status_var = globals().get('status_var')
    if primary_var is None:
        primary_var = globals().get('primary_var')
    if secondary_var is None:
        secondary_var = globals().get('secondary_var')
    if severity_var is None:
        severity_var = globals().get('severity_var')
    code = (decode_entry.get().strip().upper() if decode_entry else "").strip()
    #if not re.match(r'^[0-9][A-Z]{5}$', code):
    #    show_status_message(f"Invalid code: Use format #AAAAA", 10000)
    #    logging.warning(f"Invalid code format: {code}")
    #    return f"Invalid code: Use format #AAAAA"
    
    if not re.match(r'^[0-9][A-Z]{5}$', code):
        show_status_message(f"Invalid code: Use format #AAAAA", 10000)
        logging.warning(f"Invalid code format: {code}")
        if output_text:
            output_text.delete("1.0", tk.END)
        if narrative_text:
            narrative_text.config(state="normal")
            narrative_text.delete("1.0", tk.END)
            narrative_text.config(state="disabled")
        return f"Invalid code: Use format #AAAAA"
    
    list_id = code[0]
    emergency_code = code[1]
    status_code = code[2]
    primary_code = code[3]
    secondary_code = code[4]
    severity_code = code[5]
    if list_id not in emergency_list_mapping:
        show_status_message(f"Invalid list ID: {list_id}", 10000)
        logging.warning(f"Invalid list ID: {list_id}")
        return f"Invalid list ID: {list_id}"
    current_file_selected = list_var.get() if list_var else ""
    expected_file = emergency_list_mapping[list_id]
    if current_file_selected != expected_file:
        logging.debug(f"Mismatch in selected file. Expected {expected_file}, loading")
        load_selected_file(list_id)
    if list_var is not None:
        list_var.set(expected_file)
    if current_file_selected != expected_file:
        logging.debug(f"Mismatch in selected file. Expected {expected_file}, loading")
        load_selected_file(list_id)
    if not positions:
        show_status_message("No event list loaded", 10000)
        logging.warning("No positions data loaded")
        return "No event list loaded"
    try:
        # Debug: Log positions state
        logging.debug(f"positions keys: {list(positions.keys())}")
        logging.debug(f"station_response: {positions.get('station_response', {})}")
        logging.debug(f"Checking severity_code: {severity_code}")
        
        emergency_data = None
        emergency_group = "Unknown"
        has_groups = any(k.startswith("***") for k in positions["emergency_type"].keys())
        if has_groups:
            for group, sub_emergencies in positions["emergency_type"].items():
                if group.startswith("***") and emergency_code in sub_emergencies:
                    emergency_data = sub_emergencies[emergency_code]
                    emergency_group = group
                    break
                elif group == emergency_code:
                    emergency_data = positions["emergency_type"][emergency_code]
                    emergency_group = "Unknown"
                    break
        else:
            if emergency_code in positions["emergency_type"]:
                emergency_data = positions["emergency_type"][emergency_code]
                emergency_group = "Unknown"
        if not emergency_data:
            show_status_message(f"Invalid Event Type code: {emergency_code}", 10000)
            logging.warning(f"Invalid Event Type code: {emergency_code}")
            return f"Invalid Event Type code: {emergency_code}"
        impacts = positions.get("shared_impacts", {})
        valid_primary_code = False
        primary_impact_name = None
        impact_group = "Unknown"
        if isinstance(impacts, dict):
            if primary_code in impacts and isinstance(impacts[primary_code], dict) and "name" in impacts[primary_code]:
                valid_primary_code = True
                primary_impact_name = impacts[primary_code]["name"]
                impact_group = impacts[primary_code].get("group", "Unknown")
            else:
                for group, sub_impacts in impacts.items():
                    if isinstance(sub_impacts, dict) and "items" in sub_impacts:
                        if primary_code in sub_impacts["items"] and primary_code in impacts:
                            valid_primary_code = True
                            primary_impact_name = impacts[primary_code]["name"]
                            impact_group = group
                            break
        if not valid_primary_code:
            show_status_message(f"Invalid Impact code: {primary_code}", 10000)
            logging.warning(f"Invalid Impact code: {primary_code}")
            return f"Invalid Impact code: {primary_code}"
        if secondary_code not in positions["public_reaction"]:
            show_status_message(f"Invalid Response code: {secondary_code}", 10000)
            logging.warning(f"Invalid Response code: {secondary_code}")
            return f"Invalid Response code: {secondary_code}"
        #if secondary_code == "Y":
        #    show_status_message("Invalid Response code: Y is reserved", 10000)
        #    logging.warning("Invalid Response code: Y is reserved")
        #    return "Invalid Response code: Y is reserved"
        station_response = positions.get("station_response", {})
        valid_severity_code = False
        severity_name = "Unknown"
        # Check standalone keys first (e.g., 'A' for Station Status)
        if severity_code in station_response and isinstance(station_response[severity_code], dict) and "name" in station_response[severity_code]:
            valid_severity_code = True
            severity_name = station_response[severity_code]["name"]
        else:
            # Check groups for other codes
            for group, sub_response in station_response.items():
                if isinstance(sub_response, dict) and "items" in sub_response:
                    if severity_code in sub_response["items"] and severity_code in station_response:
                        valid_severity_code = True
                        severity_name = station_response[severity_code].get("name", "Unknown")
                        break
        if not valid_severity_code:
            show_status_message(f"Invalid Station Status code: {severity_code}", 10000)
            logging.warning(f"Invalid Station Status code: {severity_code}")
            return f"Invalid Station Status code: {severity_code}"
        if status_code not in positions["status_codes"]:
            show_status_message(f"Invalid Status/Target code: {status_code}", 10000)
            logging.warning(f"Invalid Status/Target code: {status_code}")
            return f"Invalid Status/Target code: {status_code}"
     
        # Only update GUI elements if they are provided
        if emergency_var is not None:
            emergency_var.set(f"{emergency_code}-{emergency_data['name']}")
            update_menus(emergency_code)
        if primary_var is not None:
            primary_var.set(f"{primary_code}-{primary_impact_name}")
        if secondary_var is not None:
            secondary_var.set(f"{secondary_code}-{positions['public_reaction'][secondary_code]['name']}")
        if severity_var is not None:
            severity_var.set(f"{severity_code}-{positions['station_response'].get(severity_code, {}).get('name', 'Unknown')}")
        if status_var is not None:
            status_var.set(f"{status_code}-{positions['status_codes'][status_code]['name']}")
        # Only call root.update() if root is defined (i.e., in GUI mode)
        if 'root' in globals():
            globals()['root'].update()
     
        description_parts = [
            emergency_data["name"] if emergency_code != "A" else None,
            primary_impact_name if primary_code != "A" else None,
            positions["public_reaction"][secondary_code]["name"] if secondary_code != "A" else None,
            severity_name if severity_code != "A" else None,
            positions["status_codes"][status_code]["name"] if status_code in positions["status_codes"] else "Unknown"
        ]
        description = generate_description(description_parts, severity_code, list_id, code, status_code, secondary_code, emergency_group, impact_group)
        narrative = generate_narrative(description_parts, emergency_code, primary_code, secondary_code, severity_code, status_code, code, list_id)
     
        if output_text:
            output_text.delete("1.0", tk.END)
            output_text.insert(tk.END, description)
            output_lines = description.split('\n')
            for i, line in enumerate(output_lines):
                if line.startswith("Brevity Code:"):
                    output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len('Brevity Code:')}")
                    file_start = line.find("File:")
                    if file_start != -1:
                        output_text.tag_add("bold", f"{i+1}.{file_start}", f"{i+1}.{file_start + len('File:')}")
                elif line.startswith(positions.get("gui_titles", {}).get('emergency', 'Event:')):
                    output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('emergency', 'Event:'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('status', 'Status or Target:')):
                    output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('status', 'Status or Target:'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('primary', 'Impact:')):
                    output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('primary', 'Impact:'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('secondary', 'Response:')):
                    output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('secondary', 'Response:'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('severity', 'Station Status:')):
                    output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('severity', 'Station Status:'))}")
        if narrative_text:
            narrative_text.config(state="normal")
            narrative_text.delete("1.0", tk.END)
            narrative_text.insert(tk.END, f"{narrative}")
            narrative_lines = narrative.split('\n')
            for i, line in enumerate(narrative_lines):
                if line.startswith("Brevity Code:"):
                    narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len('Brevity Code:')}")
                elif line.startswith(positions.get("gui_titles", {}).get('emergency', 'Event:').rstrip(':')):
                    narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('emergency', 'Event:').rstrip(':'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('status', 'Status or Target:').rstrip(':')):
                    narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('status', 'Status or Target:').rstrip(':'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('primary', 'Impact:').rstrip(':')):
                    narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('primary', 'Impact:').rstrip(':'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('secondary', 'Response:').rstrip(':')):
                    narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('secondary', 'Response:').rstrip(':'))}")
                elif line.startswith(positions.get("gui_titles", {}).get('severity', 'Station Status:').rstrip(':')):
                    narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('severity', 'Station Status:').rstrip(':'))}")
            narrative_text.config(state="disabled")
        show_status_message("Brevity code generated", 5000)
        return description
    except Exception as e:
        logging.error(f"Error decoding code: {str(e)}")
        show_status_message(f"Error decoding code: {str(e)}", 10000)
        return f"Error decoding code: {str(e)}"

def decode_to_report(code):
    """Decode a brevity code and return the Brevity Report as a string."""
    global emergency_list_mapping, positions, current_file
    emergency_list_mapping = get_json_files()
    if not emergency_list_mapping:
        return "Error: No valid JSON files found"
    code = code.strip().upper()
    # Create a mock decode_entry object to pass the code
    class MockEntry:
        def get(self):
            return code
    result = decode_code(
        decode_entry=MockEntry(),
        output_text=None,
        narrative_text=None,
        list_var=None,
        emergency_var=None,
        status_var=None,
        primary_var=None,
        secondary_var=None,
        severity_var=None
    )
    return result

def clear_fields():
    global updating_menus
    updating_menus = False
    list_var.set("Select Emergency List")
    emergency_var.set("Select Code")
    status_var.set("Select Code")
    primary_var.set("Select Code")
    secondary_var.set("Select Code")
    severity_var.set("Select Code")
    output_text.delete("1.0", tk.END)
    narrative_text.config(state="normal")
    narrative_text.delete("1.0", tk.END)
    narrative_text.config(state="disabled")
    if 'decode_entry' in globals():
        decode_entry.delete(0, tk.END)
    show_status_message("Fields cleared", 5000)
    logging.debug("Cleared all fields and outputs")

def populate_menu(menu, var, data, key, button, max_length=100, group_order=None, select_handler=None, emergency_code=None):
    menu.delete(0, tk.END)
    if not data:
        menu.add_command(label=f"No {key} Available".ljust(max_length), command=lambda: None)
        return
    if "A" in data and key != "status":
        val = f"A-{data['A'].get('name', 'Unknown')}"
        menu.add_command(label=val.ljust(max_length),
                        command=lambda v=val: [var.set(v), select_handler(var, key, menu, button, v[0], emergency_code)])
        menu.add_separator()
    has_groups = any(k.startswith("***") for k in data.keys())
    if has_groups and group_order:
        for group in group_order:
            if group in data:
                menu.add_command(label=group, command=lambda: None, foreground="#00008B", font=("Arial", 10, "bold"))
                group_data = data[group]
                codes_in_group = []
                if "items" in group_data and isinstance(group_data["items"], list):
                    codes_in_group = [c for c in sorted(group_data["items"]) if c in data and isinstance(data[c], dict) and "name" in data[c]]
                else:
                    codes_in_group = sorted([c for c in group_data.keys() if re.match(r'^[A-Z]$', c)])
                for code in codes_in_group:
                    name = data.get(code, {}).get('name', 'Unknown') if key == "impacts" else group_data[code].get('name', 'Unknown')
                    val = f"{code}-{name}"
                    menu.add_command(label=(" " + val).ljust(max_length),
                                   command=lambda v=val, g=group: [var.set(v), select_handler(var, key, menu, button, v[0], emergency_code, g)])
                menu.add_separator()
    else:
        for code in sorted(data.keys()):
            if code == "A" or code.startswith("***"): continue
            val = f"{code}-{data[code].get('name', 'Unknown')}"
            menu.add_command(label=val.ljust(max_length),
                           command=lambda v=val: [var.set(v), select_handler(var, key, menu, button, v[0], emergency_code)])

def update_menus(emergency_code, primary_code=None):
    global updating_menus
    if updating_menus:
        logging.debug("Skipping update_menus: already in progress")
        return
    updating_menus = True
    try:
        logging.debug(f"Updating menus for emergency_code={emergency_code}")
        max_length = 100
        # Only update menus if GUI elements are defined
        if 'emergency_menu' in globals():
            emergency_menu.delete(0, tk.END)
            if not positions:
                emergency_menu.add_command(label="No Event List Loaded".ljust(max_length), command=lambda: None)
            else:
                populate_menu(emergency_menu, emergency_var, positions["emergency_type"], "emergency_type",
                             emergency_button, max_length, positions.get("emergency_group_order", []),
                             handle_menu_select, emergency_code)
        if 'primary_menu' in globals():
            primary_menu.delete(0, tk.END)
            populate_menu(primary_menu, primary_var, positions.get("shared_impacts", {}), "impacts",
                         primary_button, max_length, positions.get("impact_group_order", []),
                         handle_menu_select, emergency_code)
        if 'secondary_menu' in globals():
            secondary_menu.delete(0, tk.END)
            if not positions.get("public_reaction", {}):
                secondary_menu.add_command(label="No Response Available".ljust(max_length), command=lambda: None)
            else:
                if "A" in positions["public_reaction"]:
                    val = f"A-{positions['public_reaction']['A']['name']}"
                    secondary_menu.add_command(label=val.ljust(max_length),
                                            command=lambda v=val: [secondary_var.set(v), handle_menu_select(secondary_var, "public_reaction", secondary_menu, secondary_button, v[0])])
                    secondary_menu.add_separator()
                for group_name in sorted(positions["public_reaction"].keys(), key=lambda x: positions["public_reaction"][x].get("order", float("inf")) if isinstance(positions["public_reaction"][x], dict) and "order" in positions["public_reaction"][x] else float("inf")):
                    if not group_name.startswith("***"): continue
                    group = positions["public_reaction"][group_name]
                    secondary_menu.add_command(label=group_name, command=lambda: None, foreground="#00008B", font=("Arial", 10, "bold"))
                    for code in sorted(group.get("items", [])):
                        if code in positions["public_reaction"]:
                            val = f"{code}-{positions['public_reaction'][code].get('name', 'Unknown')}"
                            secondary_menu.add_command(label=(" " + val).ljust(max_length),
                                                    command=lambda v=val, g=group_name: [secondary_var.set(v), handle_menu_select(secondary_var, "public_reaction", secondary_menu, secondary_button, v[0], None, g)])
                    secondary_menu.add_separator()
                unmapped_items = [code for code in sorted(positions["public_reaction"].keys()) if code != "A" and code != "Y" and not code.startswith("***") and not any(code in group.get("items", []) for group in positions["public_reaction"].values() if isinstance(group, dict) and "items" in group)]
                if unmapped_items:
                    secondary_menu.add_separator()
                    for code in sorted(unmapped_items):
                        val = f"{code}-{positions['public_reaction'][code].get('name', 'Unknown')}"
                        secondary_menu.add_command(label=val.ljust(max_length),
                                                command=lambda v=val: [secondary_var.set(v), handle_menu_select(secondary_var, "public_reaction", secondary_menu, secondary_button, v[0])])
        if 'severity_menu' in globals():
            severity_menu.delete(0, tk.END)
            if not positions.get("station_response", {}):
                severity_menu.add_command(label="No Station Status Available".ljust(max_length), command=lambda: None)
            else:
                if "A" in positions["station_response"] and not positions["station_response"]["A"].get("group"):
                    val = f"A-{positions['station_response']['A'].get('name', 'Unknown')}"
                    severity_menu.add_command(label=val.ljust(max_length),
                                           command=lambda v=val: [severity_var.set(v), handle_menu_select(severity_var, "station_response", severity_menu, severity_button, v[0])])
                    severity_menu.add_separator()
                for group_name, group in sorted(positions["station_response"].items(), key=lambda x: x[1].get("order", float("inf")) if isinstance(x[1], dict) and "order" in x[1] else float("inf")):
                    if not group_name.startswith("***"): continue
                    severity_menu.add_command(label=group_name, command=lambda: None, foreground="#00008B", font=("Arial", 10, "bold"))
                    response_dict = positions["station_response"]
                    for code in sorted(group.get("items", [])):
                        if code in response_dict:
                            name = response_dict[code].get('name', 'Unknown')
                            val = f"{code}-{name}"
                            severity_menu.add_command(label=(" " + val).ljust(max_length),
                                                   command=lambda v=val, g=group_name: [severity_var.set(v), handle_menu_select(severity_var, "station_response", severity_menu, severity_button, v[0], None, g)])
                    severity_menu.add_separator()
        if 'status_menu' in globals():
            status_menu.delete(0, tk.END)
            if not positions.get("status_codes"):
                status_menu.add_command(label="No Status/Target List Loaded".ljust(max_length), command=lambda: None)
                logging.debug("No valid status codes available, using default label")
            else:
                status_group_order = sorted(
                    [g for g in positions["status_codes"].keys() if g.startswith("***")],
                    key=lambda x: positions["status_codes"][x].get("order", float("inf"))
                )
                codes = {k: v for k, v in positions["status_codes"].items() if not k.startswith("***")}
                standalone_codes = [code for code in sorted(codes.keys()) if not any(code in group.get("items", []) for group in positions["status_codes"].values() if group.get("items"))]
                for code in standalone_codes:
                    val = f"{code}-{codes[code].get('name', 'Unknown')}"
                    status_menu.add_command(label=val.ljust(max_length),
                                          command=lambda v=val: [status_var.set(v), handle_menu_select(status_var, "status", status_menu, status_button, v[0])])
                if standalone_codes:
                    status_menu.add_separator()
                for group_name in status_group_order:
                    if group_name in positions["status_codes"]:
                        status_menu.add_command(label=group_name, command=lambda: None, foreground="#00008B", font=("Arial", 10, "bold"))
                        for code in sorted(positions["status_codes"][group_name].get("items", [])):
                            if code in codes:
                                val = f"{code}-{codes[code].get('name', 'Unknown')}"
                                status_menu.add_command(label=(" " + val).ljust(max_length),
                                                      command=lambda v=val, g=group_name: [status_var.set(v), handle_menu_select(status_var, "status", status_menu, status_button, v[0], None, g)])
    finally:
        updating_menus = False
        if 'root' in globals():
            globals()['root'].update()

def handle_menu_select(var, key, menu, button, code, emergency_code=None, group=None):
    if var.get() == "Select Code":
        logging.debug(f"Ignoring 'Select Code' selection for key={key}")
        return
    logging.debug(f"Handling menu selection: key={key}, code={code}")
    if key == "list":
        emergency_var.set("Select Code")
        status_var.set("Select Code")
        primary_var.set("Select Code")
        secondary_var.set("Select Code")
        severity_var.set("Select Code")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.config(state="disabled")
        update_menus("A")
        if 'root' in globals():
            globals()['root'].update()
    elif key == "emergency_type":
        status_var.set("Select Code")
        primary_var.set("Select Code")
        secondary_var.set("Select Code")
        severity_var.set("Select Code")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.config(state="disabled")
        update_menus(code)
        if 'root' in globals():
            globals()['root'].update()
    elif key == "status":
        primary_var.set("Select Code")
        secondary_var.set("Select Code")
        severity_var.set("Select Code")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        group_description = positions["status_codes"].get(group, {}).get("description", "No group description available")
        narrative_text.insert(tk.END, group_description)
        narrative_text.config(state="disabled")
        update_menus(emergency_var.get().split("-")[0] if emergency_var.get() != "Select Code" else "A")
        if 'root' in globals():
            globals()['root'].update()
    elif key == "impacts":
        secondary_var.set("Select Code")
        severity_var.set("Select Code")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.config(state="disabled")
        update_menus(emergency_code)
        if 'root' in globals():
            globals()['root'].update()
    elif key == "public_reaction":
        severity_var.set("Select Code")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        group_description = positions["public_reaction"].get(group, {}).get("description", "No response group description available" if code != "A" else "No group description for Unknown")
        narrative_text.insert(tk.END, group_description)
        narrative_text.config(state="disabled")
        update_menus(emergency_var.get().split("-")[0] if emergency_var.get() != "Select Code" else "A")
        if 'root' in globals():
            globals()['root'].update()
    elif key == "station_response":
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        group_description = positions["station_response"].get(group, {}).get("description", "No station status group description available" if code != "A" else "No group description for Unknown")
        narrative_text.insert(tk.END, group_description)
        narrative_text.config(state="disabled")
        update_menus(emergency_var.get().split("-")[0] if emergency_var.get() != "Select Code" else "A")
        if 'root' in globals():
            globals()['root'].update()
    on_field_change()

def copy_code_text(copy_full_description=False):
    try:
        first_line = output_text.get("1.0", "2.0").strip()
        if not first_line.startswith("Brevity Code:"):
            show_status_message("No brevity code available to copy", 10000)
            logging.debug("No brevity code available")
            return
        code = first_line[13:].split("File:")[0].strip()
        if not code:
            show_status_message("No brevity code available to copy", 10000)
            logging.debug("Empty brevity code")
            return
        text = output_text.get("1.0", tk.END).strip() if copy_full_description else code
        root.clipboard_clear()
        root.clipboard_append(text)
        show_status_message("Code copied to clipboard", 5000)
        logging.debug(f"Copied {'full description' if copy_full_description else 'code'}")
    except Exception as e:
        show_status_message(f"Error copying code: {str(e)}", 10000)
        logging.debug(f"Error copying code: {str(e)}")

def copy_all():
    try:
        output = output_text.get("1.0", tk.END).strip()
        narrative = narrative_text.get("1.0", tk.END).strip()
        if not output and not narrative:
            show_status_message("No output or narrative available to copy", 10000)
            logging.debug("No output or narrative available")
            return
        combined_text = output
        if narrative:
            combined_text += "\n\n" + narrative
        root.clipboard_clear()
        root.clipboard_append(combined_text)
        show_status_message("Output and narrative copied to clipboard", 5000)
        logging.debug("Copied output and narrative")
    except Exception as e:
        show_status_message(f"Error copying output and narrative: {str(e)}", 10000)
        logging.debug(f"Error copying output and narrative: {str(e)}")

def copy_sitrep():
    try:
        sitrep_text = output_text.get("1.0", tk.END).strip()
        if not sitrep_text:
            show_status_message("No Situation Report available to copy", 10000)
            logging.debug("No Situation Report available")
            return
        root.clipboard_clear()
        root.clipboard_append(sitrep_text)
        show_status_message("Situation Report copied to clipboard", 5000)
        logging.debug("Copied Situation Report")
    except Exception as e:
        show_status_message(f"Error copying Situation Report: {str(e)}", 10000)
        logging.debug(f"Error copying Situation Report: {str(e)}")

def toggle_narrative():
    if narrative_var.get():
        narrative_label.pack(fill=tk.X, padx=10, pady=2)
        narrative_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
    else:
        narrative_frame.pack_forget()
        narrative_label.pack_forget()
    if 'root' in globals():
        globals()['root'].update()

def paste_into_decode(event=None):
    try:
        clipboard = root.clipboard_get()
        decode_entry.delete(0, tk.END)
        decode_entry.insert(0, clipboard)
        decode_code()
        return "break"
    except tk.TclError:
        show_status_message("Clipboard is empty or invalid", 5000)
        return "break"

def on_field_change(*args):
    if not positions:
        show_status_message("No event list loaded", 10000)
        logging.warning("No positions data loaded")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.config(state="disabled")
        return
    list_id = None
    for lid, fname in emergency_list_mapping.items():
        if list_var.get() == fname:
            list_id = lid
            break
    if not list_id or list_var.get() == "Select Emergency List":
        show_status_message("No event list selected", 10000)
        logging.warning("No valid list_id or Select Emergency List selected")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.config(state="disabled")
        return
    emergency_val = emergency_var.get()
    status_val = status_var.get()
    primary_val = primary_var.get()
    secondary_val = secondary_var.get()
    severity_val = severity_var.get()
    if any(val == "Select Code" for val in [emergency_val, status_val, primary_val, secondary_val, severity_val]):
        logging.debug("Incomplete selection")
        return
    try:
        emergency_code = emergency_val.split("-")[0]
        status_code = status_val.split("-")[0]
        primary_code = primary_val.split("-")[0]
        secondary_code = secondary_val.split("-")[0]
        severity_code = severity_val.split("-")[0]
        emergency_data = None
        emergency_group = "Unknown"
        has_groups = any(k.startswith("***") for k in positions["emergency_type"].keys())
        if has_groups:
            for group, sub_emergencies in positions["emergency_type"].items():
                if group.startswith("***") and emergency_code in sub_emergencies:
                    emergency_data = sub_emergencies[emergency_code]
                    emergency_group = group
                    break
                elif group == emergency_code:
                    emergency_data = positions["emergency_type"][emergency_code]
                    emergency_group = "Unknown"
                    break
        else:
            if emergency_code in positions["emergency_type"]:
                emergency_data = positions["emergency_type"][emergency_code]
                emergency_group = "Unknown"
        if not emergency_data:
            show_status_message(f"Invalid Event Type code: {emergency_code}", 10000)
            logging.warning(f"Invalid Event Type code: {emergency_code}")
            return
        impacts = positions.get("shared_impacts", {})
        valid_primary_code = False
        primary_impact_name = "Unknown"
        impact_group = "Unknown"
        if isinstance(impacts, dict):
            if primary_code in impacts and isinstance(impacts[primary_code], dict) and "name" in impacts[primary_code]:
                valid_primary_code = True
                primary_impact_name = impacts[primary_code]["name"]
                impact_group = impacts[primary_code].get("group", "Unknown")
            else:
                for group, sub_impacts in impacts.items():
                    if isinstance(sub_impacts, dict) and "items" in sub_impacts:
                        if primary_code in sub_impacts["items"] and primary_code in impacts:
                            valid_primary_code = True
                            primary_impact_name = impacts[primary_code]["name"]
                            impact_group = group
                            break
        if not valid_primary_code:
            show_status_message(f"Invalid Impact code: {primary_code}", 10000)
            logging.warning(f"Invalid Impact code: {primary_code}")
            return
        if secondary_code not in positions["public_reaction"]:
            show_status_message(f"Invalid Response code: {secondary_code}", 10000)
            logging.warning(f"Invalid Response code: {secondary_code}")
            return
        #if secondary_code == "Y":
        #    show_status_message("Invalid Response code: Y is reserved", 10000)
        #    logging.warning("Invalid Response code: Y is reserved")
        #    return
        station_response = positions.get("station_response", {})
        valid_severity_code = False
        severity_name = "Unknown"
        # Check standalone keys first (e.g., 'A' for Station Status)
        if severity_code in station_response and isinstance(station_response[severity_code], dict):
            valid_severity_code = True
            severity_name = station_response[severity_code].get("name", "Unknown")
        else:
            # Check groups for other codes
            for group, sub_response in station_response.items():
                if isinstance(sub_response, dict) and "items" in sub_response:
                    if severity_code in sub_response["items"]:
                        valid_severity_code = True
                        if severity_code in station_response and isinstance(station_response[severity_code], dict):
                            severity_name = station_response[severity_code].get("name", "Unknown")
                        break
                elif severity_code in sub_response:
                    valid_severity_code = True
                    severity_name = sub_response[severity_code].get("name", "Unknown")
                    break
        if not valid_severity_code:
            logging.warning(f"Invalid Station Status code: {severity_code}")
            show_status_message(f"Invalid Station Status code: {severity_code}", 10000)
            return f"Invalid Station Status code: {severity_code}"
        if status_code not in positions["status_codes"]:
            show_status_message(f"Invalid Status/Target code: {status_code}", 10000)
            logging.warning(f"Invalid Status/Target code: {status_code}")
            return
        code = f"{list_id}{emergency_code}{status_code}{primary_code}{secondary_code}{severity_code}"
        description_parts = [
            emergency_data["name"] if emergency_code != "A" else None,
            primary_impact_name if primary_code != "A" else None,
            positions["public_reaction"][secondary_code]["name"] if secondary_code != "A" else None,
            severity_name if severity_code != "A" else None,
            positions["status_codes"][status_code]["name"] if status_code in positions["status_codes"] else "Unknown"
        ]
        description = generate_description(description_parts, severity_code, list_id, code, status_code, secondary_code, emergency_group, impact_group)
        narrative = generate_narrative(description_parts, emergency_code, primary_code, secondary_code, severity_code, status_code, code, list_id)
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, description)
        output_lines = description.split('\n')
        for i, line in enumerate(output_lines):
            if line.startswith("Brevity Code:"):
                output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len('Brevity Code:')}")
                file_start = line.find("File:")
                if file_start != -1:
                    output_text.tag_add("bold", f"{i+1}.{file_start}", f"{i+1}.{file_start + len('File:')}")
            elif line.startswith(positions.get("gui_titles", {}).get('emergency', 'Event:')):
                output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('emergency', 'Event:'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('status', 'Status or Target:')):
                output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('status', 'Status or Target:'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('primary', 'Impact:')):
                output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('primary', 'Impact:'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('secondary', 'Response:')):
                output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('secondary', 'Response:'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('severity', 'Station Status:')):
                output_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('severity', 'Station Status:'))}")
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.insert(tk.END, f"{narrative}")
        narrative_lines = narrative.split('\n')
        for i, line in enumerate(narrative_lines):
            if line.startswith("Brevity Code:"):
                narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len('Brevity Code:')}")
            elif line.startswith(positions.get("gui_titles", {}).get('emergency', 'Event:').rstrip(':')):
                narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('emergency', 'Event:').rstrip(':'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('status', 'Status or Target:').rstrip(':')):
                narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('status', 'Status or Target:').rstrip(':'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('primary', 'Impact:').rstrip(':')):
                narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('primary', 'Impact:').rstrip(':'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('secondary', 'Response:').rstrip(':')):
                narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('secondary', 'Response:').rstrip(':'))}")
            elif line.startswith(positions.get("gui_titles", {}).get('severity', 'Station Status:').rstrip(':')):
                narrative_text.tag_add("bold", f"{i+1}.0", f"{i+1}.{len(positions.get('gui_titles', {}).get('severity', 'Station Status:').rstrip(':'))}")
        narrative_text.config(state="disabled")
        show_status_message("Brevity code generated", 5000)
    except Exception as e:
        logging.error(f"Error generating code: {str(e)}")
        output_text.delete("1.0", tk.END)
        narrative_text.config(state="normal")
        narrative_text.delete("1.0", tk.END)
        narrative_text.config(state="disabled")
        return f"Error decoding code: {str(e)}"

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.title("Brevity1.0 by KD9DSS")
        root.geometry("700x700")
        root.configure(bg="#DCDCDC")
        root.attributes("-topmost", False)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TMenuButton.TMenubutton", font=("Arial", 10, "bold"), background="#28a745", foreground="white", padding=4, borderwidth=3, relief="solid", width=20)
        style.map("TMenuButton.TMenubutton", background=[("active", "#34c759")], foreground=[("active", "white"), ("disabled", "#666666")])
        style.configure("TActionButton.TButton", font=("Arial", 10, "bold"), background="#28a745", foreground="black", padding=4, borderwidth=3, relief="solid", width=20)
        style.map("TActionButton.TButton", background=[("active", "#34c759"), ("disabled", "#CCCCCC")], foreground=[("disabled", "#666666")])
        style.configure("TLabel", font=("Arial", 10, "bold"), background="#DCDCDC", foreground="black")
        top_action_frame_outer = tk.Frame(root, bg="#DCDCDC")
        top_action_frame_outer.pack(fill=tk.X, padx=10, pady=5)
        decode_subframe = tk.Frame(top_action_frame_outer, bg="#DCDCDC")
        decode_subframe.pack(anchor="center")
        label_decode = ttk.Label(decode_subframe, text="Enter Brevity Code:")
        label_decode.pack(anchor="center")
        decode_inner_frame = tk.Frame(decode_subframe, bg="#DCDCDC")
        decode_inner_frame.pack(anchor="center", pady=2)
        validate_cmd = root.register(validate_code_input)
        decode_entry = tk.Entry(decode_inner_frame, width=14, font=("Arial", 10), bg="#F8F7F2", fg="black", insertbackground="black", relief="solid", borderwidth=1, validate="key", validatecommand=(validate_cmd, "%P"), state="normal")
        decode_entry.pack(side=tk.LEFT, padx=5)
        decode_button = ttk.Button(decode_inner_frame, text="Decode", command=decode_code, style="TActionButton.TButton")
        decode_button.pack(side=tk.LEFT, padx=5)
        decode_entry.focus()
        decode_entry.bind("<Control-v>", paste_into_decode)
        #decode_entry.bind("<Return>", lambda event: decode_code() or "break")
        decode_entry.bind("<Return>", lambda event: decode_code(event, decode_entry, output_text, narrative_text, list_var, emergency_var, status_var, primary_var, secondary_var, severity_var) or "break")
        decode_entry.bind("<Button-3>", lambda event: paste_menu.post(event.x_root, event.y_root))
        paste_menu = tk.Menu(decode_entry, tearoff=0)
        paste_menu.add_command(label="Paste", command=paste_into_decode)
        input_frame = tk.Frame(root, bg="#DCDCDC", bd=2, relief="groove", highlightbackground="#CCCCCC", highlightthickness=1)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        row1_frame = tk.Frame(input_frame, bg="#DCDCDC")
        row1_frame.pack(fill=tk.X, pady=2)
        select_list_subframe = tk.Frame(row1_frame, bg="#DCDCDC")
        select_list_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        label_select = ttk.Label(select_list_subframe, text="1. Select List:")
        label_select.pack(anchor="center")
        list_var = tk.StringVar(value="Select Emergency List")
        list_var.trace("w", lambda *args: load_selected_file(list_var.get()[0]) if list_var.get() != "Select Emergency List" and list_var.get() in emergency_list_mapping.values() else None)
        list_menu = tk.Menu(root, tearoff=0, font=("Arial", 10), bg="#F8F7F2", fg="black")
        max_length = 100
        emergency_list_mapping = get_json_files()
        for list_id, filename in sorted(emergency_list_mapping.items()):
            padded_filename = filename.ljust(max_length)
            list_menu.add_command(label=padded_filename, command=lambda f=filename: [list_var.set(f), load_selected_file(f[0])])
        list_menu.add_command(label="Select Emergency List".ljust(max_length), command=lambda: list_var.set("Select Emergency List"))
        list_button = ttk.Menubutton(select_list_subframe, textvariable=list_var, menu=list_menu, style="TMenuButton.TMenubutton")
        list_button.pack(anchor="center")
        emergency_subframe = tk.Frame(row1_frame, bg="#DCDCDC")
        emergency_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        label_emergency = ttk.Label(emergency_subframe, text="2. Event:")
        label_emergency.pack(anchor="center")
        emergency_var = tk.StringVar(value="Select Code")
        emergency_var.trace("w", lambda *args: on_field_change())
        emergency_menu = tk.Menu(root, tearoff=0, font=("Arial", 10), bg="#F8F7F2", fg="black")
        emergency_menu.add_command(label="Select Code".ljust(max_length), command=lambda: emergency_var.set("Select Code"))
        emergency_button = ttk.Menubutton(emergency_subframe, textvariable=emergency_var, menu=emergency_menu, style="TMenuButton.TMenubutton")
        emergency_button.pack(anchor="center")
        status_subframe = tk.Frame(row1_frame, bg="#DCDCDC")
        status_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        label_status = ttk.Label(status_subframe, text="3. Status/Target:")
        label_status.pack(anchor="center")
        status_var = tk.StringVar(value="Select Code")
        status_var.trace("w", lambda *args: on_field_change())
        status_menu = tk.Menu(root, tearoff=0, font=("Arial", 10), bg="#F8F7F2", fg="black")
        status_menu.add_command(label="Select Code".ljust(max_length), command=lambda: status_var.set("Select Code"))
        status_button = ttk.Menubutton(status_subframe, textvariable=status_var, menu=status_menu, style="TMenuButton.TMenubutton")
        status_button.pack(anchor="center")
        row2_frame = tk.Frame(input_frame, bg="#DCDCDC")
        row2_frame.pack(fill=tk.X, pady=2)
        primary_subframe = tk.Frame(row2_frame, bg="#DCDCDC")
        primary_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        label_primary = ttk.Label(primary_subframe, text="4. Impact:")
        label_primary.pack(anchor="center")
        primary_var = tk.StringVar(value="Select Code")
        primary_var.trace("w", lambda *args: on_field_change())
        primary_menu = tk.Menu(root, tearoff=0, font=("Arial", 10), bg="#F8F7F2", fg="black")
        primary_menu.add_command(label="Select Code".ljust(max_length), command=lambda: primary_var.set("Select Code"))
        primary_button = ttk.Menubutton(primary_subframe, textvariable=primary_var, menu=primary_menu, style="TMenuButton.TMenubutton")
        primary_button.pack(anchor="center")
        secondary_subframe = tk.Frame(row2_frame, bg="#DCDCDC")
        secondary_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        label_secondary = ttk.Label(secondary_subframe, text="5. Response:")
        label_secondary.pack(anchor="center")
        secondary_var = tk.StringVar(value="Select Code")
        secondary_var.trace("w", lambda *args: on_field_change())
        secondary_menu = tk.Menu(root, tearoff=0, font=("Arial", 10), bg="#F8F7F2", fg="black")
        secondary_menu.add_command(label="Select Code".ljust(max_length), command=lambda: secondary_var.set("Select Code"))
        secondary_button = ttk.Menubutton(secondary_subframe, textvariable=secondary_var, menu=secondary_menu, style="TMenuButton.TMenubutton")
        secondary_button.pack(anchor="center")
        severity_subframe = tk.Frame(row2_frame, bg="#DCDCDC")
        severity_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        label_severity = ttk.Label(severity_subframe, text="6. Station/Location:")
        label_severity.pack(anchor="center")
        severity_var = tk.StringVar(value="Select Code")
        severity_var.trace("w", lambda *args: on_field_change())
        severity_menu = tk.Menu(root, tearoff=0, font=("Arial", 10), bg="#F8F7F2", fg="black")
        severity_menu.add_command(label="Select Code".ljust(max_length), command=lambda: severity_var.set("Select Code"))
        severity_button = ttk.Menubutton(severity_subframe, textvariable=severity_var, menu=severity_menu, style="TMenuButton.TMenubutton")
        severity_button.pack(anchor="center")
        bottom_action_frame_outer = tk.Frame(root, bg="#DCDCDC")
        bottom_action_frame_outer.pack(fill=tk.X, padx=10, pady=5)
        bottom_action_subframe = tk.Frame(bottom_action_frame_outer, bg="#DCDCDC")
        bottom_action_subframe.pack(fill=tk.X)
        clear_button_subframe = tk.Frame(bottom_action_subframe, bg="#DCDCDC")
        clear_button_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        clear_button = ttk.Button(clear_button_subframe, text="Clear", command=clear_fields, style="TActionButton.TButton")
        clear_button.pack(anchor="center")
        copy_code_button_subframe = tk.Frame(bottom_action_subframe, bg="#DCDCDC")
        copy_code_button_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        copy_code_button = ttk.Button(copy_code_button_subframe, text="Copy Code", command=copy_code_text, style="TActionButton.TButton")
        copy_code_button.pack(anchor="center")
        copy_sitrep_button_subframe = tk.Frame(bottom_action_subframe, bg="#DCDCDC")
        copy_sitrep_button_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        copy_sitrep_button = ttk.Button(copy_sitrep_button_subframe, text="Copy Report", command=copy_sitrep, style="TActionButton.TButton")
        copy_sitrep_button.pack(anchor="center")
        copy_all_button_subframe = tk.Frame(bottom_action_subframe, bg="#DCDCDC")
        copy_all_button_subframe.pack(side=tk.LEFT, padx=10, expand=True)
        copy_all_button = ttk.Button(copy_all_button_subframe, text="Copy All", command=copy_all, style="TActionButton.TButton")
        copy_all_button.pack(anchor="center")
        output_label_frame = tk.Frame(root, bg="#DCDCDC")
        output_label_frame.pack(fill=tk.X, padx=10, pady=2)
        narrative_var = tk.BooleanVar(value=False)
        narrative_check = tk.Checkbutton(output_label_frame, text="View Detailed Narrative", variable=narrative_var, command=toggle_narrative, font=("Arial", 10, "bold"), bg="#DCDCDC", fg="black")
        narrative_check.pack(side=tk.RIGHT, padx=20)
        output_label = ttk.Label(output_label_frame, text="Brevity Report", font=("Arial", 10, "bold"), background="#DCDCDC")
        output_label.pack(side=tk.LEFT, padx=10)
        output_frame = tk.Frame(root, bg="#DCDCDC", bd=2, relief="groove", highlightbackground="#CCCCCC", highlightthickness=1)
        output_frame.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        output_scrollbar = tk.Scrollbar(output_frame)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        output_text = tk.Text(output_frame, height=7, font=("Arial", 12), bg="#F8F7F2", fg="black", yscrollcommand=output_scrollbar.set, wrap=tk.WORD, relief="solid", borderwidth=1)
        output_text.pack(fill=tk.BOTH, expand=True)
        output_scrollbar.config(command=output_text.yview)
        output_text.tag_configure("bold", font=("Arial", 12, "bold"))
        narrative_label = ttk.Label(root, text="Detailed Narrative", font=("Arial", 10, "bold"), background="#DCDCDC")
        narrative_frame = tk.Frame(root, bg="#DCDCDC", bd=2, relief="groove", highlightbackground="#CCCCCC", highlightthickness=1)
        narrative_scrollbar = tk.Scrollbar(narrative_frame)
        narrative_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        narrative_text = tk.Text(narrative_frame, height=10, font=("Arial", 12), bg="#F8F7F2", fg="black", yscrollcommand=narrative_scrollbar.set, wrap=tk.WORD, relief="solid", borderwidth=1, state="disabled")
        narrative_text.pack(fill=tk.BOTH, expand=True)
        narrative_scrollbar.config(command=narrative_text.yview)
        narrative_text.tag_configure("bold", font=("Arial", 12, "bold"))
        toggle_narrative()
        status_bar = tk.Text(root, height=1, font=("Arial", 10), bg="#DCDCDC", fg="black", relief="flat", state="disabled")
        status_bar.pack(fill=tk.X, padx=10, pady=5)
        if emergency_list_mapping:
            first_list_id = sorted(emergency_list_mapping.keys())[0]
            load_selected_file(first_list_id)
        else:
            show_status_message("No valid JSON files found", 10000)
            logging.warning("No valid JSON files found")
        root.mainloop()
    except Exception as e:
        logging.error(f"Exception in main: {str(e)}")
        traceback.print_exc()