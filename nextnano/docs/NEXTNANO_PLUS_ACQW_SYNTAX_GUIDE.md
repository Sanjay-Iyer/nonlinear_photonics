# nextnano++ 3.0.0 Syntax Guide for 1D GaAs/AlGaAs ACQW Workflows

## Purpose

This guide is scoped to the syntax needed for the current nonlinear-photonics repository:
- 1D GaAs/AlGaAs asymmetric coupled quantum wells (ACQWs)
- abrupt and linearly graded interfaces
- imported nonlinear grading profiles (Fermi / erf / cosine generated in Python)
- electron Gamma-band and heavy-hole (HH) bound states
- structure/composition, band-edge, energy, and wavefunction outputs
- parser-first validation before licensed solver runs

It is not intended to document every nextnano++ keyword.

---

# 1. Basic input grammar

## Groups

nextnano++ organizes input into nested groups:

```text
group_name{
    keyword = value
    nested_group{
        ...
    }
}
```

Examples:

```text
global{
    simulate1D{}
    temperature = 300
}
```

```text
structure{
    region{
        ...
    }
}
```

## Scalars, vectors, and strings

```text
temperature = 300
x = [10.0, 20.0]
name = "GaAs"
```

## Variables

Variables begin with `$` and have global scope after definition.

```text
$well_left  = 20.0
$well_right = 27.1

structure{
    region{
        line{
            x = [$well_left, $well_right]
        }
        binary{
            name = "GaAs"
        }
    }
}
```

Variables may be used in mathematical expressions.

## Comments

Single-line comments:

```text
# comment
temperature = 300   # inline comment
```

Multi-line text comments:

```text
!TEXT
comment block
!ENDTEXT
```

Do not nest `!TEXT ... !ENDTEXT` blocks.

---

# 2. Global 1D simulation definition

For this project the growth coordinate is nextnano++ simulation `x`.

```text
global{
    simulate1D{}

    crystal_zb{
        # Define the zincblende crystal orientation as required by the model.
        # Keep this consistent with the validated project deck.
    }

    substrate{
        name = "GaAs"
    }

    temperature = 300
}
```

Important:
- Exactly one of `simulate1D{}`, `simulate2D{}`, or `simulate3D{}` must be selected.
- `simulate1D{}` means the simulation coordinate is `x`.
- Structure coordinates are in nm.
- Temperature is in K.

Do not casually change the crystal orientation or substrate in a validated scientific workflow.

---

# 3. Grid syntax

A 1D simulation uses:

```text
grid{
    xgrid{
        line{ pos = 0.0  spacing = 0.05 }
        line{ pos = 50.0 spacing = 0.05 }
    }
}
```

At least two `line{}` entries are required to define the simulation extent.

A line has:

```text
line{
    pos = 5.0
    spacing = 0.05
}
```

- `pos` is in nm.
- `spacing` is in nm.
- nextnano recommends putting grid lines at material interfaces so geometry remains well defined when spacing changes.

For the current Demo 14 workflow, the scientific mesh setting should remain controlled by the repository configuration rather than hard-coded independently in the deck renderer.

---

# 4. Structure geometry

Structure material assignments live inside:

```text
structure{
    region{
        SHAPE
        MATERIAL
    }
}
```

## Entire domain

```text
everywhere{}
```

## 1D interval

```text
line{
    x = [10.0, 20.0]
}
```

Coordinates are in nm.

For this project, prefer explicit intervals derived from one authoritative composition/geometry model.

---

# 5. Critical region/material rule

## Project rule: one material assignment per `region{}`

The nextnano++ 3.0.0 parser on the project installation rejected a Demo 14 deck that placed multiple material specifications in one `region{}` with an error such as:

```text
Too many instances of 'ternary_linear'
```

Therefore use:

```text
region{
    line{ x = [a, b] }
    ternary_linear{ ... }
}

region{
    line{ x = [b, c] }
    ternary_constant{ ... }
}

region{
    line{ x = [c, d] }
    ternary_linear{ ... }
}
```

Do NOT use:

```text
region{
    line{ x = [a, d] }

    ternary_linear{ ... }
    ternary_constant{ ... }
    ternary_linear{ ... }
}
```

This is a parser-enforced rule for the installed nextnano++ 3.0.0 workflow.

---

# 6. Binary GaAs

A binary material region is:

```text
region{
    line{
        x = [10.0, 20.0]
    }

    binary{
        name = "GaAs"
    }
}
```

Use `binary{ name = "GaAs" }` when an explicit pure-GaAs region is intended.

---

# 7. Constant AlGaAs

For Al(x)Ga(1-x)As:

```text
region{
    line{
        x = [20.0, 22.0]
    }

    ternary_constant{
        name    = "Al(x)Ga(1-x)As"
        alloy_x = 0.55
    }
}
```

For this material name:
- `alloy_x = 0.55` means Al0.55Ga0.45As.
- alloy fractions are dimensionless and must be between 0 and 1.

---

# 8. Linear AlGaAs grading

A linear alloy profile is:

```text
region{
    line{
        x = [20.0, 21.0]
    }

    ternary_linear{
        name    = "Al(x)Ga(1-x)As"
        alloy_x = [0.0, 0.55]
        x       = [20.0, 21.0]
    }
}
```

This means:

```text
x = 20.0 nm  -> Al fraction 0.00
x = 21.0 nm  -> Al fraction 0.55
```

The reverse grade is:

```text
region{
    line{
        x = [21.0, 22.0]
    }

    ternary_linear{
        name    = "Al(x)Ga(1-x)As"
        alloy_x = [0.55, 0.0]
        x       = [21.0, 22.0]
    }
}
```

For a 1D simulation, only the `x` coordinate is needed.

## Important renderer rule

The `line{ x=[...] }` interval and the `ternary_linear{ x=[...] }` interval should describe the same physical segment unless there is a deliberate, documented reason otherwise.

---

# 9. Correct ACQW material topology

The physical structure for a GaAs/AlGaAs coupled double well must contain actual outer barriers.

Conceptually:

```text
AlGaAs outer barrier
    ↓
interface / grade
    ↓
GaAs well 1
    ↓
interface / grade
    ↓
AlGaAs central barrier
    ↓
interface / grade
    ↓
GaAs well 2
    ↓
interface / grade
    ↓
AlGaAs outer barrier
```

A structure with only:

```text
GaAs background
+ one central AlGaAs barrier
```

is NOT the intended finite coupled-double-well structure because the GaAs wells are not confined by outer AlGaAs barriers.

## Project implementation rule

Generate all region boundaries from one authoritative continuous composition function `x_Al(x)`.

Do not independently compute:
- deck geometry,
- grading-width diagnostics,
- analysis windows,
- and plotting geometry

from separate formulas that can drift.

---

# 10. Native linear grading pattern

For a non-overlapping linear interface model, the physical region sequence may be expressed as separate regions such as:

```text
region{ line{ x=[x0,x1] } ternary_constant{ name="Al(x)Ga(1-x)As" alloy_x=0.55 } }
region{ line{ x=[x1,x2] } ternary_linear{   name="Al(x)Ga(1-x)As" alloy_x=[0.55,0.0] x=[x1,x2] } }
region{ line{ x=[x2,x3] } binary{           name="GaAs" } }
region{ line{ x=[x3,x4] } ternary_linear{   name="Al(x)Ga(1-x)As" alloy_x=[0.0,0.55] x=[x3,x4] } }
```

Continue similarly through the central barrier, second well, and right outer barrier.

The exact positions must come from the project grading/geometry model.

## Overlapping grades

If smooth/linear interface widths overlap across a thin barrier, do not fabricate a flat Al0.55Ga0.45As plateau merely to fit a fixed `linear -> constant -> linear` template.

Instead:
1. construct the intended `x_Al(x)`,
2. determine the actually achieved peak composition,
3. partition it into valid nextnano++ regions, or
4. use an imported profile where that representation is more faithful.

---

# 11. Imported alloy profiles

This is the preferred mechanism for arbitrary profiles such as:
- Fermi
- erf
- cosine
- other Python-generated continuous profiles

## Step A: declare the file

```text
import{
    file{
        name                 = "al_profile"
        filename             = "al_profile.dat"
        format               = DAT
        number_of_dimensions = 1
    }
}
```

If `directory` is omitted and the filename has no path, nextnano++ looks in the input-file directory.

An explicit import directory may be used:

```text
import{
    directory = "./"

    file{
        name     = "al_profile"
        filename = "al_profile.dat"
        format   = DAT
    }
}
```

## Step B: assign it to a ternary region

```text
structure{
    region{
        line{
            x = [0.0, 50.0]
        }

        ternary_import{
            name        = "Al(x)Ga(1-x)As"
            import_from = "al_profile"
        }
    }
}
```

For a ternary, the imported profile must have exactly one alloy data component.

---

# 12. 1D `.dat` profile format

For a 1D ternary alloy profile, use two numeric columns:

```text
# x_nm    x_Al
0.00      0.55
0.05      0.55
0.10      0.54
...
```

Interpretation:
- first column = x coordinate
- second column = alloy fraction

Alloy fractions should normally already be in the range 0 to 1.

If source values are percentages, nextnano++ supports `scale`, for example:

```text
file{
    name     = "al_profile"
    filename = "al_profile.dat"
    format   = DAT
    scale    = 0.01
}
```

Headers/comments in imported files are ignored by the importer.

Important interpolation behavior:
- imported values are linearly interpolated between supplied grid points,
- therefore the density of points in `al_profile.dat` matters,
- always compare nextnano++'s realized alloy-composition output against the intended Python profile.

---

# 13. Structure-validation output

Always request alloy composition:

```text
structure{
    output_alloy_composition{}

    ...
}
```

This outputs the alloy composition at each grid point.

This is a critical validation artifact for Demo 14/15.

The validation hierarchy should be:

```text
requested parameters
    ↓
Python x_Al(x)
    ↓
rendered .nnp / imported .dat
    ↓
nextnano++ output_alloy_composition
    ↓
compare numerically
```

Do not assume a deck is scientifically correct merely because `--parse` succeeds.

---

# 14. Classical band-edge output

To request band edges:

```text
classical{
    Gamma{}
    HH{}

    output_bandedges{}
}
```

`output_bandedges{}` writes `bandedges.dat`.

A restricted set can be requested with `profiles`, for example:

```text
classical{
    Gamma{}
    HH{}

    output_bandedges{
        profiles = "Gamma HH"
    }
}
```

For this project, Gamma conduction and HH valence profiles are the main band-edge quantities of interest.

---

# 15. Quantum region

A quantum region is defined separately from material `structure{ region{} }` blocks.

Example:

```text
quantum{
    region{
        name = "acqw"
        x    = [10.0, 40.0]

        Gamma{
            num_ev = 4
        }

        HH{
            num_ev = 4
        }

        output_states{}
    }
}
```

Important:
- `name` is required.
- in 1D, `x=[start,end]` defines the Schrödinger domain in nm.
- this numerical quantum-region boundary is NOT a substitute for physical outer barriers.
- the quantum region should extend far enough into the barriers that bound-state wavefunctions decay appropriately.

---

# 16. Single-band Gamma and HH models

These groups trigger the single-band effective-mass Schrödinger solver:

```text
Gamma{
    num_ev = 4
}

HH{
    num_ev = 4
}
```

`num_ev` is the number of eigenvalues requested and must be at least 1.

For the current ACQW workflow, the key states are typically the lowest few Gamma-electron and heavy-hole states needed by the chi2 post-processing/state-tracking logic.

Do not change `num_ev` without confirming the parser and state tracker still receive enough physical states.

---

# 17. Quantum state output

Use:

```text
output_states{}
```

inside a quantum region.

Relevant controls include:

```text
output_states{
    max_num       = 4
    envelopes     = yes
    probabilities = yes
    in_one_file   = yes
}
```

In nextnano++ 3.0.0:
- envelope-function output is supported,
- probability-density output is supported,
- the energy spectrum is written to energy-spectrum output files.

These outputs feed the repository's state parsing, tracking, dipole integrals, and chi2 analysis.

---

# 18. Triggering the Schrödinger solve

Defining `quantum{ region{...} }` configures the quantum model.

The actual quantum solve is triggered by:

```text
run{
    quantum{}
}
```

This solves the Schrödinger equation for the defined quantum region(s).

---

# 19. Parser and structure-only validation

The command line supports:

```text
nextnano++ --parse input_file.in
```

This:
- parses the input,
- validates grammar/keyword structure,
- quits without performing the full simulation.

The command line also supports:

```text
nextnano++ --structure input_file.in
```

This:
- parses the input,
- generates the structure,
- quits before the full physics solve.

For this repository the recommended gate is:

```text
render deck
    ↓
--parse
    ↓
--structure when useful
    ↓
inspect output_alloy_composition / generated structure
    ↓
licensed quantum solve
```

A parser pass proves syntax compatibility only. It does NOT prove that the material topology is physically correct.

---

# 20. Production command-line options used by this project

The known-good licensed solver configuration uses options of the form:

```text
nextnano++_Intel_64bit.exe \
    --license <license_file> \
    --database <database_file> \
    --threads 4 \
    --outputdirectory <output_dir> \
    --noautooutdir \
    <input_file>
```

Relevant documented options:

```text
--parse
--structure
--database <file>
--license <file>
--inputdirectory <dir>
--outputdirectory <dir>
--noautooutdir
--threads <n>
```

The Python harness must check the subprocess exit code before attempting analysis.

---

# 21. Demo 14 / Demo 15 renderer invariants

Every generated candidate should satisfy all of these before a licensed solve:

1. The deck parses.
2. Exactly one material assignment is used per `structure{ region{} }`.
3. The full ACQW contains left and right AlGaAs outer barriers.
4. Both GaAs wells are physically confined by AlGaAs.
5. All intended interfaces are represented.
6. `0 <= x_Al(x) <= 1`; project bounds may be narrower.
7. The rendered/imported composition matches the authoritative Python `x_Al(x)`.
8. `output_alloy_composition{}` is enabled for validation runs.
9. Grid interfaces/spacing resolve the grading profile adequately.
10. Quantum-region numerical boundaries lie sufficiently inside outer barriers.
11. A solver nonzero exit is a technical failure and stops analysis.
12. No objective value is fabricated for parser/solver/analysis failures.

---

# 22. Do not confuse these three validations

## Syntax validation

Question:

```text
Can nextnano++ read this deck?
```

Tool:

```text
--parse
```

## Structure validation

Question:

```text
Did nextnano++ construct the intended Al composition and barriers?
```

Tools/artifacts:
- `--structure`
- `output_alloy_composition{}`
- material/region outputs

## Physics validation

Question:

```text
Did the structure produce physically credible bound states and energies?
```

Artifacts:
- band edges
- energy spectra
- envelopes/probabilities
- boundary leakage
- state tracking
- mesh convergence

A syntax pass cannot replace structure or physics validation.

---

# 23. Recommended canonical validation sequence

```text
BO proposal
    ↓
derive trial geometry
    ↓
construct authoritative x_Al(x)
    ↓
render native/imported nextnano++ input
    ↓
save requested-vs-realized grading diagnostics
    ↓
nextnano++ --parse
    ↓
PASS?
    ├── NO -> technical failure; preserve deck/log; zero solver objective
    └── YES
          ↓
nextnano++ --structure / composition check where applicable
          ↓
composition matches intended x_Al(x)?
    ├── NO -> renderer/technical failure
    └── YES
          ↓
licensed quantum solve
          ↓
exit code == 0 and expected outputs exist?
    ├── NO -> solver technical failure
    └── YES
          ↓
parse energies + wavefunctions
          ↓
QC/state tracking
          ↓
absolute chi2 analysis
          ↓
Ax observation
```

---

# 24. Local authoritative examples to keep near the code

The installed nextnano++ 3.0.0 package contains official examples for imported data:

```text
nextnano++\examples\basics\import-dat_1D.nnp
nextnano++\examples\basics\import-dat_1D_ternary.dat
```

The project also has working Ramesh-style double-quantum-well input files. Use those as regression references for:
- AlGaAs outer-barrier topology,
- GaAs wells,
- separate grading regions,
- material-region syntax.

Do not copy a reference blindly: compare the intended composition profile and geometry numerically.

---

# 25. Minimum reference deck skeleton

This is a syntax skeleton, not a complete scientific deck:

```text
global{
    simulate1D{}
    substrate{
        name = "GaAs"
    }
    temperature = 300
}

grid{
    xgrid{
        line{ pos = 0.0  spacing = 0.05 }
        line{ pos = 50.0 spacing = 0.05 }
    }
}

structure{
    output_alloy_composition{}

    region{
        line{ x = [0.0, 10.0] }
        ternary_constant{
            name    = "Al(x)Ga(1-x)As"
            alloy_x = 0.55
        }
    }

    # Additional independent regions for:
    # grade -> well 1 -> grade -> central barrier
    # -> grade -> well 2 -> grade -> outer barrier
}

classical{
    Gamma{}
    HH{}
    output_bandedges{
        profiles = "Gamma HH"
    }
}

quantum{
    region{
        name = "acqw"
        x    = [5.0, 45.0]

        Gamma{
            num_ev = 4
        }

        HH{
            num_ev = 4
        }

        output_states{
            envelopes     = yes
            probabilities = yes
        }
    }
}

run{
    quantum{}
}
```

For imported nonlinear grading, add an `import{ file{...} }` block and use `ternary_import{}` in the relevant structure region(s).

---

# 26. Source hierarchy for future debugging

Use this evidence order:

1. Current nextnano++ 3.0.0 official documentation.
2. `--parse` against the actual installed executable.
3. `--structure` and actual generated structure/composition outputs.
4. Official examples shipped with the exact installed package.
5. Previously successful project input decks and raw logs.
6. Repository tests/mocks.

A Python unit test cannot override a contradiction from the actual nextnano++ parser.

---

# 27. Official documentation pages consulted

- nextnano++ Input syntax
- `global{}`
- `grid{}`
- `structure{ region{} }` shape objects
- `structure{ region{} }` material assignment
- `import{}`
- Importing files tutorial
- `structure{ output_alloy_composition{} }`
- `classical{ output_bandedges{} }`
- `quantum{ region{} }`
- Gamma/L/ X/Delta/HH/LH/SO single-band model page
- `quantum{ region{ output_states{} } }`
- `run{ quantum{} }`
- nextnano++ Command line

Guide scope/version: nextnano++ 3.0.0, August 2026 project workflow.
