# Reading and writing tool-specific data with lxml.
#
# Run from the examples/python folder: python toolspecific_lxml.py
# Reads the tool data of ../toolspecific.xml, adds tool data to ../basicWing.xml,
# validates the result and saves it as basicWing_with_tool_data.xml in this folder.
# The rules for tool data are documented in toolspecificType of the CPACS schema;
# the same steps with TiXI are shown in toolspecific_tixi.py.

# %% Step 1: Define the namespace of the tool schema
# lxml addresses elements of a namespace via a mapping of prefixes to namespace
# URIs. The prefix is chosen freely and does not have to match a prefix used in
# the file.
from lxml import etree

TOOL_NAMESPACE = "http://www.cpacs.de/myTool"
NS = {"mt": TOOL_NAMESPACE}

# %% Step 2: Read tool data, using the prefix for every element of the tool data
# CPACS elements such as toolspecific and tool have no namespace and take no prefix.
# Paths passed to find() start below the element they are called on.
cpacs = etree.parse("../toolspecific.xml").getroot()
tool_data = cpacs.find("toolspecific/tool/mt:myToolName", NS)
text = tool_data.findtext("mt:parentElement/mt:childElement1", namespaces=NS)
number = float(tool_data.findtext("mt:parentElement/mt:childElement2", namespaces=NS))
print(text, number)

# %% Step 3: Add a tool element to another dataset
# A dataset without tool data has no toolspecific element yet, so it is created first.
tree = etree.parse("../basicWing.xml")
cpacs = tree.getroot()

toolspecific = cpacs.find("toolspecific")
if toolspecific is None:
    toolspecific = etree.SubElement(cpacs, "toolspecific")

tool = etree.SubElement(toolspecific, "tool")
etree.SubElement(tool, "name").text = "myToolName"
etree.SubElement(tool, "version").text = "1.2.3"

# %% Step 4: Create the tool data with the namespace in every element name
# lxml writes the name of an element in a namespace as "{namespace URI}name".
# nsmap={None: TOOL_NAMESPACE} declares the namespace as default namespace, so that
# the file shows <myToolName xmlns="...">; without it, lxml invents a prefix
# such as ns0.
def tool_element(parent, name, **attributes):
    return etree.SubElement(parent, f"{{{TOOL_NAMESPACE}}}{name}", attributes, nsmap={None: TOOL_NAMESPACE})

tool_data = tool_element(tool, "myToolName", schemaVersion="1.0")
parent_element = tool_element(tool_data, "parentElement")
tool_element(parent_element, "childElement1").text = "stringValue"
tool_element(parent_element, "childElement2").text = "1.0"

# %% Step 5: Validate against the combined schema and save
# The CPACS schema alone rejects tool data whose schema it does not know, see
# ../toolspecific_combined.xsd and section 4 of the toolspecificType documentation.
schema = etree.XMLSchema(etree.parse("../toolspecific_combined.xsd"))
schema.assertValid(tree)
etree.indent(tree, space="    ")
tree.write("basicWing_with_tool_data.xml", xml_declaration=True, encoding="utf-8")
