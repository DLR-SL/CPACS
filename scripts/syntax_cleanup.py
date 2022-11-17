import argparse
import logging
import os
import shutil
import sys
import time

from lxml.etree import XMLParser, indent, parse, register_namespace, tostring

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


def printout(text):
    log.debug("\n> %s ..." % text)


class CPACSXSDSyntaxCleaner(object):
    NAMESPACES = {
        "xsd": "https://www.w3.org/2001/XMLSchema",
        "ddue": "http://ddue.schemas.microsoft.com/authoring/2003/5",
        "sd": "http://schemas.xsddoc.codeplex.com/schemaDoc/2009/3",
        "xlink": "https://www.w3.org/1999/xlink",
    }
    LICENSE_FILE = "license.txt"

    def __init__(self, schema_file, schema_file_new):
        self.schema_file = schema_file
        if schema_file_new is None:
            shutil.copy(schema_file, "backup_%s.xsd" % time.strftime("%Y%m%d_%H%M%S"))
            self.schema_file_new = schema_file
        else:
            self.schema_file_new = schema_file_new

    def get_root_tree(self):
        parser = XMLParser(strip_cdata=False)
        tree = parse(self.schema_file, parser=parser)
        root = tree.getroot()
        return root

    def set_namespaces(self):
        """
        Set name-spaces
        """
        printout("Set namespaces")

        for k, v in self.NAMESPACES.items():
            register_namespace(k, v)

    @staticmethod
    def sort_alphabetic(root):
        """
        Sort types
          Sorts types in alphabetic order, but puts cpacs
          root element and cpacsType in front. Comments at the
          highest hierarchy level must be deleted as it is not
          clear from the schema where to place it. Furthermore,
          the license text should be imported from a separate file
          to ensure easy and consistent maintenance of the licence
          agreement.
        """
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

        return root

    @staticmethod
    def check_naming_conventions(root):
        """
        Naming conventions
        """
        printout("Check for naming conventions")

        for elem in root:
            name = elem.get("name")
            new_name = None

            # Lowercase first letter:
            if name[0].isupper():
                new_name = name[0].lower() + name[1:]

            # Name ends with "Type":
            if name[-4:] != "Type" and name != "cpacs":
                new_name = name + "Type"

            # Apply new name and inform user about changes:
            if new_name is not None:
                log.debug(' Renaming "%s" to "%s".' % (name, new_name))
                elem.set("name", new_name)
                # Elements using this type:
                for t in set(
                    [el for el in list(root.iter()) if el.get("type") == name]
                ):
                    t.attrib["type"] = new_name
                # Derived types (restritions/extensions):
                for t in set(
                    [el for el in list(root.iter()) if el.get("base") == name]
                ):
                    t.attrib["base"] = new_name
        return root

    @staticmethod
    def get_elem_type(elem):
        try:
            return elem.tag.split("}")[-1]
        except Exception as e:
            log.debug(e)
            return None

    @classmethod
    def arrange_attributes(cls, root):
        """
        Arranging attributes
           Affects xsd:elements, xsd:choice and xsd:attribute
        """
        printout("Arrange attributes")

        attributes_order = {
            key: i
            for i, key in enumerate(
                ["name", "minOccurs", "maxOccurs", "default", "use", "fixed", "type"]
            )
        }
        for elem in root:
            children = [
                child
                for child in list(elem.iter())
                if cls.get_elem_type(child) in {"element", "choice", "attribute"}
            ]
            for child in children:
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
                        (attribute["name"] in {"minOccurs", "maxOccurs"})
                        and attribute["value"] == "1"
                    ):
                        child.attrib[attribute["name"]] = attribute["value"]
        return root

    @staticmethod
    def find_unused_types(root):
        types_exist = [el for el in root if el.get("name") != "cpacs"]
        types_used = set(
            [el.attrib["type"] for el in list(root.iter()) if "type" in el.keys()]
            + [el.attrib["base"] for el in list(root.iter()) if "base" in el.keys()]
        )
        return [t for t in types_exist if not t.attrib["name"] in types_used]

    @classmethod
    def remove_unused_types(cls, root):
        """
        Remove unused types
        """
        printout("Removing unused types")

        while len(types_unused := cls.find_unused_types(root)):
            for t in types_unused:
                log.debug(' Removing type "%s"' % t.attrib["name"])
                root.remove(t)
        return root

    def get_cleaned_root_tree(self):
        root = self.get_root_tree()
        self.set_namespaces()
        root = self.sort_alphabetic(root)
        root = self.check_naming_conventions(root)
        root = self.arrange_attributes(root)
        root = self.remove_unused_types(root)
        return root

    def read_license_information(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        with open(os.path.join(__location__, self.LICENSE_FILE), "r") as f:
            return f.read()

    def pretty_print(self, root):
        """
        Pretty print
        """
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
        cpacs_license = self.read_license_information()
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + cpacs_license + root_str

    def write_cleaned_schema_file(self, root_str):
        """
        Output schema file
        """
        printout('Write schema to "%s"' % self.schema_file_new)
        with open(self.schema_file_new, "w") as f:
            f.writelines(root_str)

    def run(self):
        log.debug("\n\n%s\nCPACS Syntax formatting" % ("=" * 70))

        root = self.get_cleaned_root_tree()
        root_str = self.pretty_print(root)
        self.write_cleaned_schema_file(root_str)


def parse_args():
    """
    Specify input/output file names:
      1) Input schema file
      2) Output schema file (optional; backup file will be created)
    """

    parser = argparse.ArgumentParser(
        prog="syntax_cleanup", description="Syntax cleaner for CPACS XSD Schema"
    )
    parser.add_argument("schema_input", help="Path to input schema file")
    parser.add_argument(
        "schema_output", nargs="?", default=None, help="Path to output schema file"
    )
    parser.add_argument("--log", default="DEBUG")
    args = parser.parse_args()

    log.setLevel(args.log.upper())
    return args.schema_input, args.schema_output


if __name__ == "__main__":
    schema_input, schema_output = parse_args()
    cleaner = CPACSXSDSyntaxCleaner(schema_input, schema_output)
    cleaner.run()
