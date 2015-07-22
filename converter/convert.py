'''
This is a small script for cleaning up CPACS files after editing them in Eclipse
It will do some basic things!

    1. If the new type does not have a complexContent and the extension to 
    complexBaseType this will be added automagically
    
    2. If the documentation is not according to the MAML notation for CPACS
    the existing documentation will be translated into MAML notation or
    default values will be applied
    
    3. All Elements are sorted in a alphabetical order and CPACS is put on top of the list

    4. Some namespace mishaps are cleaned up
    
    5. Finally, the script will sort through all the files and look for obsolete
    types. These types will not be deleted and hence attention should be paid to the output. 

@author: boeh_da
'''
 
from xml.etree.ElementTree import Element, SubElement, parse, Comment,tostring
import  ElementBuilder


def newDoc(app,doc):
    '''
    Creates a new xml documentation element according to MAML notation
    app and doc are included in the summary and remarks section
    '''
    docElement    = Element("xsd:annotation")
    
    appElement    = SubElement(docElement,"xsd:appinfo")
    schemaDoc     = SubElement(appElement,"schemaDoc")
    
    summary       = SubElement(schemaDoc,"ddue:summary")
    sumpara       = SubElement(summary,"ddue:para")
    sumpara.text  = app 
    
    remarks       = SubElement(schemaDoc,"ddue:remarks")
    rempara       = SubElement(remarks,"ddue:para")
    rempara.text  = doc 

    return docElement
    
def addcomplexContent(type):
    '''
    If a complex type is found that has no complex Content, complex Content 
    will be added here. This is essential to clean up Eclipse Editor output 
    '''
    complexContent      = Element("xsd:complexContent")
    extensionBase       = SubElement(complexContent, "xsd:extension")
    extensionBase.set('base','complexBaseType')
      
    for node in type:
        if node.tag.find('annotation')==-1:
            extensionBase.insert(0,node)
            type.remove(node)
    
    for node in type:
        if cmp(node.tag.find,'{http://www.w3.org/2001/XMLSchema}attribute'):
            extensionBase.insert(-1,node)
            type.remove(node)
      
    type.insert(1,complexContent)
    return type

def getTypeList(root):
    '''
    This function provides a list of all types included in CPACS
    '''
    typeList = []
    for type in root:
        if type.tag.find('complexType')!=-1:
            if  not type.attrib['name'].find('Base') != -1:
                typeList.append(type.attrib['name'])
    return typeList


if __name__ == '__main__':
    # Read CPACS schema file
    cpacs_file = "./schema/cpacs_schema.xsd"
    tree = parse(cpacs_file)
    ElementBuilder.Namespace('', 'xsd')
    elem = tree.getroot()

    print "1. Add complex content"
    for type in elem:
        if type.tag.find('complexType')!=-1:
            complexContentFound = False
            #Exclude stuff like stringBaseType
            if  not type.attrib['name'].find('Base') != -1:
                #search for complex Content
                for part in type:
                    if part.tag.find('complexContent') !=-1 and not part.tag.find('annotation')!=-1:
                        complexContentFound = True

                if not complexContentFound:
                    print "adding complex Content to: %s" %type.attrib['name']
                    type = addcomplexContent(type)

    print
    print "2. Add documentation stubs"
    for type in elem:
        if type.tag.find('complexType')!=-1:
            annotationFound = False
            for part in type:
                doc=""
                app=""
                if part.tag.find('annotation')!=-1:
                    annotationFound = True
                    newStyleDoc     = False
                    for item in part:
                        if item.tag.find('appinfo')!=-1:
                            app = str(item.text)
                            for subitem in item :
                                if subitem.tag.find('schemaDoc') != -1:
                                    newStyleDoc     = True

                        if item.tag.find('documentation')!=-1:
                            doc = str(item.text)

                    if not newStyleDoc:
                        type.remove(part)
                        print ("adding documentation to: %s") %type.attrib['name']
                        type.insert(0,newDoc(app,doc))

            if not annotationFound:
                print ("adding annotation to: %s") %type.attrib['name']
                type.insert(0,newDoc(type.attrib["name"],''))

    print
    print "3. Alphabetical sorting"
    bla     = list(elem)
    bla.sort(key=lambda name: name.attrib["name"])


    elem.clear()
    for item in bla:
        elem.append(item)

    # CPACS as top type
    for type in elem:
        #type.insert(0,Comment("****************************************************\n"))
        if type.tag.find('element')!=-1:
            elem.remove(type)
            elem.insert(0,type)

    # Export file
    tree.write(cpacs_file)

    print
    print "4. Some basic cleaning up after the export"
    myCPACS = open(cpacs_file,"r")
    lines  = myCPACS.readlines()
    myCPACS.close()

    res     = []
    for line in lines:
        # Replacing some of the mislead namespace settings.
        # Please note, this part of code is probably very fragile as the sorting order of the
        # namespaces may change at random
        line = line.replace('xs:','xsd:')
        line = line.replace('ns0','xsd')
        line = line.replace('ns1:','sd:')
        line = line.replace('ns2','ddue')
        line = line.replace('ns3','xlink')
        line = line.replace('xsd:schemaDoc','schemaDoc')
        line = line.replace('xsd:summary','ddue:summary')
        line = line.replace('xsd:remarks','ddue:remarks')
        line = line.replace('xsd:para','ddue:para')
        line = line.replace('xsd:content','ddue:content')
        line = line.replace('xsd:section','ddue:section')
        line = line.replace('xsd:definitionTable','ddue:definitionTable')
        line = line.replace('xsd:mediaLink','ddue:mediaLink')
        line = line.replace('xsd:image','ddue:image')
        line = line.replace('xsd:title','ddue:title')
        line = line.replace('xsd:definition','ddue:definition')
        line = line.replace('xsd:definedTerm','ddue:definedTerm')
        line = line.replace('xsd:entry','ddue:entry')
        line = line.replace('xsd:legacyBold','ddue:legacyBold')
        line = line.replace('xsd:legacyItalic','ddue:legacyItalic')
        line = line.replace('xsd:table','ddue:table')
        line = line.replace('xsd:row','ddue:row')
        line = line.replace('xsd:code','ddue:code')
        line = line.replace('xsd:href','xlink:href')
        line = line.replace('xsd:list','ddue:list')
        line = line.replace('xsd:listItem','ddue:listItem')
        #These tow lines represent default values and are not necessary in the CPACS file
        line = line.replace('minOccurs="1"',' ')
        line = line.replace('maxOccurs="1"',' ')



        line = line.replace('<schemaDoc','<schemaDoc xmlns="http://schemas.xsddoc.codeplex.com/schemaDoc/2009/3" xmlns:ddue="http://ddue.schemas.microsoft.com/authoring/2003/5"')
        res.append(line)

    res[0] = '<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ddue="http://ddue.schemas.microsoft.com/authoring/2003/5" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:sd="http://schemas.xsddoc.codeplex.com/schemaDoc/2009/3" xmlns:xlink="http://www.w3.org/1999/xlink"><xsd:element name="cpacs">\n'
    myCPACS = open(cpacs_file,'w')
    myCPACS.writelines(res)
    myCPACS.close()

    print
    print "5. Look for unused types in the CPACS schema definition, i.e. types that are not needed anymore"
    # In the future this might become a test
    original = parse(cpacs_file)
    ElementBuilder.Namespace('', 'xsd')
    originalTypes = getTypeList(original.getroot())

    myCPACS = open(cpacs_file,"r")
    lines   = myCPACS.readlines()
    myCPACS.close()

    toomuch = []
    for item in originalTypes:
        didNotfind  = True
        for line in lines:
            if line.find('type="'+str(item))!=-1:
                didNotfind  = False

        if didNotfind:
            toomuch.append(item)

    if len(toomuch)>0:
        print "The following types are currently unused in CPACS, please check whether these should be deleted"
        for item in toomuch:
            print item
    else:
        print "No unsused types could be identified"


