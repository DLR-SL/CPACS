# CPACS Development Process

## Organizing Branches
The developments of CPACS follows the Gitflow workflow as described in [https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow "https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow"). For the developments there are two main branches. While the *master* branch is used for keeping track of the official releases, the *develop* branch is used to combine all the developments and thus contains the main development version. All Feature branches are merged into the *develop* branch.

## Contribution

The purpose of this text is to describe the way CPACS should be developed in between releases. To learn more about the actual release process please look up the corresponding file. 

All developments concerning CPACS should be documented in a public issue tracker. Please note, that this is currently carried out on the github site after the move from googlecode.

Some guidelines for the CPACS development process: 

- Each issue should be marked with a target version. 
- Before implementation, each issue should be checked for conflicts with other parts of the parametrization. 
- No issue shall be implemented without documentation in the CPACS schema file!!!
- Redundancy in the CPACS schema should be avoided by all means. 
- If a multi-fidelity definition is requested, then it should occur on different levels of the schema to prohibit redundancy, e.g. massBreakdown. 


In general the inclusion of new items should work more or less in this order: 

1. Open issue and specify targets
2. Gather all "stakeholders" and start discussion process. In a best case, one of the stakeholders provides an initial proposal as a baseline for further discussions. 
3. Note the state of the discussion in the issue file. 
4. Prototype implementation in CPACS schema
5. Final implementation including documentation
6. Issue closed and feature marked for target version of CPACS


Incoming issues from outside the development team should be checked before being accepted.
The following questions should be answered:

- What is the driver for the requested change?
- If new definitions shall be implemented: Is there an immediate plan to exchange the data between different parties? Don't waste time on the definition of nodes which might not be used for data exchange.

## Release Process

The release process serves to inform all stakeholders and, if necessary, to involve their ideas and requirements in further revisions. For this purpose, preliminary versions are released before the final release. These are:

- **Beta releases**: These releases include all modifications and enhancements from the development process. As a prototype they are intended to be tested in practice. Depending on practical experience, further changes can be flexibly incorporated. 
- **Release candidates (RC)**: A RC is close to the final version and major adjustments should be avoided. This means that the RC serves as a final review for the official release.   

The following figure illustrates the iterative release process:

![ReleaseProcess](./images/releaseProcess.png)
