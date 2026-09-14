# Reading and writing tool-specific data with TiXI.
#
# Run from the examples/python folder: python toolspecific_tixi.py
# Reads the tool data of ../toolspecific.xml, adds tool data to ../basicWing.xml,
# validates the result and saves it as basicWing_with_tool_data.xml in this folder.
# The rules for tool data are documented in toolspecificType of the CPACS schema;
# the same steps with lxml are shown in toolspecific_lxml.py.

# %% Step 1: Define the namespace of the tool schema
from tixi3.tixi3wrapper import Tixi3

TOOL_NAMESPACE = "http://www.cpacs.de/myTool"

# %% Step 2: Open the dataset and register the namespace under a prefix
# TiXI finds elements of the tool data only via a registered prefix. The prefix is
# chosen freely and does not have to match a prefix used in the file.
# registerNamespacesFromDocument() does not help, because tool data usually
# declares its namespace without a prefix.
tixi = Tixi3()
tixi.open("../toolspecific.xml")
tixi.registerNamespace(TOOL_NAMESPACE, "mt")

# %% Step 3: Read tool data, using the prefix for every element of the tool data
# CPACS elements such as toolspecific and tool have no namespace and take no prefix.
tool_data = "/cpacs/toolspecific/tool/mt:myToolName"
text = tixi.getTextElement(tool_data + "/mt:parentElement/mt:childElement1")
number = tixi.getDoubleElement(tool_data + "/mt:parentElement/mt:childElement2")
print(text, number)
tixi.close()

# %% Step 4: Add a tool element to another dataset
tixi = Tixi3()
tixi.open("../basicWing.xml")
tixi.registerNamespace(TOOL_NAMESPACE, "mt")

if not tixi.checkElement("/cpacs/toolspecific"):
    tixi.createElement("/cpacs", "toolspecific")

tixi.createElement("/cpacs/toolspecific", "tool")
tool = "/cpacs/toolspecific/tool[last()]"
tixi.addTextElement(tool, "name", "myToolName")
tixi.addTextElement(tool, "version", "1.2.3")

# %% Step 5: Create the tool data with the prefix in every element name
# Without the prefix ("myToolName" instead of "mt:myToolName"), TiXI (tested with
# 3.3.0 and 3.3.2) creates the element in a wrong namespace as soon as the dataset
# declares any prefixed namespace, which practically every CPACS dataset does with
# xmlns:xsi. No error is reported, but the dataset is invalid.
tixi.createElementNS(tool, "mt:myToolName", TOOL_NAMESPACE)
tool_data = tool + "/mt:myToolName"
tixi.addTextAttribute(tool_data, "schemaVersion", "1.0")
tixi.createElementNS(tool_data, "mt:parentElement", TOOL_NAMESPACE)
tixi.addTextElementNS(tool_data + "/mt:parentElement", "mt:childElement1", TOOL_NAMESPACE, "stringValue")
tixi.addDoubleElementNS(tool_data + "/mt:parentElement", "mt:childElement2", TOOL_NAMESPACE, 1.0, "%g")

# %% Step 6: Validate against the combined schema and save
tixi.schemaValidateFromFile("../toolspecific_combined.xsd")
tixi.save("basicWing_with_tool_data.xml")
tixi.close()
