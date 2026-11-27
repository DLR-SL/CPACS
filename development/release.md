# CPACS Documentation 

## Release Process

This text will outline the major steps necessary to release a new version of CPACS. A prerequisite for such a release is that all issues that correspond to the target version are marked as done on the issue tracker or are postponed to a future version. Please relate to the corresponding development process documentation. 

The release process is grouped into the following steps: 

## 0. Clean up CPACS Schema

 - Remove unused types                  --> convert.py
 - Set the version                      --> `version` on `xsd:schema`, see below
 - Sort in alphabetical order           --> convert.py
 - Remove unused namespaces!            --> cleanNamespaces.bat

The `version` attribute on the root element `xsd:schema` states the CPACS version of the schema according to Semantic Versioning 2.0.0. It runs through three stages:

| Stage | `version` |
| ---------- | ---------- |
| develop, working towards 3.6.0 | `3.6.0-dev` |
| Release candidates | `3.6.0-rc.1`, `3.6.0-rc.2`, … |
| Release | `3.6.0` |

Right after the release, develop moves on to the next version with `-dev`. The pre-release identifiers are written in lower case: Semantic Versioning compares them in ASCII order, so `3.6.0-RC1` would sort before `3.6.0-dev`. Until the tools that need the version read it from the attribute, the documentation of `cpacsType` keeps its table with version and date: the version there is written exactly as in the attribute (`3.6.0-dev`, not `develop` or `V3.6.0`), and the date is updated with it. `pixi run test-examples` checks the form of the attribute and that the table matches it.
 
## 1. Create documentation                 --> see [Building the documentation](buildDocumentation.md)

## 2. Create libraries                     --> generateLibraries.bat

Currently, CPACS is supported by TIXI and TIGL as interfaces to CPACS. Additionally, there is the possibility to create bindings for other languages as well. This becomes especially handy once users try to generate CPACS files. Within the CPACS release schedule two binding will be generated: Python and Java. The Python bindings are created using the generateDS library; Java bindings via JAXB, see the tools section. Both calls are listed in the generateLibraries batch file. 

## 3. Upload files 
tbd
