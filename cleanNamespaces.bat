python .\converter\convert.py
java -jar .\tools\SaxonHE9-6-0-8J\saxon9he.jar -s:.\schema\cpacs_schema.xsd -xsl:.\converter\namespace-cleanup.xsl -o:.\schema\cpacs_schema.xsd