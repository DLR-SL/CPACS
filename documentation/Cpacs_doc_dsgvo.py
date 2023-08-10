import os
import re

# ==============================================================================================
#   DSGVO
#       This script modifies the CPACS documentation so that it contains a dsgvo-conform footer
# ==============================================================================================

def replace_page_footer(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    pattern = r'<div id="pageFooter" class="pageFooter"><p>.*?</p>'
    replacement = '''
<div id="pageFooter" class="pageFooter"><p>
    &copy; 2023 <a href="https://www.DLR.de">Deutsches Zentrum für Luft- und Raumfahrt e.V.</a>&nbsp;&nbsp;&nbsp;
    <a href="https://www.dlr.de/sl">Institute of System Architectures in Aeronautics</a></li>&nbsp;&nbsp;&nbsp;
    <a href="https://www.cpacs.de/pages/imprint.html">Imprint</a></li>&nbsp;&nbsp;&nbsp;
    <a href="https://www.cpacs.de/pages/privacy.html">Privacy</a></li>
</p>
'''

    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html') or file.endswith('.htm'):
                file_path = os.path.join(root, file)
                replace_page_footer(file_path)
                print(f"Processed: {file_path}")


if __name__ == '__main__':

    target_directory = "./build/doc/"

    process_directory(target_directory)