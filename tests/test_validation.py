import unittest
from tixi3 import tixi3wrapper

class schemaCheck(unittest.TestCase):

    def test_genericSystems(self):
        xml = '../examples/genericSystemShapes.xml'
        xsd = '../schema/cpacs_schema.xsd'
        tixi_h.open(xml)
        if not tixi_h.schemaValidateFromFile(xsd):
            result = True
        self.assertTrue(result)
        tixi_h.close()
        
    def test_basicWing(self):
        xml = '../examples/basicWing.xml'
        xsd = '../schema/cpacs_schema.xsd'
        tixi_h.open(xml)
        if not tixi_h.schemaValidateFromFile(xsd):
            result = True
        self.assertTrue(result)
        tixi_h.close()

if __name__ == '__main__':
    tixi_h = tixi3wrapper.Tixi3()
    unittest.main()
