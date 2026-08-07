# nextnano++ Syntax Reference Guide
## Verified syntax for GaAs/AlGaAs ACQW, grading, quantum-state, and validation workflows

**Project scope:** nextnano++ 3.0.0-style inputs used for 1D GaAs/AlGaAs asymmetric coupled quantum wells (ACQWs), Demo 14 renderer validation, Demo 16 stress validation, and future broader Demo 15 work.

**Status convention**
- **VERIFIED — official docs:** confirmed against the current nextnano++ documentation.
- **VERIFIED — installed parser/project:** confirmed by the installed nextnano++ 3.0.0 parser or a previously successful project input.
- **PROJECT RULE:** a repository convention added to prevent scientifically wrong or ambiguous simulations.
- **ADVANCED / NOT CURRENTLY USED:** valid nextnano++ syntax but not needed for the present 1D ACQW workflow.

---

# 0. Important corrections to previously collected syntax

Several syntax snippets collected from secondary summaries looked plausible but do **not** match the current nextnano++ documentation exactly. For this project, use the corrected forms in this guide.

## Comments

**Use:**

```text
# one-line comment

x = 3.0   # inline comment

!TEXT
multi-line comment
!ENDTEXT
```

Do **not** assume C/C++ comment syntax such as:

```text
// comment
/* comment */
```

The current nextnano++ input-syntax documentation explicitly documents `#` and `!TEXT ... !ENDTEXT`.

## Global orientation

Use `crystal_zb{}` with Miller-index axes, for example:

```text
global{
    simulate1D{}

    crystal_zb{
        x_hkl = [1, 0, 0]
        y_hkl = [0, 1, 0]
    }

    substrate{
        name = "GaAs"
    }

    temperature = 300
}
```

Do **not** replace this with an undocumented generic block such as:

```text
orientation{
    z_axis = ...
    x_axis = ...
}
```

For zincblende, exactly two of `x_hkl`, `y_hkl`, and `z_hkl` are defined; nextnano++ obtains the remaining axis from the coordinate system.

## Grid

Use:

```text
grid{
    xgrid{
        ...
    }
}
```

not:

```text
grid{
    x{
        ...
    }
}
```

For 2D, use `xgrid{}` + `ygrid{}`. For 3D, use `xgrid{}` + `ygrid{}` + `zgrid{}`.

## Quantum-state counts

For the current single-band Gamma/HH workflow, the number of requested eigenvalues is specified with `num_ev` **inside the individual band model**:

```text
Gamma{
    num_ev = 4
}

HH{
    num_ev = 4
}
```

Do not substitute generic undocumented attributes such as:

```text
num_electrons = 4
num_holes = 4
```

for the current production renderer.

## Output directory

The current nextnano++ `output{}` documentation uses:

```text
output{
    directory = "../output/example"
}
```

Do not use an invented `folder = ...` attribute.

Likewise, do not assume a generic:

```text
format = dat
```

at the top level of `output{}`. Current output format controls are more specific (`format2D`, `format3D`, write flags, etc.). For this project, keep the validated existing output behavior unless there is a documented reason to change it.

## Poisson

Current nextnano++ syntax initializes Poisson through one of the documented initialization groups, such as:

```text
poisson{
    between_fermi_levels{}
}
```

or:

```text
poisson{
    electric_field{
        ...
    }
}
```

Do not promote generic boundary snippets such as `boundary_position{ z_min = dirichlet ... }` into production unless separately verified against the actual nextnano++ docs/parser for the intended context.

---

# 1. Core lexical syntax

## 1.1 Groups and attributes

nextnano++ is a nested group/attribute language:

```text
group_name{
    attribute = value

    nested_group{
        attribute = value
    }
}
```

Attributes are unique inside their scope, while groups may repeat when the grammar permits repeated instances.

Example:

```text
structure{
    region{
        line{
            x = [10.0, 20.0]
        }

        binary{
            name = "GaAs"
        }
    }
}
```

## 1.2 Variables

Variables start with `$`.

```text
$well_start = 20.0
$well_end   = 27.1

structure{
    region{
        line{
            x = [$well_start, $well_end]
        }

        binary{
            name = "GaAs"
        }
    }
}
```

Variable names start with `$` followed by a letter or underscore and then letters, digits, or underscores.

Arrays can also be assigned:

```text
$vector = [1, 3, 5, 7]
$second = $vector(2)
```

## 1.3 Strings

Quoted strings:

```text
name = "GaAs"
```

Unquoted strings are also supported in some contexts, but for material names, file paths, and human-readable names, quoted strings are clearer and safer.

## 1.4 Comments

One-line:

```text
# comment
x = 3.0   # inline comment
```

Multi-line:

```text
!TEXT
This is ignored by the parser.
Do not nest text blocks.
!ENDTEXT
```

## 1.5 Conditional syntax

nextnano++ also supports parser-level conditionals such as `!WHEN`. This is valid syntax, but it is **not needed for the current Demo 14/16 production renderer**. Prefer generating explicit deterministic decks in Python rather than adding avoidable conditional complexity.

---

# 2. Required global simulation definition

For the present 1D GaAs/AlGaAs ACQW problem:

```text
global{
    simulate1D{}

    crystal_zb{
        x_hkl = [1, 0, 0]
        y_hkl = [0, 1, 0]
    }

    substrate{
        name = "GaAs"
    }

    temperature = 300
}
```

Key rules:

- `global{}` is required.
- Exactly one of `simulate1D{}`, `simulate2D{}`, or `simulate3D{}` is selected.
- `simulate1D{}` means the simulation coordinate is `x`.
- `crystal_zb{}` selects zincblende models/routines.
- Exactly two crystal axes are supplied using `x_hkl`, `y_hkl`, `z_hkl`.
- `substrate{}` is required in the documented global configuration.
- `temperature` is in K.

**PROJECT RULE:** Crystal orientation, substrate, and temperature are scientific inputs. Do not silently change them in a renderer refactor.

---

# 3. Spatial grid

## 3.1 1D grid

```text
grid{
    xgrid{
        line{
            pos = 0.0
            spacing = 0.05
        }

        line{
            pos = 50.0
            spacing = 0.05
        }
    }
}
```

Important fields:

- `pos`: position in nm
- `spacing`: grid spacing in nm

The grid may be nonuniform by adding multiple `line{}` entries.

## 3.2 Dimensionality

1D:

```text
grid{
    xgrid{}
}
```

2D:

```text
grid{
    xgrid{}
    ygrid{}
}
```

3D:

```text
grid{
    xgrid{}
    ygrid{}
    zgrid{}
}
```

**PROJECT RULE:** Put grid control under one authoritative scientific configuration. Do not let the renderer and analysis layer independently invent different mesh values.

---

# 4. Structure geometry

Material assignments occur inside:

```text
structure{
    region{
        SHAPE
        MATERIAL
    }
}
```

## 4.1 Entire domain

```text
everywhere{}
```

## 4.2 1D interval

```text
line{
    x = [10.0, 20.0]
}
```

## 4.3 2D shapes — advanced

Documented examples include:

- `rectangle{}`
- `circle{}`
- `trapezoid{}`
- `semiellipse{}`
- `triangle{}`
- `polygon{}`
- `regular_polygon{}`
- `hexagon{}`

Example:

```text
rectangle{
    x = [10.0, 20.0]
    y = [0.0, 5.0]
}
```

## 4.4 3D shapes — advanced

Documented examples include:

- `cuboid{}`
- `sphere{}`
- `cylinder{}`
- `obelisk{}`
- `semiellipsoid{}`
- `cone{}`
- prism/pyramid variants

Example:

```text
cuboid{
    x = [10.0, 20.0]
    y = [0.0, 5.0]
    z = [0.0, 5.0]
}
```

These higher-dimensional shapes are **not part of the current 1D ACQW renderer**.

---

# 5. Material assignment syntax

The current nextnano++ material page documents binary, ternary, quaternary, and quinternary assignments.

## 5.1 Binary

```text
binary{
    name = "GaAs"
}
```

Use for pure GaAs regions.

---

# 6. Constant alloy profiles

## 6.1 Ternary constant — production-critical

```text
ternary_constant{
    name    = "Al(x)Ga(1-x)As"
    alloy_x = 0.55
}
```

For `Al(x)Ga(1-x)As`, `alloy_x = 0.55` means Al0.55Ga0.45As.

`alloy_x` is dimensionless and lies between 0 and 1.

## 6.2 Quaternary constant — advanced

```text
quaternary_constant{
    name    = "Al(x)Ga(y)In(1-x-y)As"
    alloy_x = 0.2
    alloy_y = 0.5
}
```

For a composition `A_x B_y C_(1-x-y) H`:

```text
x + y <= 1
```

## 6.3 Quinternary constant — advanced

`quinternary_constant{}` is documented analogously to the quaternary form.

Not currently used.

---

# 7. Linear spatial alloy grading

## 7.1 Ternary linear — production-critical

1D example:

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
x = 20.0 nm -> Al fraction 0.00
x = 21.0 nm -> Al fraction 0.55
```

Reverse grade:

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

## 7.2 Higher-dimensional interpretation

The documented syntax generalizes to a line in 2D/3D:

```text
ternary_linear{
    name    = "In(x)Al(1-x)As"
    alloy_x = [0.8, 0.2]

    x = [75.0, 125.0]
    y = [10.0, 20.0]
    z = [10.0, 20.0]
}
```

The alloy varies along the start-to-end vector and remains constant in planes perpendicular to that line.

- `x` is used in 1D
- `x`,`y` may be used in 2D
- `x`,`y`,`z` are available in 3D

## 7.3 Quaternary linear — advanced

```text
quaternary_linear{
    name    = "Al(x)Ga(y)In(1-x-y)As"
    alloy_x = [0.2, 0.5]
    alloy_y = [0.1, 0.3]

    x = [20.0, 20.0]
    y = [20.0, 20.0]
    z = [11.0, 20.0]
}
```

## 7.4 Quinternary linear — advanced

`quinternary_linear{}` is documented analogously to quaternary grading.

---

# 8. Parser-enforced material-region rule

**VERIFIED — installed nextnano++ 3.0.0 parser**

The Demo 14 native-linear renderer previously produced a region containing multiple material specifications. The installed parser rejected the deck with an error of the form:

```text
Too many instances of 'ternary_linear'
Terminating program !!
```

Therefore the production rule is:

```text
region{
    line{ x = [a, b] }

    ternary_linear{
        ...
    }
}

region{
    line{ x = [b, c] }

    ternary_constant{
        ...
    }
}

region{
    line{ x = [c, d] }

    ternary_linear{
        ...
    }
}
```

Do **not** put several independent material assignments in the same `region{}`:

```text
# BAD FOR THIS INSTALLED PARSER

region{
    ternary_linear{...}
    ternary_constant{...}
    ternary_linear{...}
}
```

**PROJECT RULE:** one intended material assignment per production `structure{ region{} }`.

---

# 9. Pyramidal and trumpet alloy profiles — advanced / not used

These are real documented nextnano++ alloy models, primarily relevant to 3D quantum-dot-like structures.

## 9.1 Ternary pyramid

```text
ternary_pyramid{
    name    = "In(x)Ga(1-x)As"
    alloy_x = [0.28, 0.80]

    x = [20.0, 0]
    y = [20.0, 0]
    z = [11.0, 1]
}
```

The first spatial value is the apex coordinate and the second is the corresponding component of the axis direction.

The documented composition form is based on:

```text
c = c_min + (c_max - c_min) cos^2(phi)
```

## 9.2 Ternary trumpet

```text
ternary_trumpet{
    name    = "In(x)Ga(1-x)As"
    alloy_x = [0.2, 0.5]

    x = [20.0, 0]
    y = [20.0, 0]
    z = [11.0, 1]

    z0   = 1.25
    rho0 = 0.6
}
```

Quaternary and quinternary pyramid/trumpet forms are also documented.

**PROJECT RULE:** Do not use pyramid/trumpet profiles as clever substitutes for 1D ACQW interface grading. Demo 14/16 should remain linear/imported 1D profiles unless the physical model itself changes.

---

# 10. Imported alloy profiles

This is production-critical for Python-generated Fermi, erf, cosine, or other nonlinear profiles.

## 10.1 Declare the imported file

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

Documented `format` choices are:

```text
DAT
AVS
```

For `.dat` input:

```text
number_of_dimensions = 1
```

is optional if it matches the simulation dimension, but explicit is useful for clarity.

## 10.2 File lookup rules

If:

```text
filename = "al_profile.dat"
```

contains no path and `import{ directory }` is not defined, nextnano++ looks in the directory containing the input file.

An explicit directory may also be used:

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

## 10.3 Assign imported data to a ternary material

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

For ternary material import, the imported alloy profile has exactly **one alloy data component**.

For quaternary material import, it has exactly **two alloy data components**.

## 10.4 Typical 1D `.dat` concept

For a 1D ternary profile, the file contains a spatial coordinate plus one alloy-composition component:

```text
# x_nm    x_Al
0.00      0.55
0.05      0.55
0.10      0.53
0.15      0.49
...
```

Do not confuse “one data component” with “one total text column.” The spatial coordinate is also present.

## 10.5 Scale

Imported data can be multiplied by a scale factor:

```text
file{
    name     = "profile"
    filename = "profile.dat"
    format   = DAT
    scale    = 0.01
}
```

Use only when the source data require a unit/composition conversion.

## 10.6 Headers

The official import documentation states that headers are ignored.

## 10.7 Imported-profile validation

**PROJECT RULE:** Imported data are not trusted merely because `--parse` succeeds.

Compare:

```text
Python authoritative x_Al(x)
        vs
nextnano++ output_alloy_composition
```

numerically.

---

# 11. Optional analytic imports

The `import{}` group can also define analytic functions:

```text
import{
    analytic_function{
        name = "function_1"
        function = "..."
    }
}
```

Documented mathematical operators include:

```text
+  -  *  /  ^
```

with explicit multiplication required (`5*x`, not `5x`).

This is **not currently the production choice** for Demo 14 nonlinear grading, which generates profile files in Python.

---

# 12. ACQW physical topology

The intended coupled-double-well structure must have real outer barriers:

```text
AlGaAs outer barrier
    ↓
graded/interface transition
    ↓
GaAs well 1
    ↓
graded/interface transition
    ↓
AlGaAs central barrier/profile
    ↓
graded/interface transition
    ↓
GaAs well 2
    ↓
graded/interface transition
    ↓
AlGaAs outer barrier
```

In shorthand:

```text
AlGaAs | GaAs well 1 | AlGaAs barrier | GaAs well 2 | AlGaAs
```

A renderer using:

```text
everywhere{} -> GaAs
```

plus only one central AlGaAs barrier does **not** create the intended finite coupled quantum wells.

**PROJECT RULE:** physical confinement must come from material band offsets, not merely from numerical quantum-region boundaries.

---

# 13. Working-reference rendering pattern

Project reference decks demonstrate a useful pattern:

1. establish the AlGaAs matrix/background,
2. define GaAs wells and graded interface regions explicitly,
3. verify the final structure using generated composition/material output.

Because region overlap/precedence can be subtle, do not infer the final physical structure merely from text order. Validate the realized structure.

---

# 14. Structure/composition outputs

For renderer validation, request alloy composition:

```text
structure{
    output_alloy_composition{}

    ...
}
```

This output is essential for Demo 16.

Recommended additional structural diagnostics where useful:

```text
output_region_index{}
output_material_index{}
```

The full comparison chain should be:

```text
requested parameters
    ↓
derived geometry
    ↓
Python x_Al(x)
    ↓
rendered nextnano++ regions/import file
    ↓
nextnano++ generated structure
    ↓
output_alloy_composition
    ↓
numerical comparison
```

---

# 15. Classical band model

`classical{}` selects bands and controls bulk-like outputs.

For the present workflow:

```text
classical{
    Gamma{}
    HH{}

    output_bandedges{}
}
```

The current docs also provide:

```text
LH{}
SO{}
X{}
Delta{}
L{}
```

when required.

## Band edges

```text
classical{
    Gamma{}
    HH{}

    output_bandedges{}
}
```

For the ACQW workflow, Gamma conduction and HH valence edges are the main structural physics diagnostics.

Carrier-density outputs exist, for example:

```text
output_carrier_densities{}
```

but are not central to the current neutral quantum-well validation.

---

# 16. Quantum model

## 16.1 Quantum region

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

Documented region extent attributes include:

```text
x
y
z
```

depending on simulation dimensionality.

For the current `simulate1D{}` workflow, the quantum domain is defined along `x`.

## 16.2 Single-band models

These trigger single-band effective-mass Schrödinger equations:

```text
Gamma{}
L{}
X{}
Delta{}
HH{}
LH{}
SO{}
```

The current project mainly uses:

```text
Gamma{
    num_ev = ...
}

HH{
    num_ev = ...
}
```

`num_ev` controls the number of eigenvalues requested.

## 16.3 k.p models — advanced

The current nextnano++ quantum-region grammar also includes:

```text
kp_6band{}
kp_8band{}
```

These are valid quantum models, but do not replace the current single-band Gamma/HH workflow without an explicit scientific decision and parser/analysis updates.

---

# 17. Quantum output states

`output_states{}` was added in nextnano++ 3.0.0 and controls wavefunction output.

Example:

```text
output_states{
    max_num       = 4
    envelopes     = yes
    probabilities = yes
    in_one_file   = yes
}
```

Important documented attributes include:

```text
max_num
all_k_points
envelopes
envelopes_CB_HH_LH_SO
probabilities
probability_components
probabilities_partial_CB_HH_LH_SO
spinor_composition
spinor_composition_CB_HH_LH_SO
in_one_file
scale
energy_shift
include_energies_in_shifted_files
```

For the current ACQW pipeline, the critical outputs are:

```text
envelopes = yes
probabilities = yes
```

For 1-band models, the solver outputs envelope-function and probability data used by state tracking and dipole calculations.

The energy spectrum is written to `energy_spectrum_*.dat`.

---

# 18. Running the quantum solve

Defining `quantum{}` specifies the model. The solve is triggered inside `run{}`:

```text
run{
    quantum{}
}
```

`run{}` is required.

Documented run modes also include:

```text
structure_only{}
strain{}
poisson{}
current_poisson{}
quantum{}
quantum_density{}
quantum_poisson{}
quantum_current_poisson{}
quantum_optics{}
```

Only use modes consistent with the intended physical workflow.

---

# 19. Poisson — optional for broader workflows

Current nextnano++ syntax requires the `poisson{}` group if Poisson initialization/solution is used.

One documented initialization example:

```text
poisson{
    between_fermi_levels{}
}
```

Other initialization choices include:

```text
import_potential{}
electric_field{}
charge_neutral{}
zero_charge{}
```

The docs require exactly one compatible initialization mode when `poisson{}` is used.

Documented solver controls include:

```text
newton_solver{}
linear_solver{}
bisection{}
```

and outputs such as:

```text
output_potential{}
output_electric_field{}
```

**Current ACQW note:** do not add self-consistent Poisson physics to Demo 14/16 unless it is already part of the validated scientific model.

---

# 20. Impurities and doping — advanced / not currently central

## 20.1 Define an impurity

```text
impurities{
    donor{
        name       = "n-Si"
        degeneracy = 2
        energy     = 0.0058
    }
}
```

Acceptor definitions are also supported.

## 20.2 Assign constant doping to a structure region

```text
structure{
    region{
        doping{
            constant{
                name = "n-Si"
                conc = 1.0e18
                add  = no
            }
        }

        ...
    }
}
```

`conc` is in cm^-3.

## 20.3 Linear doping

```text
doping{
    linear{
        name = "n-Si"
        conc = [1.0e18, 2.0e18]
        x    = [50.0, 100.0]
        add  = no
    }
}
```

## 20.4 Gaussian/imported doping

The current grammar also supports Gaussian 1D/2D/3D forms and imported doping profiles.

These are not needed for the present undoped ACQW validation workflow unless the scientific scope changes.

---

# 21. Contacts and currents — advanced / not currently used

`contacts{}` defines available boundary conditions for current and Poisson equations. The current docs include contact/boundary groups such as:

```text
fermi{}
fermi_electron{}
fermi_hole{}
schottky{}
ohmic{}
zero_field{}
charge_neutral{}
```

`currents{}` configures drift-diffusion current calculations and may include:

```text
electron_mobility{}
hole_mobility{}
recombination_model{}
linear_solver{}
output_fermi_levels{}
output_currents{}
```

**Important:** Do not use generic secondary-source examples such as a made-up `contact{ name=... voltage=... }` syntax unless the exact current nextnano++ keyword page verifies it. Contacts/currents are outside the present ACQW renderer scope.

---

# 22. General output configuration

Current nextnano++ syntax uses:

```text
output{
    directory = "../output/example"
}
```

Other documented options include:

```text
mandatory_path
set_origin{}
format2D
format3D
silent
write_avs_v
write_origin_plt
write_gnuplot_plt
use_gnuplot_one_file
section{}
section1D{}
section2D{}
material_parameters{}
```

For command-line-driven project workflows, the solver is commonly given an explicit output directory on the command line. Avoid having an input-file `mandatory_path = yes` accidentally override the run harness.

---

# 23. Command-line validation and production execution

The installed nextnano++ executable supports modes such as:

```text
--parse
--structure
```

and options including:

```text
--database <database_file>
--license <license_file>
--inputdirectory <dir>
--outputdirectory <dir>
--noautooutdir
--threads <n>
```

Project known-good production command pattern:

```text
nextnano++_Intel_64bit.exe \
    --license <License_nnp.lic> \
    --database <database.nnp> \
    --threads 4 \
    --outputdirectory <output_dir> \
    --noautooutdir \
    <input_file>
```

The Python wrapper must inspect the subprocess return code before post-processing.

---

# 24. Three levels of validation

## Level 1 — Syntax

Question:

```text
Can the installed nextnano++ parser read this deck?
```

Use:

```text
nextnano++ --parse case.in
```

This catches grammar errors such as the previous multi-material `region{}` failure.

A parser PASS does **not** prove the structure is physically correct.

## Level 2 — Structure

Question:

```text
Did nextnano++ build the intended material composition?
```

Use structure generation plus:

```text
output_alloy_composition{}
```

Compare expected and realized `x_Al(x)`.

This catches errors such as the previous missing outer barriers.

## Level 3 — Physics

Question:

```text
Does the correct structure produce physically credible quantum states?
```

Check:

- Gamma/HH band edges
- energy spectra
- wavefunctions
- probability density
- state localization
- boundary leakage
- orthonormality/state tracking
- mesh convergence where required
- downstream chi2 only after solver/QC success

---

# 25. Demo 14 / Demo 16 renderer invariants

Every generated ACQW candidate should satisfy:

1. `global{ simulate1D{} }` and the validated zincblende orientation are correct.
2. The grid is generated from the authoritative scientific mesh configuration.
3. Every production material region has one intended material assignment.
4. Left and right AlGaAs outer barriers exist.
5. Two GaAs wells exist at the intended locations.
6. The central AlGaAs barrier/profile exists.
7. All four GaAs/AlGaAs transitions are represented.
8. The intended profile satisfies allowed alloy bounds.
9. If grades overlap, no fake flat Al0.55 plateau is invented.
10. Native-linear and imported profiles are constructed from the same authoritative `x_Al(x)` model.
11. Local grading-width measurement examines the intended interface, not the opposite side of a whole well.
12. `output_alloy_composition{}` is available for structure-validation runs.
13. The quantum region extends into physical barriers; numerical boundaries do not substitute for confinement.
14. Solver nonzero return codes stop analysis.
15. Missing expected output files stop analysis.
16. No fabricated objective is assigned after technical failure.

---

# 26. ACQW native-linear example skeleton

This is a structural example, not a complete scientific production deck.

```text
$domain_end = 50.0
$x0 = 0.0

global{
    simulate1D{}

    crystal_zb{
        x_hkl = [1, 0, 0]
        y_hkl = [0, 1, 0]
    }

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

    # Each material segment is a separate region.

    region{
        line{ x = [0.0, 10.0] }

        ternary_constant{
            name    = "Al(x)Ga(1-x)As"
            alloy_x = 0.55
        }
    }

    region{
        line{ x = [10.0, 10.7] }

        ternary_linear{
            name    = "Al(x)Ga(1-x)As"
            alloy_x = [0.55, 0.0]
            x       = [10.0, 10.7]
        }
    }

    # Additional regions:
    # GaAs well 1
    # grade up
    # central barrier/profile
    # grade down
    # GaAs well 2
    # grade up into right outer barrier
    # right outer barrier
}

classical{
    Gamma{}
    HH{}
    output_bandedges{}
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
            max_num       = 4
            envelopes     = yes
            probabilities = yes
            in_one_file   = yes
        }
    }
}

run{
    quantum{}
}
```

---

# 27. Imported-profile ACQW skeleton

```text
import{
    file{
        name                 = "al_profile"
        filename             = "al_profile.dat"
        format               = DAT
        number_of_dimensions = 1
    }
}

structure{
    output_alloy_composition{}

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

Whether the entire domain or only specific profile spans should use `ternary_import{}` is a renderer-design decision. Validate the actual generated composition rather than assuming the file/region combination is correct.

---

# 28. Advanced alloy syntax quick reference

| Syntax | Purpose | Current ACQW use |
|---|---|---|
| `binary{}` | pure binary material | **Yes** |
| `ternary_constant{}` | constant ternary composition | **Yes** |
| `ternary_linear{}` | linear ternary spatial grade | **Yes** |
| `ternary_import{}` | imported ternary profile | **Yes** |
| `ternary_pyramid{}` | pyramidal angular 3D alloy model | No |
| `ternary_trumpet{}` | trumpet/horn 3D alloy model | No |
| `quaternary_constant{}` | constant 2-composition alloy | Future/general |
| `quaternary_linear{}` | linearly graded 2-composition alloy | Future/general |
| `quaternary_import{}` | imported 2-component alloy profile | Future/general |
| `quaternary_pyramid{}` | 3D quaternary pyramid | No |
| `quaternary_trumpet{}` | 3D quaternary trumpet | No |
| `quinternary_constant{}` | higher-order alloy | Future/general |
| `quinternary_linear{}` | higher-order linear alloy | Future/general |
| `quinternary_import{}` | higher-order imported alloy | Future/general |
| `quinternary_pyramid{}` | higher-order 3D profile | No |
| `quinternary_trumpet{}` | higher-order 3D profile | No |

---

# 29. Evidence hierarchy for future renderer changes

When deciding whether syntax is valid, use this order:

1. **Current official nextnano++ documentation**
2. **Actual installed nextnano++ 3.0.0 `--parse` behavior**
3. **`--structure` and actual generated structure/composition output**
4. **Official examples shipped with the installed nextnano++ package**
5. **Previously successful project input files and raw logs**
6. **Repository unit/integration tests**
7. Secondary summaries or generated syntax notes

A Python test or secondary guide cannot overrule a contradiction from the actual installed parser.

---

# 30. Local authoritative references

Useful installed examples:

```text
C:\Code\optics\nextnano\2026_07_03\nextnano++\examples\basics\import-dat_1D.nnp

C:\Code\optics\nextnano\2026_07_03\nextnano++\examples\basics\import-dat_1D_ternary.dat
```

Project-specific references:

- known-working Ramesh-style double-quantum-well input files
- Demo 11 validated paper structure
- Demo 14 production renderer after parser/outer-barrier fixes
- Demo 16 deterministic renderer/structure stress cases

---

# 31. Official documentation pages used for this guide

Current nextnano++ documentation:

- Input syntax  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/input_syntax/index.html

- global{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/global.html

- grid{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/grid.html

- structure region material assignment  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/structure/region_material.html

- structure region shapes  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/structure/region_shapes.html

- import{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/import.html

- impurities{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/impurities.html

- structure region doping{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/structure/region/doping.html

- classical{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/classical/index.html

- quantum{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/quantum/index.html

- quantum region{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/quantum/region/index.html

- Gamma/L/X/Delta/HH/LH/SO quantum models  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/quantum/region/Gamma_L_X_Delta_HH_LH_SO.html

- quantum output_states{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/quantum/region/output_states.html

- poisson{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/poisson.html

- contacts{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/contacts.html

- currents{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/currents/index.html

- output{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/output.html

- run{}  
  https://www.nextnano.com/docu/nextnanoplus/latest/user_guide/keywords/run/index.html

---

# 32. Final project rule

For Demo 14, Demo 16, and future Demo 15:

```text
requested design
    ↓
authoritative Python geometry/x_Al(x)
    ↓
valid nextnano++ syntax
    ↓
nextnano++ realized structure
    ↓
validated band profile
    ↓
validated quantum states
    ↓
only then downstream chi2 / optimization
```

The simulation is trustworthy only when **both** syntax and realized physical structure are correct.
