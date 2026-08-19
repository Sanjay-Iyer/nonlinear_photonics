# Demo 20 - Generated nextnano++ Input Examples

The growth coordinate is `x` in nextnano++ and is reported as `z` in plots. Every width below is a full start-to-end transition width centred on I1-I4.

## Abrupt

Requested by Python:

```json
{
  "profile": "abrupt",
  "widths_nm": {
    "I1": 0,
    "I2": 0,
    "I3": 0,
    "I4": 0
  }
}
```

Actual generated nextnano++ syntax:

```text
structure{
    output_region_index{ boxes = no }
    output_material_index{ boxes = no }
    output_alloy_composition{ boxes = no }
    region{
        everywhere{}
        ternary_constant{ name = "Al(x)Ga(1-x)As"  alloy_x = 0.550000 }
    }
    region{
        line{ x = [0.000000, 30.000000] }
        contact{ name = qw_contact }
    }
    region{
        line{ x = [9.100000, 16.200000] }
        binary{ name = "GaAs" }
    }
    region{
        line{ x = [18.000000, 20.900000] }
        binary{ name = "GaAs" }
    }
}
```

## Linear 0.7 nm

Requested by Python:

```json
{
  "profile": "linear",
  "widths_nm": {
    "I1": 0.7,
    "I2": 0.7,
    "I3": 0.7,
    "I4": 0.7
  }
}
```

Actual generated nextnano++ syntax:

```text
structure{
    output_region_index{ boxes = no }
    output_material_index{ boxes = no }
    output_alloy_composition{ boxes = no }
    region{
        everywhere{}
        ternary_constant{ name = "Al(x)Ga(1-x)As"  alloy_x = 0.550000 }
    }
    region{
        line{ x = [0.000000, 30.000000] }
        contact{ name = qw_contact }
    }
    region{
        line{ x = [9.100000, 16.200000] }
        binary{ name = "GaAs" }
    }
    region{
        line{ x = [18.000000, 20.900000] }
        binary{ name = "GaAs" }
    }
    region{
        line{ x = [8.750000, 9.450000] }
        ternary_linear{ name = "Al(x)Ga(1-x)As"  alloy_x = [0.550000, 0.000000]  x = [8.750000, 9.450000] }
    }
    region{
        line{ x = [15.850000, 16.550000] }
        ternary_linear{ name = "Al(x)Ga(1-x)As"  alloy_x = [0.000000, 0.550000]  x = [15.850000, 16.550000] }
    }
    region{
        line{ x = [17.650000, 18.350000] }
        ternary_linear{ name = "Al(x)Ga(1-x)As"  alloy_x = [0.550000, 0.000000]  x = [17.650000, 18.350000] }
    }
    region{
        line{ x = [20.550000, 21.250000] }
        ternary_linear{ name = "Al(x)Ga(1-x)As"  alloy_x = [0.000000, 0.550000]  x = [20.550000, 21.250000] }
    }
}
```

## Fermi-like 0.7 nm

Requested by Python:

```json
{
  "profile": "fermi",
  "widths_nm": {
    "I1": 0.7,
    "I2": 0.7,
    "I3": 0.7,
    "I4": 0.7
  }
}
```

Actual generated nextnano++ syntax:

```text
import{
    file{ name = "al_profile"  filename = "al_profile.dat"  format = DAT  number_of_dimensions = 1 }
    output_imports{}
}

structure{
    output_region_index{ boxes = no }
    output_material_index{ boxes = no }
    output_alloy_composition{ boxes = no }
    region{
        everywhere{}
        ternary_constant{ name = "Al(x)Ga(1-x)As"  alloy_x = 0.550000 }
    }
    region{
        line{ x = [0.000000, 30.000000] }
        contact{ name = qw_contact }
    }
    region{
        line{ x = [0.000000, 30.000000] }
        ternary_import{ name = "Al(x)Ga(1-x)As"  import_from = "al_profile" }
    }
}
```

Imported DAT sample (first/last rows):

```text
0.000000 0.55000000
0.050000 0.55000000
0.100000 0.55000000
0.150000 0.55000000
...
29.850000 0.55000000
29.900000 0.55000000
29.950000 0.55000000
30.000000 0.55000000
```
