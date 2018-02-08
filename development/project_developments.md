# Developments in Research Projects
Since the start of the developments in 2005, CPACS and its user community have grown constantly.
By now CPACS is used in many different research projects. Each project has a different focus and thus individual requirements for using CPACS. In order not to hamper the project activities a separate development branch should be created for each project where the results from feature branches can be combined into a project specific CPACS version. For easier integration into the development branch of the official CPACS repository, changes should still be developed in feature branches which are kept until integration to the official CPACS has been performed. This allows to easier integrate features individually.
The most common reasons for ongoing developments in CPACS are the following. 

## Missing Data
When CPACS is used in research projects you might find that you need to store additional data for which there is no definition in CPACS. In such a case we suggest the following approach:

1. An immediate solution can be to use the toolspecific node for user specific data. This allows you to continue with the project without relying on a time consuming development process for modifying the schema, and through practical experiences and quick development cycles you should be able to identify the relevant data relatively fast. If this is all you need for your project you can stop here. But in case you would like to contribute to the development of CPACS you should continue with the next steps.

2. The next step is to find a suitable node structure for the CPACS data and identify where the data should be located. This should be done by involving experts from all the participating disciplines as well as considering the main CPACS development guidelines. If more accessible the discussions can be done based on example XML files describing the structure rather than the XSD file. Once an agreement has been reached on the data structure you can follow with the next step.
 
3. Modify the schema (XSD) file of CPACS according to your findings. Commit the changes small digestable pieces. By using separate commits for each semantic change, integration can be simplified a lot. Try and keep consistent with common practices in CPACS (an official collection of practices still has to be assembled). 

4. Create a pull request as explained at [https://help.github.com/articles/creating-a-pull-request/](https://help.github.com/articles/creating-a-pull-request/ "Creating a Pull Request") and wait for feedback.


## Unsuitable Data Structure
If you discover that a data structure is not suitable for your task/project you can take the same approach as for missing data, but when finding a new structure try to reduce the required changes to a minimum. If this is not possible or this would not lead to a feasible result, you might aswell redesign the concerning CPACS nodes. In such a case the integration process to the main development branch is much more difficult sinca all parties which use the existing nodes should be allowed to make their case. This will trigger a discussion which need to be resolved within the CPACS community.
