# CPACS

The Common Parametric Aircraft Configuration Schema (**CPACS**) is a data definition for the air transportation system. CPACS enables engineers to exchange information between their tools. It is therefore a driver for multi-disciplinary and multi-fidelity design in distributed environments. CPACS describes the characteristics of aircraft, rotorcraft, engines, climate impact, fleets and mission in a structured, hierarchical manner. Not only product but also process information is stored in CPACS. The process information helps in setting up workflows for analysis modules. Due to the fact that CPACS follows a central model approach, the number of interfaces is reduced to a minimum.

![Centralized vs Decentralized](/development/images/centralized.png)

## CPACS Documentation

The online documentation of the current development status can be viewed at [this link](https://dlr-sl.github.io/CPACS/). Further documentation of the official releases can be found at [cpacs.de](https://www.cpacs.de/pages/documentation.html).

## CPACS Homepage

The CPACS homepage contains information about new developments, releases and other related projects. Check out the available content at [www.cpacs.de](https://www.cpacs.de).

## CPACS Tutorial Video: How-to Create a Wing

Have a look at our first [tutorial](https://www.youtube.com/watch?v=NgYWfc5N-Xw) video for CPACS. It explains how to create a wing in CPACS. Thanks to Till and Erwin for their work!

## Development

Further information about the CPACS development is available [here](/development/README.md).

### Schema validation environment

The reproducible development and validation environment is managed with [Pixi](https://pixi.sh).

Install the environment:

```bash
pixi install
```

Run the complete validation suite:

```bash
pixi run check
```

Run individual checks:

```bash
pixi run test-schema
pixi run test-examples
```

Format the schema in place:

```bash
pixi run format-schema
```

The generated `pixi.lock` file is part of the repository and must be committed. The local `.pixi/` environment directory must not be committed.

## Cite & Acknowledge

CPACS is available as Open Source and we encourage anyone to make use of it. If you are applying CPACS in a scientific environment and publish any related work, please cite the following article:

M. Alder, E. Moerland, J. Jepsen and B. Nagel. [_Recent Advances in Establishing a Common Language for Aircraft Design with CPACS_](https://elib.dlr.de/134341/). Aerospace Europe Conference 2020, Bordeaux, France, 2020.

For more publications concerning CPACS, we provide the following link to [Google Scholar](https://scholar.google.de/scholar?start=0&q=CPACS+Common+Parametric+Aircraft+Configuration+Schema&hl=de&as_sdt=0,5).
