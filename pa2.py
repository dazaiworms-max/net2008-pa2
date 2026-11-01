# Latasha Luo, 041198293

import os
import sys
import yaml
import json
import xml.etree.ElementTree as ET

class BadFile(Exception):
    """Raised when an invalid file is passed into main"""

class Device:
    """A network device in the inventory"""
    def __init__(self, device):
        if device.get("id"):
            self.id = device.get("id")
        else:
            self.id = None

        self.role = device.get("role")
        self.os = device.get("os")
        self.owner = ""

        if device.find("owner") is not None and device.find("owner").text:
            self.owner = device.find("owner").text

        self.interfaces = []
        self.up = 0
        self.down = 0
        self.other = 0

        for interface in device.findall("interface"):
            status = interface.get("status")
            self.interfaces.append({"name": interface.get("name"), "status": status})

            if status == "up":
                self.up +=1
            elif status == "down":
                self.down +=1
            else:
                self.other +=1

    def has_id(self):
        """Checks if device has an id"""
        if self.id == None:
            return False
        else:
            return True

def parse_inventory(xml_file):
    """Checks the validity of the XML file provided and parses its inventory"""
    if not os.path.exists(xml_file):
        sys.exit(f"XML file {xml_file} does not exist")

    # Is the file valid?
    try:
        with open(xml_file, "r", encoding="utf-8") as f:
            inventory_tree = ET.parse(f)
    except Exception as e:
        raise BadFile(f"Error reading XML inventory file {xml_file}: {e}")

    # Parse and store inventory
    inventory_root = inventory_tree.getroot()

    if inventory_root.get("site"):
        site = inventory_root.get("site")
    else:
        site = None

    devices = []
    skipped = 0

    for device in inventory_root.findall("device"):
        device_in_inventory = Device(device)
        if device_in_inventory.has_id():
            devices.append(device_in_inventory)
        else:
            skipped +=1

    return site, devices, skipped

def load_policy(yaml_file):
    """Read in the YAML policy file"""
    if not os.path.exists(yaml_file):
        print(f"YAML file {yaml_file} does not exist")
        sys.exit(1)

    # Checking if the file is valid
    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            policy_mapping = yaml.safe_load(f)
    except Exception as e:
        raise BadFile(f"Error rading YAML policy file {yaml_file}: {e}")

    if not isinstance(policy_mapping, dict):
        print(f"YAML file {yaml_file} does not have valid mapping")
        sys.exit(1)

    return policy_mapping

def parse_os(os_string):
    try:
        return tuple(int(part) for part in os_string.split("."))
    except (ValueError, AttributeError):
        return (0, )

def check_min_os(device, policy_mapping):
    min_os_policy = policy_mapping.get("min_os")

    if not isinstance(min_os_policy, dict):
        print (f"YAML policy file is not a valid mapping")
        sys.exit(1)

    required_os = min_os_policy.get(device.role)
    if required_os == None:
        return None

    if parse_os(device.os) < parse_os(required_os):
        return {
            "device": device.id,
            "type": "os_outdated",
            "found": device.os,
            "required": required_os
        }

    return None

def make_report(report):
    """Generate a JSON audit file report"""
    try:
        with open("audit.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
    except (TypeError, OSError) as e:
        print(f"JSON file could not be written: {e}")
        sys.exit(1)

    print(f"Audit.json has been created")
    sys.exit(0)

def main():
    if len(sys.argv) != 3:
        print(f"usage: python pa2.py DEVICES.xml POLICY.yaml")
        sys.exit(2)

    xml_file = sys.argv[1]
    yaml_file = sys.argv[2]

    empty_report = {
        "site": None,
	    "total_devices": 0,
	    "skipped_devices": 0,
	    "roles": None,
	    "interfaces": {"up": 0, "down": 0, "other": 0},
        "violations": None,
        "compliant": None
    }

    if os.path.getsize(xml_file) == 0:
        make_report(empty_report)

    try:
        site, devices, skipped = parse_inventory(xml_file)
    except BadFile as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        policy = load_policy(yaml_file)
    except BadFile as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Count to tally for report
    roles = {}
    all_up = 0
    all_down = 0
    all_other = 0
    violations = []
    compliance_check = True
    compliant = []

    for device in devices:
        compliance_check = True
        roles[device.role] = roles.get(device.role, 0) +1
        all_up += device.up
        all_down += device.down
        all_other += device.other
        
        os_checked = check_min_os(device, policy)
        if os_checked != None:
            violations.append(os_checked)
            compliance_check = False

        if compliance_check:
            compliant.append(device.id)

    report = {
        "site": site,
	    "total_devices": len(devices),
	    "skipped_devices": skipped,
	    "roles": roles,
	    "interfaces": {"up": all_up, "down": all_down, "other": all_other},
        "violations": violations,
        "compliant": compliant
    }

    make_report(report)

if __name__ == "__main__":
    main()