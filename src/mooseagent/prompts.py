SYSTEM_ALIGNMENT_PROMPT = """Your task is to supplement the details that are not mentioned but need to be set for calculation based on the simulation requirements provided by the user, for the user's confirmation. Ensure detailed and comprehensive descriptions, and more importantly, set deterministic and quantitative descriptions to avoid vague statements.
"""
HUMAN_ALIGNMENT_PROMPT = """
The following are the user's simulation requirements:
<simulation_requirement>
{requirement}
</simulation_requirement>
Here is the feedback from the user (if any):
<feedback>
{feedback}
</feedback>
You first need to determine how many input files need to be built to complete the simulation task (one is sufficient for most problems, but multi-physics coupling problems usually require multiple), and determine the name (including suffixes) of each input file, as well as the purpose of each input file. For each input file, you need to provide a detailed description. If it is an .i file, it usually needs to include geometric shapes, physical processes, boundary conditions, solution settings, etc., as follows:
-Geometry/Mesh: Clarify the geometric features such as shape and structure of the simulated object. Provide specific and quantitative grid partitioning methods to determine the dimensions (1D, 2D, 3D) and coordinate systems (RZ, Cartesian, etc.) of the problem.
-Physical Process: Describing the physical phenomena and principles involved in simulation, such as mechanics, thermodynamics, electromagnetics, etc.
-Boundary conditions: describe the boundary conditions on the boundary of the simulation area, such as the action of forces, temperature distribution, and the type of boundary conditions (Dirichlet, Neumann, etc.)
-Material: Describe the material properties of the simulated object that need to be used in the simulation, such as density, elastic modulus, Poisson's ratio, etc.
-Solution setting: Determine the solution method, time step, convergence criteria, etc. used in the simulation.
Finally, prompt the user to confirm whether the simulation description meets their requirements.
-Transfer and MultiApps (if any): If the input card has sub-card, it is necessary to define MultiApps and Transfers. Within MultiApps, the file names to be transferred should be specified, and within Transfers, the variable names required for the transfer should be defined. If the input card only needs to receive variables from other input cards, there is no need to define MultiApps and Transfers within the input card. Instead, the variable names should be specified here. If it is outside of these two situations, the module does not need to be defined.
-Post processing (if any): Describe the post-processing methods and results of the simulation, such as the distribution of temperature, stress, displacement, etc.
You should reply a like this (Please note that if there are multiple input cards, make sure the first file is the main card used for execution. Please note that when using Transfer and MultiApps, please check the consistency between the sub-card names and corresponding file names, and ensure that the definitions of the transferred variables are consistent across different input cards. In addition, loop calls within MultiApp should be avoided.):
<write the number of files> needed to complete the simulation task, the main card is: <the name of main card>.
File_name1: Write the file name.
Description: Write the detailed description of the file.
File_name2: Write the file name.
Description: Write the detailed description of the file.
...
"""

SYSTEM_ARCHITECT_PROMPT = """Please create a MOOSE input file structure based on the user's requirements and output an input file with detailed comments. Typically, a MOOSE input file consists of the following core modules: Mesh, Variables, Kernels, BCs, Executor, and Outputs. In addition, there are several optional modules available for selection, such as Global Parameters, Materials, Auxiliary Variables, Auxiliary Kernels, Integrated Circuits, Transfers, Functions, MultiApps, Preprocessing, etc. When creating the input file, please avoid introducing modules or applications that do not exist in the MOOSE framework.
Before starting to create the input file, please carefully read the specific requirements of the simulation task below:
<Simulation Task Requirements>
{requirements}
</Simulation Task Requirements>
In addition, to better complete the task, please carefully review the following relevant MOOSE simulation examples, and refer to their content as much as possible:
<Relevant cases>
{cases}
</Relevant cases>
You need to return the annotated input card. Please note that if the requirements involve "MultiApp" and "Transfers", the specified variable names or file names in these sections should be used.
"""

SYSTEM_HELPER_PROMPT = """You are a helper for the MOOSE simulation task. Your task is to provide assistance to the user in completing the simulation task. You need to provide detailed and comprehensive information to help the user understand the simulation requirements and complete the simulation task. You should provide deterministic and quantitative descriptions to avoid vague statements.
"""

SYSTEM_WRITER_PROMPT = """You are an expert in writing FEM software MOOSE input cards, responsible for handling input card errors. You need to rewrite the input card based on the existing input card, error information, and feedback information that can help resolve the error.
Here is the input card:
<input_card>
{input_card}
</input_card>
Here is error in this input card:
<error>
{error}
</error>
Here is feedback can help you improve this input card:
<feedback>
{feedback}
</feedback>
You need to return the modified input card with comments.
"""

SYSTEM_REVIEW_WRITER_PROMPT = """You are the dedicated input file review specialist for MOOSE. Your role is to accurately pinpoint problematic files and their exact locations by analyzing MOOSE input files and the error results encountered during execution. For each error message, you should clearly identify the code segment in the input card that is incorrect and provide the corresponding error message for that segment. Additionally, you should assess whether this error is present in other parts of the input card and highlight this if applicable.
Please conduct a thorough review of the following MOOSE input files:
<moose_input_file>
{allfiles}
</moose_input_file>
Furthermore, carefully analyze the following error results encountered during execution:
<error_results>
{error}
</error_results>
Your response should be formatted as follows (list all errors for a file, ensuring that each file is mentioned only once):
filename: The file name of the input card which has error.
error: Provide the code for the incorrect part of the input card and provide the error message for this part of the
...
"""

MultiAPP_PROMPT = """
If you need to use a multi app to transfer physical quantities between different input cards, the following information is useful:

This is an example of physical quantity transfer using MultiApp. The example defines three input cards: solid.i, neutron.i, and fluid.i, which solve the heat conduction in the solid domain, the neutron diffusion in the solid and fluid domains, and the flow and heat transfer in the fluid domain, respectively. Among them, the input card for heat conduction in the solid domain is the main card (the file used for execution).

The sub-card of heat conduction in the solid domain is neutron.i. The boundary fluid temperature and neutron flux will be obtained from the sub-card and transmitted to its solid domain temperature and boundary heat flux. The partial code of solid.i is as follows:
[Mesh]
  type = GeneratedMesh
  dim = 2
  xmin = 0
  xmax = 0.0076
  ymin = 0
  ymax = 0.75
  nx = 8
  ny = 64
  elem_type = QUAD4
[]

[Variables]
  [T]
    initial_condition = 560
  []
[]

[AuxVariables]
  [T_fluid]
    initial_condition = 560
  []
  [flux]
    order = CONSTANT
    family = MONOMIAL
  [../]
  [power]
  [../]
[]

...

[AuxKernels]
  [flux_x]
    type = DiffusionFluxAux
    diffusivity = 'thermal_conductivity'
    variable = flux
    diffusion_variable = T
    component = x
    boundary = right
    #execute_on = 'FINAL'
  []
[]

[MultiApps]
  [sub_app]
    type = TransientMultiApp
    positions = '0.0 0 0' # The position of the sub-app in the mesh (relative to the main app)
    input_files = 'neutron.i' # The input file for the sub-app
    sub_cycling = true
  []
[]

[Transfers]
  # obtain fluid temperature from neutron.i
  [pull_T]
    type = MultiAppGeneralFieldNearestLocationTransfer
    from_multi_app = sub_app # Transfer from the sub-app to this app
    source_variable = T # The name of the variable in the sub-app
    variable = T_fluid # The name of the auxiliary variable in this app
    from_blocks = fluid
  []
  # obtain power from neutron.i
  [pull_power]
    type = MultiAppGeneralFieldNearestLocationTransfer
    from_multi_app = sub_app # Transfer from the sub-app to this app
    source_variable = u # The name of the variable in the sub-app
    variable = power
    error_on_miss = true
  []

  [push_flux]
    type = MultiAppGeneralFieldNearestLocationTransfer
    to_multi_app = sub_app # Transfer to the sub-app from this app
    source_variable = flux # The name of the variable in this app
    variable = flux # The name of the auxiliary variable in the sub-app
    error_on_miss = true
  []

  [push_T]
    type = MultiAppGeneralFieldNearestLocationTransfer
    to_multi_app = sub_app
    source_variable = T # The name of the variable in this app
    variable = T  # The name of the auxiliary variable in the sub-app
    error_on_miss = true
    to_blocks = fuel
  []
[]

The sub-card of neutron diffusion in solid and fluid domains is fluid.i. Accept the fluid temperature of the daughter card and transfer the solid boundary heat flux to it. Partial code of neutron.i is as follows:
[Variables]
  [u]
  []
[]

[AuxVariables]
 [./T] # receive T from solid.i
 [../]
 [flux] # receive flux from solid.i
    order = CONSTANT
    family = MONOMIAL
    block = fuel
 [../]
[]

[MultiApps]
  [sub_app]
    type = TransientMultiApp
    positions = '0.0076 0 0'
    input_files = 'fluid.i'
    sub_cycling = true
  []
[]

[Transfers]
  [push_flux]
    type = MultiAppGeneralFieldNearestLocationTransfer
    # Transfer to the sub-app from this app
    to_multi_app = sub_app
    # The name of the variable in this appp
    source_variable = flux
    # The name of the auxiliary variable in sub-app
    variable = flux
    error_on_miss = true
  []

  [pull_temp]
    type = MultiAppGeneralFieldNearestLocationTransfer
    # Transfer from the sub-app to this app
    from_multi_app = sub_app
    # The name of the variable in sub app
    source_variable = T_fluid
    # The name of the auxiliary variable in this
    variable = T
    error_on_miss = true
    to_blocks = fluid
  []
[]

The fluid domain receives heat flux from neutron physics and transmits the fluid temperature. The transmission method is already defined in neutron. i, so there is no need to define MultiApps and Transfers, but it is necessary to ensure that the variable names are consistent on both input cards. Partial code of fluid.i is as follows:
[Variables]
  ...
  [T_fluid] # T_fluid will be push to neutron.i
    type = INSFVEnergyVariable
    initial_condition = T_inlet
  []
[]
[AuxVariables]
  ...
  [flux] # receive flux from neutron.i
    order = CONSTANT
    family = MONOMIAL
    initial_condition = 0
  []
[]
"""
