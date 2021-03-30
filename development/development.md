# CPACS Development

## Organizing Branches
The developments of CPACS follows the Gitflow workflow as described in [https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow "https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow"). For the developments there are two main branches. While the *master* branch is used for keeping track of the official releases, the *develop* branch is used to combine all the developments and thus contains the main development version. All Feature branches are merged into the *develop* branch.

## Development Process

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


Incoming issues from outside the development team should be checked before beeing accepted.
The following questions should be answered:

- What is the driver for the requested change?
- If new definitions shall be implemented: Is there an immediate plan to exchange the data between different parties? Don't waste time on the definition of nodes which might not be used for data exchange.

## Release Process

The release process serves to inform all stakeholders and, if necessary, to involve their ideas and requirements in further revisions. For this purpose, preliminary versions are released before the final release. These are:

- **Beta releases**: These releases include all modifications and enhancements from the development process. As a prototype they are intended to be tested in practice. Depending on practical experience, further changes can be flexibly incorporated. 
- **Release candidates (RC)**: A RC is close to the final version and major adjustments should be avoided. This means that the RC serves as a final review for the official release.   

The following figure illustrates the iterative release process:

![ReleaseProcess](./images/releaseProcess.png)


## Contribution Guidelines
TODO


## Development Guidelines
We will try to find/define some guidelines for decisions on how to structure CPACS.

First loose collection:

- Always use SI and accepted derived units
- Use the CPACS coordinate system for describing data (Do not introduce new coordinate systems if not absolutely neccessary)

### Naming conventions

- **..Point**: a fixed point in a finite parameter space; usually in spatial dimensions (e.g., `hingePoint`) or limited flight parameters (e.g., `flightPoint` comprising altitude and velocity). 
- **..Case**: used to describe combinations of complex parameter combinations such as analysis inputs/outputs (e.g., `loadCase`, `aeroCase`, `flyingQualityCase`...)
- **..State**/**..CaseDefinition**: can be used within a *case* description to enrich a *point* with more complex, individual information (e.g., `aeroCase/state`)
- **..Requirement**: used for requirements, but can be reduced to **req** to avoid very long element names


## Additional Development Guidelines by Example
TODO: Explaining guidelines using examples from previous decisions...

### Duplication VS Single Type Reference VS Hidden Changes
Let us discuss different approaches at the example of introducing a second option for specifying internal wing points by using segment eta xsi coordinates.
This related to issue https://github.com/DLR-LY/CPACS/issues/495.

In principle I see three different possibilities to implement the two options.

1. add an additional segmentUID node next to eta and xsi. THen, whenever a segmentUID is given the eta and xsi nodes should be interpreted as segment eta xsi coordinates.
  ```
  <parentNode>
    <eta />
    <xsi />
    <segmentUID /> <!-- optional -->
  </parentNode>
```
2. add the option as a choice between [eta, xsi] or [etaSeg, xsiSeg, segmentUID]
  ```
  <parentNode>
    <!-- choice 1 start-->
    <eta />
    <xsi />
    <!-- choice 1 end -->
    <!-- choice 2 -->
    <etaSeg />
    <xsiSeg />
    <segmentUID />
    <!-- choice 2 end -->
  </parentNode>
```
3. combine both options as described in 2. into their own parent node
  ```
  <parentNode>
    <!-- choice 1 start-->
    <componentSegmentPoint>
      <eta />
      <xsi />
    </componentSegmentPoint>
    <!-- choice 1 end -->
    <!-- choice 2 -->
    <segmentPoint>
      <eta />
      <xsi />
      <segmentUID />
    </segmentPoint>
    <!-- choice 2 end -->
  </parentNode>
```

Option 1. is clearly a very reduced approach. It allows the user of the data to switch the interpretation of the eta and xsi nodes depending on the existence of the segmentUID node. A risk of this approach is that without modifications, existing tools might miss the additional segmentUID node and thus misinterpret the point.
Option 2. avoids misinterpreting the segment eta xsi values by giving them a different node name. But the drawback is the additional nodes (node names) which need to be processed.
Option 3. is very similar to option 2. but keeps eta xsi as the names also for segment eta xsi coordinates and creates an additional intermediate node for both options. This opens up the opportunity to create separate types for both options which can be reused at several locations throughout the schema. This would minimize the effort in case changes are required for the definition of the points and ensures some consistency in the use of eta xsi points. E.g. if we had an etaXsiPointType for componentSegment points we could find all uses throughout the schema to implement the segment coordinate alternative. Also creating an additional type allows us to use xsd:all within the type definition which otherwise would not be possible due to the xsd:choice.


### Favor compact solutions
... if feasible

For point clouds such as used in wing profiles in early CPACS versions a point definition with x,y and z coordinate was used for every profile point.

```
<points>
  <point uID="p1">
    <x>0.0</x>
    <y>0.0</y>
    <z>0.0</z>
  </point>
  <point uID="p2">
    <x>1.0</x>
    <y>0.0</y>
    <z>0.0</z>
  </point>
  <point uID="p3">
    <x>1.0</x>
    <y>0.0</y>
    <z>1.0</z>
  </point>
  <point uID="p4">
    <x>0.0</x>
    <y>0.0</y>
    <z>1.0</z>
  </point>
  <point uID="p5">
    <x>0.0</x>
    <y>0.0</y>
    <z>0.5</z>
  </point>
  <point uID="p6">
    <x>0.0</x>
    <y>0.0</y>
    <z>0.0</z>
  </point>
</points>
```

In this case the overhead of data due to the tags was much higher than the actual data to be exchanged. Thus it was changed to a more compact definition:

```
<pointList>
  <x>0.0;1.0;1.0;0.0;0.0;0.0</x>
  <y>0.0;0.0;0.0;0.0;0.0;0.0</y>
  <z>0.0;0.0;1.0;1.0;0.5;0.0</z>
</pointList>
```
