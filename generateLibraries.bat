md build\lib\Python
md build\lib\Java
python D:\Tools\Python_27\Scripts\generateDS.py -f -o .\build\lib\Python\cpacslib.py .\schema\cpacs_schema.xsd
D:\Tools\JAXB\jaxb-ri\bin\xjc.bat -d .\build\lib -p Java .\schema\cpacs_schema.xsd