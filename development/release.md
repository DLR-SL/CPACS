# CPACS Documentation 

## Release Process

This text will outline the major steps necessary to release a new version of CPACS. A prerequisite for such a release is that all issues that correspond to the target version are marked as done on the issue tracker or are postponed to a future version. Please relate to the corresponding development process documentation. 

The release process is grouped into the following steps: 

## 0. Clean up CPACS Schema

 - Remove unused types                  --> convert.py
 - Update version number and date       --> convert.py
 - Sort in alphabetical order           --> convert.py
 - Remove unused namespaces!            --> cleanNamespaces.bat
 
## 1. Create documentation                 --> createDocumentation.bat

## 2. Create dummy file

## 3. Create libraries                     --> generateLibraries.bat

Currently, CPACS is supported by TIXI and TIGL as interfaces to CPACS. Additionally, there is the possibility to create bindings for other languages as well. This becomes especially handy once users try to generate CPACS files. Within the CPACS release schedule two binding will be generated: Python and Java. The Python bindings are created using the generateDS library; Java bindings via JAXB, see the tools section. Both calls are listed in the generateLibraries batch file. 

## 4. Upload files 
tbd
