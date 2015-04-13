python .\converter\convert.py
java -jar D:\Tools\Saxon\saxon9he.jar -s:.\schema\cpacs_schema.xsd -xsl:.\converter\namespace-cleanup.xsl -o:.\schema\cpacs_schema.xsd