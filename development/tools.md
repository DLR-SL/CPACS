# CPACS Documentation 

## Tools

A list of tools connected to CPACS development: 
- [Eclipse](https://www.eclipse.org/downloads/) including Web Tools Platform (e.g., _Eclipse IDE for Java Developers_)
- Python including xml libraries
  -- generateDS for Python library
- Saxon
- .Net environment >4.0
- Sandcastle Helpfile Builder
- Sandcastle XSD plugin 

## Version management
-------------------
The (public) version management is via GitHub. 

## Development
All handling of XML and hence XSD files is taken care of in "Eclipse" and the "Web Tools Platform". This has proven to be the most reliable and free method to edit XML files. As the CSD file tends to be lengthy and formatting operations are cumbersome one should restrict to one XML tool. Different formatting algorithms will result in different file layouts and make diff operations horrible. 

## Scripting
Several smaller tools have been developed to aid in the development of CPACS. Mostly, these scripts aid in cleaning up the file after changes have been commited. On the on hand a reasonable Python distribution <3.0 is necessary to run the converter script in the same folder on the repository. On the other hand, namespace corrections are taken care of by xslt transformations. Saxon is the xslt transformator of choice. 

## Libraries
CPACS shall be released with two software bindings: Python and Java

The python library can be created using the generateDS packacke provided by Dave Kuhlmann. It can be found online at: http://www.davekuhlman.org/generateDS.html

The Java library is generated via JAXB or rather the xjc tool. If you are lucky and you live in a world where there is no outsourced IT-department you might have xjc in your standard java distribution. If not, please feel free to browse to https://jaxb.java.net/ for a download.

## Documentation
The documentation for CPACS is generated using the MSBuild command from the .Net framework. For a plain build of the CPACS documentation run MS Build from the corresponding .Net version with the CPACS_doc_project.shfbproj file. For adaptions to the project please use the sandcastle help file builder and the XSD plugin available in [development/3rdparty.zip](../development/3rdparty.zip).

