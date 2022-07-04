import shutil
import sys
import time

from lxml.etree import XMLParser, indent, parse, register_namespace, tostring

if __name__ == "__main__":

    # Console output:
    print("\n\n%s\nCPACS Syntax formatting" % ("=" * 70))

    def printout(text):
        print("\n> %s ..." % (text))

    # ======================================================
    # Specify input/output file names:
    #   1) Input schema file
    #   2) Output schema file (optional; backup file will be created)
    #
    if len(sys.argv) >= 2:
        schema_file = sys.argv[1]
        if len(sys.argv) >= 3:
            schema_file_new = sys.argv[2]
        else:
            shutil.copy(schema_file, "backup_%s.xsd" % time.strftime("%Y%m%d_%H%M%S"))
            schema_file_new = schema_file
    else:
        print(
            "Please specify the following arguments:"
            + " (1) Input schema file (obligatory) and"
            + " (2) Output schema file (optional).\n"
            + " If not output file is defined, the input file will be overwritten and a"
            + " backup file will be created"
        )
        exit()

    parser = XMLParser(strip_cdata=False)
    tree = parse(schema_file, parser=parser)
    root = tree.getroot()

    # ======================================================
    #  Set name-spaces
    #
    printout("Set namespaces")

    namespaces = {
        "xsd": "http://www.w3.org/2001/XMLSchema",
        "ddue": "http://ddue.schemas.microsoft.com/authoring/2003/5",
        "sd": "http://schemas.xsddoc.codeplex.com/schemaDoc/2009/3",
        "xlink": "http://www.w3.org/1999/xlink",
    }
    for key in namespaces.keys():
        register_namespace(key, namespaces[key])

    # ======================================================
    #  Sort types
    #    Sorts types in alphabetic order, but puts cpacs
    #    root element and cpacsType in front. Comments at the
    #    highest hierarchy level must be deleted as it is not
    #    clear from the schema where to place it. Furthermore,
    #    the license text should be imported from a separate file
    #    to ensure easy and consistent maintenance of the licence
    #    agreement.
    #
    printout("Alphabetic sorting")

    cpacs_element = [el for el in root if el.get("name") == "cpacs"][-1]
    cpacs_type = [el for el in root if el.get("name") == "cpacsType"][-1]
    root.remove(cpacs_element)
    root.remove(cpacs_type)
    for comment in [el for el in root if not el.get("name")]:
        root.remove(comment)

    root[:] = sorted(root, key=lambda elem: elem.get("name").lower())

    root.insert(0, cpacs_element)
    root.insert(1, cpacs_type)

    # ======================================================
    # Naming conventions
    #
    printout("Check for naming conventions")

    for elem in root:
        name = elem.get("name")
        new_name = None

        # Lowercase first letter:
        if name[0].isupper():
            new_name = name[0].lower() + name[1:]

        # Name ends with "Type"
        if name[-4:] != "Type" and name != "cpacs":
            new_name = name + "Type"

        # Apply new name and inform user about changes:
        if new_name != None:
            print(' Renaming "%s" to "%s".' % (name, new_name))
            elem.set("name", new_name)
            # Elements using this type:
            for t in set([el for el in list(root.iter()) if el.get("type") == name]):
                t.attrib["type"] = new_name
            # Derived types (restritions/extensions):
            for t in set([el for el in list(root.iter()) if el.get("base") == name]):
                t.attrib["base"] = new_name

    # ======================================================
    # Arranging attributes
    #    Affects xsd:elements, xsd:choice and xsd:attribute
    #
    printout("Arrange attributes")

    def elemType(elem):
        try:
            return elem.tag.split("}")[-1]
        except:
            return None

    attributes_order = {
        key: i
        for i, key in enumerate(
            ["name", "minOccurs", "maxOccurs", "default", "use", "fixed", "type"]
        )
    }
    for elem in root:
        childs = [
            child
            for child in list(elem.iter())
            if elemType(child) == "element"
            or elemType(child) == "choice"
            or elemType(child) == "attribute"
        ]
        for child in childs:
            attributes = [
                {"name": key, "value": child.attrib[key]} for key in child.keys()
            ]
            attributes_new = sorted(
                attributes, key=lambda d: attributes_order[d["name"]]
            )
            for attribute in attributes:
                del child.attrib[attribute["name"]]
            for attribute in attributes_new:
                if not (
                    (
                        attribute["name"] == "minOccurs"
                        or attribute["name"] == "maxOccurs"
                    )
                    and attribute["value"] == "1"
                ):
                    child.attrib[attribute["name"]] = attribute["value"]

    # ======================================================
    # Remove unused types
    #
    printout("Removing unused types")

    def unused_types():
        types_exist = [el for el in root if el.get("name") != "cpacs"]
        types_used = set(
            [el.attrib["type"] for el in list(root.iter()) if "type" in el.keys()]
            + [el.attrib["base"] for el in list(root.iter()) if "base" in el.keys()]
        )
        return [t for t in types_exist if not t.attrib["name"] in types_used]

    types_unused = unused_types()
    while len(types_unused) > 0:
        for t in types_unused:
            print(' Removing type "%s"' % t.attrib["name"])
            root.remove(t)
        types_unused = unused_types()

    # ======================================================
    # Pretty print
    #
    printout("Pretty print")

    indent(root, space=" " * 4)

    # Empty line between types:
    for elem in root:
        elem.tail = "\n\n"

    # Convert to string to allow for manual string operations:
    root_str = tostring(root).decode("utf-8")

    # Replace tab with empty spaces:
    root_str = root_str.replace("\t", " " * 4)

    # Remove trailing empty spaces:
    root_str = "".join([line.rstrip() + "\n" for line in root_str.splitlines()])

    # Fix indent of complexType:
    root_str = root_str.replace("<xsd:complexType", "    <xsd:complexType")

    # Add encoding and license information:
    with open("license.txt", "r") as f:
        license = f.read()
        f.close()
    root_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + license + root_str

    # ======================================================
    # Output schema file
    #
    printout('Write schema to "%s"' % schema_file_new)
    with open(schema_file_new, "w") as f:
        f.writelines(root_str)
        f.close()
