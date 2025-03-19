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
You first need to determine how many input files need to be built to complete the simulation task (one is sufficient for most problems, but multi-physics coupling problems usually require multiple), and determine the name (including suffixes) of each input file, as well as the purpose of each input file. For each input file, you need to provide a detailed description. It is especially important to clearly specify in the description if there are the same physical quantities between different files to ensure consistency. If it is an .i file, it usually needs to include geometric shapes, physical processes, boundary conditions, solution settings, etc., as follows:
-Geometry/Mesh: Clarify the geometric features such as shape and structure of the simulated object. Provide specific and quantitative grid partitioning methods to determine the dimensions (1D, 2D, 3D) and coordinate systems (RZ, Cartesian, etc.) of the problem.
-Physical Process: Describing the physical phenomena and principles involved in simulation, such as mechanics, thermodynamics, electromagnetics, etc.
-Boundary conditions: describe the boundary conditions on the boundary of the simulation area, such as the action of forces, temperature distribution, and the type of boundary conditions (Dirichlet, Neumann, etc.)
-Material: Describe the material properties of the simulated object that need to be used in the simulation, such as density, elastic modulus, Poisson's ratio, etc.
-Solution setting: Determine the solution method, time step, convergence criteria, etc. used in the simulation.
Finally, prompt the user to confirm whether the simulation description meets their requirements.
-Post processing (if any): Describe the post-processing methods and results of the simulation, such as the distribution of temperature, stress, displacement, etc.
You should reply a list:
<write the number of files> needed to complete the simulation task.
File_name: Write the file name.
Description: Write the detailed description of the file.
...
File_name: Write the file name.
Description: Write the detailed description of the file.
"""

SYSTEM_ARCHITECT_PROMPT = """You need to draft a template for MOOSE input cards. Usually, MOOSE input cards include the following modules: Mesh,Variables,Kernels,BCs,Executioner,Outputs. Besides, there are some optional modules: GlobalParams,Materials,AuxVariables,AuxKernels,ICs,Transfers,Functions,MultiApps,Preconditioning,Executioners,Transfers, etc. For modules that you consider to have high uncertainty, please describe the functions that the module needs to complete in natural language. At the same time, provide relevant information to search for applications in MOOSE that can complete this function. Please note that 'uncertain' refers to not knowing what application to use in MOOSE to implement simulation requirements, rather than setting up simulation tasks. Be careful not to create applications that do not exist in MOOSE.
Firstly, please carefully read the following simulation task requirements for MOOSE:
<Simulation Task Requirements>
{requirements}
</Simulation Task Requirements>
Next, please carefully review the following MOOSE simulation cases:
<Simulation Case>
{cases}
</Simulation Case>
When drafting the MOOSE input card template, please follow the following rules:
1. Refer to input cards from existing cases as much as possible.
2. For the modules that are clearly defined in the requirements and cases, provide corresponding code directly in the template with annotations.
3. For unclear modules, provide a detailed description of the functionality that the code needs to implement.
4. When modules are unsure which app in moose to use to complete a task, list the content that needs to be retrieved item by item in order to improve the input card. Merge relevant content as much as possible to reduce the number of retrieves. The retrieved content should describe the functions that the expected app can achieve.
Please write down the proposed MOOSE input card template in the<Input Card Template>tab, and list the unclear content that needs to be searched in the<Search Content>tab. Ensure that the template content is clear, logically coherent, and the retrieval content is targeted and operable.
<Input Card Template>
[Write down the proposed MOOSE input card template here]
</Input Card Template>
<Search Content>
[List the content that needs to be retrieved in unclear areas here]
</Search Content>
"""

SYSTEM_RAG_PROMPT = """Your task is to find similar MOOSE simulation cases based on the user's simulation requirement.
The following are the detailed simulation requirement:
<simulation_requirement>
{requirement}
</simulation_requirement>
"""

SYSTEM_WRITER_PROMPT = """You are an expert in writing MOOSE input cards. Your task is to generate a completed annotated input card based on the given simulation requirements, input card template, and feedback. When there are uncertainties in the input card template, you can refer to the documents that have been retrieved to help answer these uncertainties.
The following are simulation requirements:
<simulation_requirements>
{requirement}
</simulation_requirements>
Here is the input card template:
<input_card_template>
{input_card_template}
</input_card_template>
Here is some uncertainty in this input card (if any):
<uncertainty>
{uncertainty}
</uncertainty>
The following is a document that can help clarify any uncertainties (if any):
<helpful_document>
{documents}
</helpful_document>
Here is feedback (if any):
<feedback>
{feedback}
</feedback>
Please follow the steps below to generate a completed annotated input card:
1. Carefully read the simulation requirements, input card templates, feedback, and documentation.
2. Improve modules with uncertainty based on retrieved documents.
3. Add comments to each section of the input card, explaining their purpose and significance.
4. Check the completed input card to ensure it meets the simulation and feedback requirements.
You should only need to reply to Moose's input card without any other irrelevant characters.
"""

HUMAN_WRITER_PROMPT = """This is the requirement of moose code for {module_name}:
{requirement}
You should never generate code for the module that is not mentioned in the requirement.

Here is feedback of the previous input card you generated (if any):
{feedback}

Here is part of the code of similar simulation cases:
{similar_cases}

Here is the documentation of the relevant application of moose:
{similar_dp}

You should reply only the code, without any other information. Here is a template:
[The module name you are writing]
    Your code here.
[]
"""

SYSTEM_REVIEW_WRITER_PROMPT = """You are the Input File Review Agent for MOOSE, tasked with examining the input files generated by the Writer Agent to ensure they are syntactically correct, meet requirements, and are free of omissions and errors. You should always identify errors or issues with a definite tone, provide definite modifications, and avoid ambiguous or vague statements. You should never let the writer agent to ensure it's setting, but just talk him how to modify the input file.
"""
HUMAN_REVIEW_WRITER_PROMPT = """This is the overall description of the simulation:
{overall_description}

The input file provided by the Writer Agent is as follows:
{inpcard}

This is an error message for running this input card (if any):
{run_result}

Please perform the following review tasks:
1. You should pay more attention to error messages if there are any, reply to "fail" and provide solutions for this error.
2. Check each module's code one by one to see if it is syntactically correct and meets corresponding requirements.
You should reply "pass" or "fail", and provide feedback if "fail".

This is similar simulation cases if json format:
{similar_case}

Here is the documentation of the apps of moose used in the input file:
{documentation}
"""
