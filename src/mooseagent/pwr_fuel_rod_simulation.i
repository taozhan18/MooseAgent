# Steady-State Thermomechanical Calculations of a PWR Fuel Rod
# This input card simulates the thermal and mechanical behavior of a PWR fuel rod under operational conditions.

[Mesh]
  [./geom]
    type = GeneratedMeshGenerator  # Specifies the type of mesh generator to use.
    dim = 3  # The dimension of the mesh, in this case, it is a 3D mesh.
    nx = 20  # Number of elements in the x-direction (radial direction).
    ny = 20  # Number of elements in the y-direction (axial direction).
    nz = 20  # Number of elements in the z-direction (circumferential direction).
  [../]
[]

[Variables]
  [./T]
    order = FIRST  # Specifies the order of the variable, FIRST indicates linear approximation for temperature.
  [../]
  [./stress]
    order = FIRST  # Specifies the order of the variable, FIRST indicates linear approximation for stress.
  [../]
[]

[Problem]
  coord_type = RZ  # Specifies the coordinate system used for the problem, RZ indicates cylindrical coordinates (radius and z).
[]

[Functions]
  [./heat_generation]
    type = ParsedFunction  # Specifies the type of function, here it is a parsed function that can evaluate expressions.
    symbol_names = 'H'  # Names of the symbols used in the expression.
    symbol_values = '1.0'  # Values corresponding to the symbols defined above.
    expression = 'H * cos(pi * z / L)'  # The cosine heat generation distribution along the height of the rod.
  [../]
[]

[Kernels]
  [./heat_conduction]
    type = HeatConduction  # Specifies the kernel type for heat conduction problems.
    variable = T  # The variable that this kernel operates on, in this case, the temperature T.
  [../]
  [./stress_calculation]
    type = TotalLagrangianStressDivergenceCentrosymmetricSpherical  # Kernel for stress calculations in spherical coordinates.
    variable = stress  # The variable this kernel operates on, in this case, the stress.
  [../]
[]

[BCs]
  [./adiabatic_top]
    type = NeumannBC  # Specifies a Neumann boundary condition for adiabatic conditions.
    variable = T  # The variable this boundary condition applies to, which is the temperature T.
    boundary = top  # The boundary where this condition applies, here it is the top boundary.
    value = 0  # No heat transfer at the top boundary.
  [../]
  [./adiabatic_bottom]
    type = NeumannBC  # Specifies a Neumann boundary condition for adiabatic conditions.
    variable = T  # The variable this boundary condition applies to, which is the temperature T.
    boundary = bottom  # The boundary where this condition applies, here it is the bottom boundary.
    value = 0  # No heat transfer at the bottom boundary.
  [../]
  [./isothermal_right]
    type = DirichletBC  # Specifies a Dirichlet boundary condition for isothermal conditions.
    variable = T  # The variable this boundary condition applies to, which is the temperature T.
    boundary = right  # The boundary where this condition applies, here it is the right boundary.
    value = 293  # The temperature at the right boundary.
  [../]
[]

[Materials]
  [./fuel_material]
    type = GenericConstantMaterial  # Specifies a material with constant properties for the fuel pellet.
    prop_names = 'thermal_conductivity thermal_expansion'  # Names of the material properties defined.
    prop_values = 'k(T) 7.107e-6'  # Values corresponding to the material properties: thermal conductivity and thermal expansion coefficient.
  [../]
  [./cladding_material]
    type = GenericConstantMaterial  # Specifies a material with constant properties for the cladding.
    prop_names = 'thermal_conductivity thermal_expansion'  # Names of the material properties defined.
    prop_values = '0.15 5.5e-6'  # Values corresponding to the material properties: thermal conductivity and thermal expansion coefficient.
  [../]
[]

[Executioner]
  type = Steady  # Specifies the type of executioner for steady-state simulations.
[]

[Outputs]
  csv = true  # Specifies that the output should be in CSV format.
[]
