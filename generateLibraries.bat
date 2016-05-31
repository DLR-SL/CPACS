md build\lib\Python
md build\lib\Java
python D:\libs\generateDS-2.7b\generateDS.py -f -o .\build\lib\Python\cpacslib.py .\schema\cpacs_schema.xsd
D:\libs\jaxb-ri\bin\xjc.bat -d .\build\lib -p Java .\schema\cpacs_schema.xsd