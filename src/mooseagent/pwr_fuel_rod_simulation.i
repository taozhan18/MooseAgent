# Pressurized Water Reactor (PWR) Fuel Rod Steady-State Thermomechanical Simulation

[Mesh]
# Define the mesh for the fuel rod geometry, including the fuel pellet and cladding.
# Fuel pellet diameter = 8.192 mm, Cladding inner diameter = 8.36 mm,
# Cladding outer diameter = 9.5 mm, Height = 3657 mm.
# A cylindrical mesh is used with finer resolution in the radial direction.
mesh_type = cylindrical
mesh_size = 0.1 # Adjust as necessary for finer resolution
fuel_pellet_diameter = 8.192 mm
cladding_inner_diameter = 8.36 mm
cladding_outer_diameter = 9.5 mm
rod_height = 3657 mm

[Variables]
# Define dependent variables for simulation.
# Temperature (T), thermal stress, and thermal strain.
[ScalarField]
variables = T

[Global]
# Thermal stress and strain will be derived from the temperature field.
thermal_stress = compute_stress(T)
thermal_strain = compute_strain(T)

[Kernels]
# Kernels include heat conduction equation and mechanical response to thermal expansion.
[HeatConduction]
# Using temperature-dependent thermal conductivity for the fuel pellet and cladding.
conductivity = function(T) # Define as needed

[MechanicalResponse]
# Incorporate thermal expansion coefficients for both materials.
thermal_expansion_coefficient_fuel = 1.2e-5
thermal_expansion_coefficient_cladding = 1.0e-5

# Define heat generation term with cosine distribution along the axial direction.
heat_generation = cos_distribution(z, amplitude = 1.0) 

[BC]
# Define boundary conditions for the simulation.
# Adiabatic boundary conditions at the top and bottom of the fuel rod.
[BC_Adiabatic]
location = top
heat_flux = 0.0

[BC_Adiabatic]
location = bottom
heat_flux = 0.0

# Fixed temperature conditions on the right side, interpolating between inlet and outlet temperature.
[BC_Temperature]
location = right_side
T_inlet = 293 K
T_outlet = 333 K

# Define internal pressure boundary condition in the gap between fuel pellet and cladding.
[BC_Pressure]
pressure = 2 MPa

[Executioner]
# Specify execution parameters for the steady-state solver.
solver_type = steady_state
max_iterations = 100
convergence_criteria = 1e-6

[Outputs]
# Define output parameters for simulation results.
# Output temperature distribution, stress distribution, and other relevant fields.
output_fields = T, thermal_stress, thermal_strain
output_format = VTK
