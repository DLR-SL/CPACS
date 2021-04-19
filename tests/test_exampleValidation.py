import unittest
import os
from tixi3 import tixi3wrapper

class schemaCheck(unittest.TestCase):

    def test_exampleFiles(self):

        xml_dir = "../examples/"
        xml_files = [os.path.join(xml_dir,f) for f in os.listdir(xml_dir)
                     if f != "toolspecific.xml"]
        xsd = "../schema/cpacs_schema.xsd"

        for xml in xml_files:
            print("Opening %s ..."%xml)
            tixi_h.open(xml)
            if not tixi_h.schemaValidateFromFile(xsd):
                validationResult = True
            self.assertTrue(validationResult)
            tixi_h.close()

if __name__ == '__main__':
    tixi_h = tixi3wrapper.Tixi3()
    unittest.main()
