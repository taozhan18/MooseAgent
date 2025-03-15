# ActionComponents system

`ActionComponents` are derived from [Actions](actions/Action.md). They are meant to facilitate the setup of
complex simulations by splitting the definition of each part of the spatial systems involved.

`ActionComponents` are not compatible with [Components](Components/index.md optional=True). `ActionComponents` are intended
to be a rework on `Components` that does not hard-code the equations to be defined on the components and
can co-exist with the `[Mesh]` block.





# Adaptivity System

MOOSE employs $h$-adaptivity and $p$-adaptivity to automatically refine or coarsen the mesh in regions of high or low
estimated solution error, respectively. The idea is to concentrate degrees of freedom (DOFs) where
the error is highest, while reducing DOFs where the solution is already well-captured. This is
achieved through splitting and joining elements from the original mesh based on an error
[`Indicator`](/Adaptivity/Indicators/index.md). Once an error has been computed, a
[`Marker`](/Adaptivity/Markers/index.md) is used to decide which elements to refine or coarsen. Mesh
adaptivity can be employed with both `Steady` and `Transient` Executioners.

## Refinement Patterns

MOOSE employs "self-similar", isotropic refinement patterns, as shown in the figure. When an element
is marked for refinement, it is split into elements of the same type. For example, when using Quad4
elements, four "child" elements are created when the element is refined. Coarsening happens in
reverse, children are deleted and the "parent" element is reactivated. The original mesh starts at
refinement level 0. Each time an element is split, the children are assigned a refinement level one
higher than their parents.

       caption=Self-similar refinement pattern utilized by MOOSE for adaptivity for 1D linear,
               2D quadrilateral, and 3D hexahedron elements.

## P-Refinement

P-refinement level mismatches are not supported for continuous, non-hierarchic
finite element families. Additionally, p-refinement of `NEDELEC_ONE` and `RAVIART_THOMAS`
elements is not supported. Consequently, by default we disable p-refinement of the
following bases: `LAGRANGE`, `NEDELEC_ONE`, `RAVIART_THOMAS`, `LAGRANGE_VEC`, `CLOUGH`,
`BERNSTEIN`, and `RATIONAL_BERNSTEIN`. Users can control what families are disabled for
p-refinement by setting the `disable_p_refinement_for_families` parameter.

## Cycles and Intervals

MOOSE normally performs one adaptivity step per solve. However, developers have the ability to
increase or decrease the amount of adaptivity performed through the "cycles" and "interval" parameters.

The "cycles" parameter can be set to perform multiple adaptivity cycles for a single solve. This is
useful for cases where one would like to resolve a sharp feature in a single step, such as in the case
of an introduced nucleus.


The "interval" parameter can be set to decrease the amount of adaptivity is performed so that
it is performed on every _nth_ step. This can sometimes help to speed up your simulation as adaptivity
can be somewhat expensive to perform.




# Application System

## Description

The `Application` block within an input file is utilized to explicitly specify the application type used for the input file. The application type should be provided using the [!param](/Application/type) parameter in the `Application` block. This block is parsed before the MOOSE application is actually built. If any mismatch between the registered application type and the user-selected type is detected, the system will immediately throw an error and stop the setup of the simulation.

## Example

The following input file snippet demonstrates the use of the `Application` block.






# AuxKernels System

The AuxKernel system mimics the [syntax/Kernels/index.md] but compute values that can be defined
explicitly with a known function. There are two main use cases for the AuxKernel system: computing
a quantity that varies with space and time for postprocessing purposes or for decoupling systems
of equations. Examples for both of these use cases shall be discussed further in the following
sections.

Creating a custom AuxKernel object is done by creating a new C++ object that inherits from
`AuxKernel`, `VectorAuxKernel` or `ArrayAuxKernel` and overriding the `computeValue` method,
which returns a scalar (`Real`), vector (`RealVectorValue`) or a Eigen vector (`RealEigenVector`)
for the three types respectively. A forth type (`AuxScalarKernel`) also exists, but the syntax for
these objects is different and detailed in the [syntax/AuxScalarKernels/index.md].

AuxKernel objects, like Kernel objects, must operate on a variable. Thus, there is a required
parameter ("variable") that indicates the variable that the AuxKernel object is computing. These
variables are defined in the [AuxVariables](syntax/AuxVariables/index.md) block of the input file.
AuxKernel objects derived from `AuxKernel`, `VectorAuxKernel` or `ArrayAuxKernel` operate on
standard scalar, vector or array field variables respectively. For example the following input
file snippet creates an auxiliary variable suitable for use with an `VectorAuxKernel`.


## Nodal vs Elemental AuxKernel Objects

There are two flavors of AuxKernel objects: nodal and elemental. The distinction is based on the
type of variable that is being operated on by the object. If the variable family is `LAGRANGE` or
`LAGRANGE_VEC` then the AuxKernel will behave as nodal. If the variable family is `MONOMIAL` then
the AuxKernel will behave as elemental.

The difference is based on how the `computeValue` method of the object is called when the kernel
is executed. In the nodal case the `computeValue` method will be executed on each +node+ within the
finite element mesh and the value returned from the method will directly assign the value
of the shape function at that node.

In the elemental case the `computeValue` method will be executed on each quadrature point of an
+element+ of the finite element mesh. The values computed at the quadrature points are used to
perform the correct finite element projection automatically and set the values for the degrees
of freedom. This is achieved by assembling and solving a *local* finite element projection
problem for each and every element in the domain (or blocks) of interest.
Typically, in the elemental case the order of the monomial finite element is set to
constant so there is a single DOF per element, but higher monomials are also supported.

As is evident by the functionality detailed, the distinction between the two arises from the nature
of the finite element shape functions. For Lagrange shape functions the DOF values correspond with
the nodes, while for elemental shape functions the DOF values are not associated with nodes.

The same AuxKernel object can be designed work both as elemental or nodal, for example the
`computeValue` method for the [FunctionAux.md] object properly handles using the correct spatial
location based on if the object is nodal or elemental with the `isNodal` method.

## Block vs Boundary Restricted AuxKernel Objects

While auxiliary variables are always defined on mesh subdomains, MOOSE allows auxiliary kernels to be either block (mesh subdomain) or boundary restricted.
When an auxiliary kernel is boundary restricted, it evaluates an auxiliary variable only on the designated boundaries.
Because of this, the auxiliary variable will only have meaningful values on the boundaries even though it is defined on mesh subdomains.
When an auxiliary kernel is block restricted, the variable that it evaluates must be defined on a subdomain covering the blocks where the auxiliary kernel is defined.
When an auxiliary kernel is boundary restricted, the variable must be defined on a subdomain that all the sides on the boundaries are connected with.
An elemental auxiliary variable defined on an element that has multiple boundary sides cannot be properly evaluated within a boundary restricted auxiliary kernel because elemental auxiliary variables can only store one value per element.
Users can split the boundaries and define multiple elemental auxiliary variables for each split to avoid the situation of element connecting with multiple boundary sides.


Nodal AuxKernel objects abuse the notion of quadrature points, the `_qp` member variable is set
to zero, but still must be used to access coupled variable values and material properties. This
is done to allow the syntax to be consistent regardless of the AuxKernel flavor: nodal or elemental.

## Mortar Nodal Auxiliary Kernel Objects

In order to compute properties in the mortar sense, it is necessary to loop over the mortar segment
mesh to spatially integrate variables. `MortarNodalAuxKernel`s offer this functionality where these "weighted" variables,
which intervene in the computation of contact constraints and their residuals, can be coupled to generate the desired output value.
Therefore, if postprocessing of mortar quantities is required, nodal mortar auxiliary kernels can be employed.
Objects inheriting from `MortarNodalAuxKernel` allow for said operations on the mortar lower-dimensional domains featuring similar
functionality to other nodal auxiliary kernels, including the possibility of computing quantities in an
`incremental` manner.

## Execute Flags

AuxKernel objects inherit from the [SetupInterface.md] so they include the "execute_on" variable.
By default this parameter is set to `EXEC_LINEAR` and `EXEC_TIMESTEP_END`. The `EXEC_LINEAR` flag
is set because it is possible to couple values compute by an AuxKernel object to other objects
such as Kernel or Material objects that are used in the residual calculation. In order to ensure
that the values from the auxiliary variable are correct during the iterative solve they are computed
for each iteration.

However, if the auxiliary variable be computed is not being coupled to objects computing the
residual evaluating the AuxKernel on each linear iteration is not necessary and can slow down the
execution of a simulation. In this case, the `EXEC_LINEAR` flag should be removed. Likely the
`EXEC_INITIAL` flag should be added to perform the auxiliary variable calculation during the initial
setup phase as well.

## Populating lower-dimensional auxiliary variables

Lower-dimensional auxiliary variables may be populated using boundary restricted
auxiliary kernels. The boundary restriction of the aux kernel should be
coincident with (a subset of) the lower-dimensional blocks that the
lower-dimensional variable lives on. Using a boundary restricted auxiliary
kernel as opposed to a lower-d block-restricted auxiliary kernel allows pulling
in coincident face evaluations of higher-dimensional variables and material
properties as well as evaluations of coupled lower-dimensional variables.

## Example A: Post processing with AuxKernel

The following example is extracted from step 4 of the
[Darcy Flow and Thermomechanics Tutorial](darcy_thermo_mech/index.md optional=True). Consider Darcy's
Law for flow in porous media neglecting changes in time and gravity:

\begin{equation}
\label{darcy}
-\nabla\cdot\frac{\mathbf{K}}{\mu}\nabla p = 0,
\end{equation}
where $\mathbf{K}$ is the permeability tensor, $\mu$ is the fluid viscosity, and $p$ is the
pressure and the velocity ($\vec{u}$) may be computed as:

\begin{equation}
\label{darcy_vel}
\vec{u} = \frac{\mathbf{K}}{\mu}\nabla p.
\end{equation}

The left-hand side of [darcy] would be solved with a nonlinear variable and an appropriate
[Kernel object](syntax/Kernels/index.md). The AuxKernel system can be used computing the velocity
following [darcy_vel]. In the tutorial the exact calculation is performed using the DarcyVelocity
object, the header and source files for this object are listed below.




## Example B: Decoupling Equations

Auxiliary variables may be used interchangeably with nonlinear variables with respect to coupling
allowing complicated systems of equations to be decoupled for solving individually. This is very
useful for testing and validation.

Consider the heat equation with an advective term that is coupled to the pressure computed
in [darcy] as in step 6 of the
[Darcy Flow and Thermomechanics Tutorial](darcy_thermo_mech/index.md optional=True):

\begin{equation}
\label{heat}
C\left( \frac{\partial T}{\partial t} + \epsilon \vec{u}\cdot\nabla T \right) - \nabla \cdot k \nabla T = 0,
\end{equation}
where $T$ is temperature, $C$ is the heat capacity, $k$ is the thermal conductivity, and
$\epsilon$ is the porosity. The advective term ($\epsilon\vec{u}\cdot\nabla T$) is computed in a
kernel object ([step06_coupled_darcy_heat_conduction/src/kernels/DarcyAdvection.C]) and requires
the pressure variable be provided as a variable:


For testing purposes is it not desirable to include the solve for the pressure variable when
examining the correctness of the heat equation solve, so an auxiliary variable that is assigned an
arbitrary function of space and time is used instead. The following input file snippet demonstrates
the decoupling of the pressure variable by computing it using an AuxVariable the FunctionAux object.






# AuxScalarKernels System

An `AuxiliaryScalarVariable` is to a [ScalarVariable.md] what an [AuxVariable.md] is to a [MooseVariable.md].
It is not the solution of a differential equation and instead can be computed directly by algebraic operations
using an auxiliary scalar kernel.

Creating a custom `AuxScalarKernel` object is done by creating a new C++ object that inherits from
`AuxScalarKernel` and overriding the `computeValue` method.

`AuxScalarKernel` objects, like all `Kernel` objects, must operate on a variable. Thus, there is a required
parameter ("variable") that indicates the variable that the `AuxScalarKernel` object is computing. These
variables are defined in the [AuxVariables](syntax/AuxVariables/index.md) block of the input file, and must be of
family `SCALAR`.

For higher order scalar variables, `computeValue` is called multiple times with each order index `_i` for the value of each order.
The definition of `computeValue` may depend on `_i`, as appropriate.

## Execution schedule

Please see the [documentation for field auxiliary kernels (AuxKernels)](syntax/AuxKernels/index.md#execute_on)
which applies identically to `AuxScalarKernels`.

## Examples

`AuxScalarKernels` are essentially used for postprocessing or for decoupling solves.
The examples in the [documentation for field auxiliary kernels (AuxKernels)](syntax/AuxKernels/index.md#example_a)
can conceptually be adapted to `AuxScalarKernels`.




# AuxVariables System

The AuxVariables block within the input file may be used to create "auxiliary" variables that
act, with respect to the interaction with other objects, like "nonlinear" variables (see
[syntax/Variables/index.md]). Please refer to the [AuxKernels/index.md] for complete details
regarding the use of auxiliary variables.




# BCs System

The `BCs` system is used to impose boundary conditions in a finite element problem. Each `BC` object
sets the boundary condition for a single variable/equation, though multiple boundaries may be specified at once.

See [FVBCs](syntax/FVBCs/index.md) for boundary conditions of finite volume problems.

Some of the main types of boundary conditions are:
- [Dirichlet Boundary conditions](DirichletBC.md) to set the value of a variable on a boundary
- [Neumann Boundary conditions](NeumannBC.md) to set a flux for the equation corresponding to the variable. Depending on the
  equation being solved, this can be equivalent to setting the value of the derivative of the variable on the boundary
- Robin boundary conditions to solve an equation tying both the variable value and its derivatives on the boundary

In MOOSE, boundary conditions are split in two categories: `NodalBC`s and `IntegratedBC`s. Similar to kernels,
`computeQpResidual/Jacobian` are the main routine to implement for most boundary conditions. [Automatic differentiation](automatic_differentiation/index.md)
is implemented for boundary conditions. `AD` BCs do not require implementing `computeQpJacobian`.

## Nodal boundary conditions

Nodal boundary conditions are applied on nodes in the mesh. Nodal boundary conditions may only be applied on variables
that have degrees of freedom at nodes, such as Lagrange variables.

We show below code snippets for the `DirichletBCBase`. This boundary condition sets the value of a variable on
a node.

If the value is preset, the `computeQpValue` is called instead of the `computeQpResidual`. This value is then directly placed in the solution vector.


If the value is not preset, the `computeQpResidual` routine is called. The residual of a non-preset `DirichletBC` is simply the difference between the desired value and the current variable value.


`_qp`, the index over quadrature points, is simply 0 on nodes. We use this indexing in order to keep consistent user interfaces.

## Integrated boundary conditions

Integrated boundary conditions are applied on sides in the mesh. A local quadrature-based integration is performed to compute
the residual and Jacobian contribution of the boundary condition.

In the following snippet, we show the definition of the contribution to the residual of a [FunctionNeumannBC.md].
The `computeQpResidual` simply returns the value of the flux.





# Bounds System

The `Bounds` system is designed to bound the value of a nonlinear variable. Whether the bound is an upper or lower
bound depends on the parameters passed to the `Bounds` object. The bound may be spatially and time-dependent,
and even depend on other simulation quantities, as implemented in the particular `Bounds` object used.

The auxiliary variable that serves as the `variable` parameter of a `Bounds` object
is not actually used or even set in the computation. However, its type is used to decide if the `Bounds` loop
will be 'nodal' (loop on all nodes) or 'elemental' (loop on quadrature points in elements). Its block restriction
is used to define where the bounds is applied. It may be re-used for multiple bounds objects.

Only nodal and constant elemental variables are supported at this time.

The `Bounds` system supports both finite element and finite volume variables. Only elemental bounds
should be used for finite volume variables.

Note that in order for `Bounds` to have an effect, the user has to specify the
PETSc options `-snes_type vinewtonssls` or `-snes_type vinewtonrsls`. A warning will be generated if neither option is specified. The PETSc manual pages for the `vinewtonssls` algorithm
can be found
[here](https://www.mcs.anl.gov/petsc/petsc-current/docs/manualpages/SNES/SNESVINEWTONSSLS.html)
while the manual page for `vinewtonrsls` can be found
[here](https://www.mcs.anl.gov/petsc/petsc-current/docs/manualpages/SNES/SNESVINEWTONRSLS.html#SNESVINEWTONRSLS).

## Example syntax

In the following example, a lower and an upper bound are applied to two variables `u` and `v`
using the same auxiliary variable `bounds_dummy` and four `Bounds` objects.





# ChainControls System

The `ChainControls` system is an extension of the [Controls system](syntax/Controls/index.md)
that uses `ChainControl` objects, which instead of working directly with
controllable parameters, work with an additional layer of "control data",
[/ChainControlData.md]. `ChainControl` objects can do the following:

- Declare new control data
- Retrieve control data declared elsewhere
- Change control data values
- Set controllable parameters in MOOSE objects using control data

The main advantage of this additional capability is to chain control operations together,
which is useful for composing complex control systems.

`ChainControlData` is managed by the [/ChainControlDataSystem.md].

## Objects and Associated Actions





# Constraints System

The `Constraints` system provides functionality for describing interaction and coupling
between various nodes, elements or surfaces in a model for which the topology may evolve
during the course of the solution. Generically, within an interaction pair, the two sides
are referred to as +Element+ and +Neighbor+ or +Secondary+ and +Primary+. A few examples
of constraints include contact, mesh tying, and periodic boundary conditions.

Since the topology of the interacting nodes and elements may evolve, the direct contributions
to the residual and the Jacobian need to be provided by the developer by overriding the
`computeResidual()` and `computeJacobian()` functions directly. Certain examples for node
and element constraints are listed in the syntax list at the bottom of the page. The remainder
of the description is focused on the application of mortar constraints for surface interaction.

## MortarConstraints

The mortar system in MOOSE uses a segment-based approach for evaluation of mortar integrals; for information on the automatic generation of mortar segment meshes see [AutomaticMortarGeneration.md].

One has the option to use Petrov-Galerkin interpolation for the Lagrange multiplier variable. This is typically useful for mechanical contact problems (see [Petrov-Galerkin_approach_for_Lagrange_multipliers.md]).

### Overview

An excellent overview of the conservative mortar constraint implementation in MOOSE for 2D problems is given in
[!cite](osti_1468630). We have verified that the MOOSE mortar implementation satisfies the following *a priori*
error estimates for 2D problems and (see discussion and plots on
[this github issue](https://github.com/idaholab/moose/issues/13080)) and for 3D problems on *hexahedral* meshes:

| Primal FE Type | Lagrange Multiplier (LM) FE Type | Primal L2 Convergence Rate | LM L2 Convergence Rate |
| --- | --- | --- | --- |
| Second order Lagrange | First order Lagrange | 3 | 2.5 |
| Second order Lagrange | Constant monomial | 3 | 1 |
| First order Lagrange | First order Lagrange | 2 | 1.5 |
| First order Lagrange | Constant monomial | 2 | 1.5 |

General meshes in 3D—especially meshes with triangular face elements on the mortar interface—require additional care to ensure convergence.
Triangular elements on the mortar interface typically exhibit the infamous (and well documented) 'locking' phenomenon; resulting in singular systems that require stabilization or other special treatment.

The above *primal* convergence rates were realized on tetrahedral and mixed meshes using a stabilization with `delta = 0.1` for the `EqualValueConstraint`, with the additional caveat that meshes (both generated and unstructured) are re-generated for each experiment.
Uniform refinement of tetrahedral meshes were typically observed to result in *divergence* of the Lagrange multiplier and degradation of primal convergence rates.
Adaptive refinement of meshes with triangular faces on the mortar interface has not been thoroughly studied in MOOSE and should be approached with caution.

Based on these observations the following recommendations are provided for using *3D* mortar in MOOSE:

1. When possible, discretize the secondary side of the mortar interface with QUAD elements (i.e. use HEX elements or carefully oriented PRISM and PYRAMID elements for volume discretization).
2. When TRI elements are present on the mortar interface, verify that the problem is well conditioned of the problem and use stabilization if necessary.
3. Avoid uniformly refining meshes, instead regenerate meshes when a refined mesh is needed.

3D mortar often requires larger AD array sizes than specified by the default MOOSE configuration. To configure MOOSE with a larger array use configuration option `--with-derivative-size=<n>`. The AD size required for a problem depends on 1) problem physics, 2) the order of primal and Lagrange multiplier variables, and 3) the relative sizing of the secondary and primary meshes.

### Parameters id=MC-parameters

There are four
required parameters the user will always have to supply for a constraint derived
from `MortarConstraint`:

- `primary_boundary`: the boundary name or ID assigned to the primary side of the
  mortar interface
- `secondary_boundary`: the boundary name or ID assigned to the secondary side of
  the mortar interface
- `primary_subdomain`: the subdomain name or ID assigned to the lower-dimensional
  block on the primary side of the mortar interface
- `secondary_boundary`: the subdomain name or ID assigned to the lower-dimensional
  block on the secondary side of the mortar interface

As suggested by the above required parameters, the user must do some mesh work
before they can use a `MortarConstraint` object. The easiest way to prepare
the mesh is to assign boundary IDs to the secondary and primary sides of the
interface when creating the mesh in their 3rd-party meshing software (e.g. Cubit
or Gmsh). If these boundary IDs exist, then the lower dimensional blocks can be
generated automatically using the `LowerDBlockFromSidesetGenerator` mesh generator as
shown in the below input file snippet:

```
[Mesh]
  [./primary]
    type = LowerDBlockFromSidesetGenerator
    sidesets = '2'
    new_block_id = '20'
  [../]
  [./secondary]
    type = LowerDBlockFromSidesetGenerator
    sidesets = '1'
    new_block_id = '10'
  [../]
[]
```

There are also some optional parameters that can be supplied to
`MortarConstraints`. They are:

- `variable`: Corresponds to a Lagrange Multiplier variable that lives on the
  lower dimensional block on the secondary face
- `secondary_variable`: Primal variable on the secondary side of the mortar interface
  (lives on the interior elements)
- `primary_variable`: Primal variable on the primary side of the mortar interface
  (lives on the interior elements). Most often `secondary_variable` and
  `primary_variable` will correspond to the same variable
- `compute_lm_residuals`: Whether to compute Lagrange Multiplier residuals. This
  will automatically be set to false if a `variable` parameter is not
  supplied. Other cases where the user may want to set this to false is when a
  different geometric algorithm is used for computing residuals for the LM and
  primal variables. For example, in mechanical contact the Karush-Kuhn-Tucker
  conditions may be enforced at nodes (through perhaps a `NodeFaceConstraint`)
  whereas the contact forces may be applied to the displacement residuals
  through `MortarConstraint`
- `compute_primal_residuals`: Whether to compute residuals for the primal
  variables. Again this may be a useful parameter to use when applying different
  geometric algorithms for computing residuals for LM variables and primal
  variables.
- `periodic`: Whether this constraint is going to be used to enforce a periodic
  condition. This has the effect of changing the normals vector, for mortar
  projection, from outward to inward facing.
- `quadrature`: Specifies the quadrature order for mortar segment elements.
  This is only useful for 3D mortar on QUAD face elements since integration of
  QUAD face elements with TRI mortar segments on the mortar interface is
  inexact. Default quadratures are typically sufficient, but *exact* integration
  of FIRST order QUAD face elements (e.g. HEX8 meshes) requires SECOND order
  integration. *Exact* integration of SECOND order QUAD face elements (e.g.
  HEX27 meshes) requires FOURTH order integration.

At present, either the `secondary_variable` or `primary_variable` parameter must be supplied.

## Coupling with Scalar Variables

If the weak form has contributions from scalar variables, then this contribution can be
treated similarly as coupling from other spatial variables. See the
[`Coupleable`](source/interfaces/Coupleable.md) interface for how to obtain the variable
values. Residual contributions are simply added to the `computeQpResidual()` function.

Because mortar-versions of `UserObjects` are not yet implemented, the only way to add
contributions to the Jacobian, as well as the contribution of the mortar spatial variables
to the scalar variable, is through deriving from the scalar augmentation class
[`MortarScalarBase`](source/constraints/MortarScalarBase.md). This class provides
standard interfaces for quadrature point contributions to primary, secondary, lower, and
scalar variables in the residual and Jacobian. Additional discussion can be found at
[`ScalarKernels`](syntax/ScalarKernels/index.md).




# Controls System

The Controls system in MOOSE has one primary purpose: +to modify input parameters during runtime
of a MOOSE-based simulation+.

If a developer has marked a MOOSE object input parameter as *controllable*, that
parameter may be controlled during a simulation using `Control` objects.
`Control` objects are defined in the input file in the `Controls` block, similar to other systems
in MOOSE. For example, the following input file snippet shows the use of the
[RealFunctionControl](/RealFunctionControl.md) object.

         block=Kernels Controls
         id=controls_example
         caption=Example of a Control object used in a MOOSE input file.

Here, `func_control` controls the `coef` parameter of the `diff` object. See
[#object-and-parameter-names] for the allowable syntax to specify controlled
parameters.

## Making a Parameter Controllable id=sec:control-param

The input parameters of objects you wish to be controlled must:

- Be marked as "controllable". In the `validParams()` method for the class,
  the `InputParameters::declareControllable(param_names)` method is used as
  shown in [declare_controllable_listing]. Note that `param_names` may be a
  list of parameter names separated by spaces, e.g., `"param1 param2 param3"`.

          start=InputParameters
          end=DirichletBC::DirichletBC
          id=declare_controllable_listing
          caption=Example `validParams` method that declares a parameter as controllable.
- Be stored as `const` references; for example, in the `.h` file,


  which is initialized in the `.C` file using `getParam<T>(param)`, as usual:


Each class documentation page lists whether each of its input parameters are controllable.
For example, see the [DirichletBC](source/bcs/DirichletBC.md#input-parameters) page.

## Developing a New Control

`Control` objects are similar to other systems in MOOSE. You create a control in your application
by inheriting from the `Control` C++ class in MOOSE. It is required to override the `execute`
method in your custom object. Within this method the following methods are generally used to get
or set controllable parameters:

- `getControllableValue` <br>
  This method returns the current controllable parameter, in the case that multiple parameters are
  being controlled, only the first value will be returned and a warning will be produced if the
  values are differ (this warning may be disabled).

- `setControllableValue` <br>
  This method allows for a controllable parameter to be changed, in the case that multiple
  parameters are being controlled, all of the values will be set.

These methods operator in a similar fashion as
other systems in MOOSE (e.g., `getPostprocessorValue` in the [Postprocessors] system), each
expects an input parameter name (`std::string`) that is prescribed in the `validParams` method.

There are additional overloaded methods that allow for the setting and getting of controllable values
with various inputs for prescribing the parameter name, but the two listed above are generally
what is needed.  Please refer to the source code for a complete list.

## Object and Parameter Names id=object-and-parameter-names

The objective of a `Control` object is to control parameters of one or more other
objects; these parameters to control are specified by input parameters of the `Control`.
[controls_example] shows an example syntax for specifying input parameters in the
`parameter` parameter. In this example, `*/*/coef` is specified, which would
match any controllable parameter named `coef` at that nesting level. In the example, there
is only one parameter that the pattern matches, so `Kernels/diff/coef` would
be equivalent. The "/"-separated path preceding the parameter name corresponds
to the syntax blocks under which the parameter is located, such as for the system name and object name.

In similar fashion, object names can be requested by controls (e.g., as in the
[`TimePeriod`](/TimePeriod.md)). In this case, the general naming scheme is the same
as above but the parameter name is not included, e.g., `Kernels/diff`.

In both cases there is an alternative form for defining an object and parameter names:
`base::object/name`. In this case "base" is the MOOSE base system that the object is derived from.
For example, `Kernel::diff/coef`. All MOOSE "bases" are listed bellow:

- ArrayAuxKernel,
- ArrayKernel,
- AuxKernel,
- AuxScalarKernel,
- BoundaryCondition,
- Constraint,
- Damper,
- DGKernel,
- DiracKernel,
- Distribution,
- EigenKernel,
- Executioner,
- Executor,
- Function,
- FVBoundaryCondition,
- FVInterfaceKernel,
- FVKernel,
- Indicator,
- InitialCondition,
- InterfaceKernel,
- Kernel,
- LineSearch,
- Marker,
- MaterialBase,
- MeshGenerator,
- MooseMesh,
- MoosePartitioner,
- MoosePreconditioner,
- MooseVariableBase,
- MultiApp,
- NodalKernel,
- Output,
- Postprocessor,
- Predictor,
- Problem,
- RelationshipManager.,
- Reporter,
- Sampler,
- ScalarInitialCondition,
- ScalarKernel,
- Split,
- TimeIntegrator,
- TimeStepper,
- Transfer,
- UserObject,
- VectorAuxKernel,
- VectorInterfaceKernel,
- VectorKernel,
- VectorPostprocessor,

MOOSE allows objects to define a `tag` name to access its controllable parameters with their `control_tags` parameter.

         block=Postprocessors
         id=controls_tags
         caption=Example of the parameter control_tags.

The two postprocessors in [controls_tags] declare the same control tag `tag`.
Thus their controllable parameter `point` can be set by controls simultaneously with `tag/*/point` as in [controls_tags_use].

         block=Controls
         id=controls_tags_use
         caption=Example of using the tagged controllable parameters.

The tag name does not include the object name although the tag name is added by an object.
To access a controllable parameter, the syntax is `tag/object/name`.
Internally, MOOSE adds the input block name as a special tag name.

## Controllable Parameters Added by Actions id=controllable_params_added_by_actions

MOOSE also allows parameters in [Actions](Action.md) to be controllable.
The procedure for making a parameter in an [Action](Action.md) controllable is the same as documented in [syntax/Controls/index.md#sec:control-param].
It is important that this controllable parameter must be directly connected with the parameters of MOOSE objects, such as kernels, materials, etc., using this parameter.

         start=GenericConstantArray
         end=connectControllableParams
         id=connect_controllable
         caption=Example of connecting controllable parameters in an action and the objects added by the action.

The action controllable parameter can be referred as usual in an input file. For example,

         block=Controls
         id=controls_example3
         caption=Example of a "Action" block that contains a parameter that is controlled via a
                 MOOSE Control object.

## Child Objects


## Associated Actions


# Convergence System

The Convergence system allows users to customize the stopping criteria for the
iteration in various solves:

- Nonlinear system solves
- Linear system solves (not yet implemented)
- Steady-state detection in [Transient.md] (not yet implemented)
- Fixed point solves with [MultiApps](syntax/MultiApps/index.md) (not yet implemented)
- Fixed point solves with multiple systems (not yet implemented)

Instead of supplying convergence-related parameters directly to the executioner,
the user creates `Convergence` objects whose names are then supplied to the
executioner, e.g.,

```
[Convergence]
  [my_convergence1]
    type = MyCustomConvergenceClass
    # some convergence parameters, like tolerances
  []
[]

[Executioner]
  type = Steady
  nonlinear_convergence = my_convergence1
[]
```

Currently only the nonlinear solve convergence is supported, but others are planned
for the near future. If the `nonlinear_convergence` parameter is not specified,
then the default `Convergence` associated with the problem is created internally.




## Convergence Criteria Design Considerations

Here we provide some considerations to make in designing convergence criteria
and choosing appropriate parameter values.
Consider a system of algebraic system of equations

\mathbf{r}(\mathbf{u}) = \mathbf{0} \,,

where $\mathbf{u}$ is the unknown solution vector, and $\mathbf{r}$ is the residual
function. To solve this system using an iterative method, we must decide on
criteria to stop the iteration.
In general, iteration for a solve should halt when the approximate solution $\tilde{\mathbf{u}}$
has reached a satisfactory level of error $\mathbf{e} \equiv \tilde{\mathbf{u}} - \mathbf{u}$,
using a condition such as

\|\mathbf{e}\| \leq \tau_u \,,

where $\|\cdot\|$ denotes some norm, and $\tau_u$ denotes some tolerance.
Unfortunately, since we do not know $\mathbf{u}$, the error $\mathbf{e}$ is
also unknown and thus may not be computed directly. Thus some approximation of
the condition [!eqref](error_criteria) must be made. This may entail some
approximation of the error $\mathbf{e}$ or some criteria which implies the
desired criteria. For example, a very common approach is to use a residual
criteria such as

\|\mathbf{r}\| \leq \tau_{r,\text{abs}} \,.

While it is true that $\|\mathbf{r}\| = 0$ implies $\|\mathbf{e}\| = 0$, a
zero-tolerance is impractical, and the translation between the tolerance
$\tau_u$ to the tolerance is $\tau_r$ is difficult. The "acceptable" absolute
residual tolerance is tricky to determine and is highly dependent on the
equations being solved. To attempt to circumvent this issue, relative residual
criteria have been used, dividing the residual norm by another value in an
attempt to normalize it. A common approach that has been used is to use the
initial residual vector $\mathbf{r}_0$ to normalize:

\frac{\|\mathbf{r}\|}{\|\mathbf{r}_0\|} \leq \tau_{r,\text{rel}} \,,

where $\tau_{r,\text{rel}}$ is the relative residual tolerance. The disadvantage
with this particular choice is that this is highly dependent on how good the
initial guess is: if the initial guess is very good, it will be nearly impossible
to converge to the tolerance, and if the initial guess is very bad, it will be
too easy to converge to the tolerance, resulting in an erroneous solution.

Some other considerations are the following:

- Consider round-off error: if error ever reaches values around round-off error,
  the solve should definitely be considered converged, as iterating further
  provides no benefit.
- Consider the other sources of error in the model that produced the system of
  algebraic equations that you're solving. For example, if solving a system of
  partial differential equations, consider the model error and the discretization
  error; it is not beneficial to require algebraic error less than the other
  sources of error.
- Since each convergence criteria typically has some weak point where they break
  down, it is usually advisable to use a combination of criteria.

For more information on convergence criteria, see [!cite](rao2018stopping) for
example.

The `Convergence` system provides a lot of flexibility by providing several
pieces that can be combined together to create a desired set of convergence
criteria. Since this may involve a large number of objects (including objects
from other systems), it may be beneficial to create an [Action](/Action.md)
to create more compact and convenient syntax for your application.

## Implementing a New Convergence Class

`Convergence` objects are responsible for overriding the virtual method

```
MooseConvergenceStatus checkConvergence(unsigned int iter)
```

The returned type `MooseConvergenceStatus` is one of the following values:

- `CONVERGED`: The system has converged.
- `DIVERGED`: The system has diverged.
- `ITERATING`: The system has neither converged nor diverged and thus will
  continue to iterate.


# Correctors

The `Correctors` system is designed to modify the values of nonlinear variable solutions.
This can be as part of a predictor-corrector time integration scheme for example.

Correctors are [UserObjects](UserObjects/index.md) behind the scene. They simply have a dedicated role and syntax.

Please let us know on [GitHub Discussions](https://github.com/idaholab/moose/discussions)
how you are using the `Correctors` system so we can include your techniques on this page!




# Dampers System

Dampers are used to decrease the attempted change to the solution with each nonlinear step.
This can be useful in preventing the solver from changing the solution dramatically from one
step to the next. This may prevent, for example, the solver from attempting to evaluate negative
temperatures.




# Debug System

## Overview

The `[Debug]` input file block is designed to contain options to enable debugging tools for a
simulation. For example, the input file snippet below demonstrates how to enable the material
property debugging tool. This tool automatically outputs material properties as fields in the
[outputs/Exodus.md] file.
A complete list of the available options is provided in the parameter list at the bottom of this page.


## Residual outputs for debugging nonlinear convergence issues

When solving multi-variable or multi-physics problems, it is often the case that the residual for a
subset of variables is more problematic to converge than for the others. This may be because the underlying
physics are tougher to solve, or because there are issues with the kernels for those variables!

MOOSE provides two convenient debug boolean options to examine the convergence of nonlinear residuals:

- [!param](/Debug/show_var_residual_norms) shows the residual norms for each nonlinear variable
  equation. The equation with the highest residual is the least converged.
  This is the norm after scaling if equation scaling, automatic or manual, is used.

- [!param](/Debug/show_top_residuals) shows the residual norms only for the least converged variable equation.


Helpful information on debugging numerical convergence issues is provided in the [numerical troubleshooting page](application_usage/failed_solves.md optional=True).

## Execution ordering output

### Ordering of the problem set-up id=debug-setup

MOOSE parses the input file and executes numerous [Actions](actions/Action.md) which progressively
load/build the mesh, create the variables, kernels, boundary conditions, output objects etc.
The ordering of this process may be shown using the [!param](/Debug/show_actions) parameter.

The dependencies of each `Action` should be declared in the source code of each `Action`. This enables MOOSE
to perform automatic dependency resolution to correctly order them. To view declared action dependencies, please
use the [!param](/Debug/show_action_dependencies) parameter.

For the automatic ordering of the mesh generators, please refer to the
[mesh documentation page](syntax/Mesh/index.md).

### Solve and execution ordering id=debug-order

Nearly every solve in MOOSE consists of a succession of operations on nodes, quadrature points,
elements and elements' faces. These operations may be for example to compute the contribution of a
kernel/boundary condition/etc. to the residual, Jacobian, etc.

The MOOSE `Debug` system offers the [!param](/Debug/show_execution_order) parameter to output the
order of execution of each of these objects in those loops. This order may depend on local block/boundary
restrictions, and local or global dependency resolutions.

This parameter is most helpful to understand if `AuxKernels`, `UserObjects` and other systems which can
interact in arbitrarily complex ways on a group of variables are indeed executed in the order desired
by the modeler. If problematic, object execution may be reordered using various boolean parameters, `execute_on` flags, and other manual dependency declarations.
For example for UserObjects, the `execution_order_group` parameter lets the modeler select the ordering of executions of user objects.

## Viewing objects created by an applications

Numerous applications will use [Actions](actions/Action.md) to simplify the user input. This reduces opportunities for
mistakes in an input, but has the inconvenience of hiding part of the simulation setup. The [!param](/Debug/show_actions) will,
for most objects, list the objects created by an action. The `Debug` system also offers several summaries of objects:

- [!param](/Debug/show_material_props) for material properties, created on elements, neighbors and sides
- [!param](/Debug/show_reporters) for reporters, created directly or from systems that derive from Reporters, such as [VectorPostprocessors](syntax/Postprocessors/index.md) and [Positions](syntax/Positions/index.md)
- [!param](/Debug/show_functors) for [Functors](syntax/Functors/index.md), an abstraction for objects which includes [Functions](syntax/Functions/index.md) and [Variables](syntax/Variables/index.md)
- [!param](/Debug/show_block_restriction) for information regarding block-restriction of objects


Additionally, [!param](/Debug/show_execution_order) will provide the list of objects executed as they are executed.
This includes, [Kernels](syntax/Kernels/index.md) (and `Interface`, `Nodal`, finite volume, etc kernels), [AuxKernels](syntax/AuxKernels/index.md), [boundary conditions](syntax/BCs/index.md)
(including finite volume), [UserObjects](syntax/UserObjects/index.md), [Postprocessors](syntax/Postprocessors/index.md) and
[VectorPostprocessors](syntax/Postprocessors/index.md).


## Other useful outputs available in other systems

The `[Debug]` system is not the only system that provides useful debugging information. We summarize
these other helpful resources below:

- to debug [MultiApps](syntax/MultiApps/index.md) and [Transfers](syntax/Transfers/index.md)-related
  issues, the `FEProblem` parameter [!param](/Problem/FEProblem/verbose_multiapps) shows a helpful summary of
  transfers executed and important metadata about each `Transfer`.

- to debug linear system convergence issues, numerous parameters may be passed to PETSc to make it more verbose.
  They are summarized on this [page about debugging numerical issues](application_usage/failed_solves.md optional=True) and in
  the [PETSc manual](https://www.mcs.anl.gov/petsc/petsc-current/docs/manualpages/).

- to debug a [Mesh](syntax/Mesh/index.md) related issue, please see [this page](syntax/Mesh/index.md#troubleshooting)
  for built-in MOOSE mesh generation issues and [this page](syntax/Mesh/index.md#issues) for possible issues from an external mesh.

- to debug `Controls`, there is a command line argument, `--show-controls` that can be passed to a MOOSE-application
  executable to show all active `Controls` and all active objects at all time steps in the simulation.

There are currently no convenient debugging options or tools for `MultiApps`-based fixed point iteration problems.
Use the [!param](/Executioner/Transient/fixed_point_min_its), [!param](/Executioner/Transient/fixed_point_max_its) and
[!param](/Executioner/Transient/accept_on_max_fixed_point_iteration) to output at the desired fixed point iteration.


## Parameters list


## Syntax list




# DeprecatedBlock System

The `DeprecatedBlock` system consists of an `Action`, [DeprecatedBlockAction.md], which may be inherited
instead of the regular [Action](source/actions/Action.md), to mark an action syntax as deprecated.

This will add a parameter [!param](/DeprecatedBlock/DeprecatedBlockAction/DEPRECATED) that will be shown in
the syntax's input parameters. It will also print a deprecation message in the console when the deprecated action is used.




# DGKernels System

# DGKernels System

## Overview

DGKernels are the kernels defined on internal sides.
DGKernels are typically for elemental variables, i.e. variables that allow solutions to be discontinuous across element sides.
DGKernels along with normal kernels allow the definition of weak forms arising from discontinuous finite element methods (DFEM).
DGKernels can be block restricted for calculations with DFEM on subdomains.
Internal sides are visited once during residual or Jacobian evaluations by MOOSE.
DGKernels handle two pieces of residual, marked as `Element` and `Neighbor`, on an internal side and corresponding four pieces of Jacobian, marked as `ElementElement`, `ElementNeighbor`, `NeighborElement` and `NeighborNeighbor`.
The normals on internal sides are pointing towards neighboring element from the current element.
Typically DGKernels are irrelevant with the normal direction.
When there are mesh refinement, MOOSE visits all the active internal sides, meaning that if there is a hanging node for an internal side, MOOSE visit the child internal sides.
DGKernels can make use of the material properties defined on both Element and Neighbor sides.
The DGKernel with interior penalty (IP) method for diffusion equations can be found at [DGDiffusion.md].
The DGKernel with upwinding scheme for hyperbolic equations can be found at [DGConvection.md].

## Extension for Hybrid Finite Element Methods

DGKernels are extended to support hybrid finite element methods (HFEM) [!citep](RT-HFEM).

Considering Poisson's equation of the form

\begin{equation}
\begin{aligned}
  -\nabla^2 u &= f && \quad \in \Omega \\
  u &= g && \quad \in \partial \Omega_D \\
  \frac{\partial u}{\partial n} &= h && \quad \in \partial \Omega_N, \\
  \alpha u + \frac{\partial u}{\partial n} &= c && \quad \in \partial \Omega_R,
\end{aligned}
\end{equation}

where $\Omega \subset \mathbb{R}^n$ is the domain, and $\partial
\Omega = \partial \Omega_D \cup \partial \Omega_N \cup \partial \Omega_R$ is its boundary.
$\alpha$ is a given function on $\Omega_R$, which has typical constant value of $1/2$.

The weak form with HFEM for this PDE is to find a triple $(u, \lambda, \lambda_D)$, in discontinuous function spaces on $\Omega$, all internal sides $\Gamma$ and $\partial \Omega_D$ respectively, such that, $\forall (u^\ast, \lambda^\ast, \lambda^\ast_D)$ in the same function spaces,

\begin{equation}
\begin{aligned}
 \left( \nabla u^\ast, \nabla u \right)_\Omega + \left( \lambda^\ast, [ u ] \right)_\Gamma + \left( [ u^\ast ], \lambda \right)_\Gamma
 +\left( u^\ast, \lambda_D \right)_{\partial \Omega_D} + \left( \lambda_D^\ast, u - g \right)_{\partial \Omega_D}
 -\left( u^\ast, h \right)_{\partial \Omega_N}
 +\left( u^\ast, \alpha u - c \right)_{\partial \Omega_R}
 -\left( u^\ast, f \right)_\Omega = 0.
\end{aligned}
\end{equation}

$[u]$ represents the jump of $u$ on an internal side.
It is noted that the orientation of normals on internal sides does not affect the solution of $u$ but flips the sign of $\lambda$.
$\lambda$ and $\lambda_D$ are also known as Lagrange multipliers for weakly imposing the continuity of $u$ across internal sides on $\Gamma$ and imposing the Dirichlet boundary condition at $\Omega_D$.
They resemble the current ($-\frac{\partial u}{\partial n}$) and converge to the current when discretization error gets smaller and smaller with mesh refinement.
HFEM has explicit local conservation, which can be seen if we substitute a test function of $u^\ast$ with constant value of one element of interest and zero elsewhere.
The local conservation is evaluated with *Lagrange multiplier* $\lambda$ and the source function $f$ for an element inside of the domain $\Omega$.

This weak form requires a *compatibility condition* to have a unique solution [!citep](RT-HFEM).
Typically we satisfy this condition by letting the order of the shape function for $u$ two order higher (including two) than the order for $\lambda$.

An alternative way of imposing the Robin boundary condition ($\alpha u + \frac{\partial u}{\partial n} = c$) is to replace $\left( u^\ast, \alpha u - c \right)_{\partial \Omega_R}$ with

\begin{equation}
\begin{aligned}
\left( u^\ast, \lambda_R \right)_{\partial \Omega_R} + \left( \lambda_R^\ast, u - u_R \right)_{\partial \Omega_R} + \left( u_R^\ast, \alpha u_R - c - \lambda_R \right)_{\partial \Omega_R},
\end{aligned}
\end{equation}

with Lagrange multiplier $\lambda_R$ and the projected solution $u_R$ on $\partial \Omega_R$ and their corresponding test functions $\lambda_R^\ast$ and $u_R^\ast$.

A variable for the Lagrange multiplier defined on all interior sides $\Gamma$ can be coupled in DGKernels with a lower-dimensional mesh derived from the main mesh for $\Gamma$.
With this extension, DGKernels can handle three pieces of residual, marked as `Element`, `Neighbor` and `Lower`, on an internal side and corresponding nine pieces of Jacobian, marked as `ElementElement`, `ElementNeighbor`, `NeighborElement`, `NeighborNeighbor`, `PrimaryLower`, `SecondaryLower`, `LowerPrimary`, `LowerSecondary` and `LowerLower`.
Similarly, a variable for the Lagrange multiplier on boundary $\Omega_D$ can be coupled in integrated boundary conditions.

The DGKernal for $\left( \lambda^\ast, [ u ] \right)_\Gamma + \left( [ u^\ast ], \lambda \right)_\Gamma$ can be found at [HFEMDiffusion.md].
The boundary condition for $\left( u^\ast, \lambda_D \right)_{\partial \Omega_D} + \left( \lambda_D^\ast, u - g \right)_{\partial \Omega_D}$ can be found at [HFEMDirichletBC.md] with the generalization of $g$ being either a fixed value or a variable defined on boundary.
With this generalization, [HFEMDirichletBC.md] can be used along with kernels defined on the Robin boundary for $\left( u_R^\ast, \alpha u_R - c - \lambda_R \right)_{\partial \Omega_R}$ for the alternative way of imposing the Robin boundary condition above.

MOOSE does not support mesh adaptation with HFEM currently.

## Example Input File Syntax

DGKernels are added through `DGKernels` input syntax.




# DiracKernels System

Dirac Kernels are used to apply sources/loads at desired point locations in the mesh. The value of the loads is a user-input
value. It is applied at the user-defined location and is effectively null outside of that location, hence the `Dirac` name.

The contribution to the residual is computing by evaluating, at each source location, the product of the test function value at
that location by the value of the source/load.

## Notable parameters

By default, the locations of the sources may not change during the simulation. If a source is detected as moving,
the system will error and prompt the user to provide the `allow_moving_sources` parameter.

By default, only one source may provided at each location in the mesh, any additional source at the same location
is automatically dropped. If multiple sources should share the same location, the user should provide the
`drop_duplicate_points`.

## Example input syntax

In this example, three `ConstantPointSource` are being applied to variable `u` with values 0.1 / -0.1 and -1
at position (0.2 0.3 0.0) / (0.2 0.8 0) and (0.8 0.5 0.8) respectively. `u` is solution to a diffusion equation
with those three sources.





# Distributions System

The distribution system within MOOSE provides an API for defining and retrieving distribution
function objects in C++, primarily for use with the Stochastic Tools module.


# Executioner System

The `Executioner` block describes how the simulation will be executed. It includes commands
to control the solver behavior and time stepping. Time stepping is controlled by a combination
of commands in the `Executioner` block, and the `TimeStepper` block nested within the
`Executioner` block.

The PETSc package is used as the underlying solver in MOOSE, and provides a wide
variety of options to control its behavior. These can be specified in the
Executioner block. Please see the online
[PETSc documentation](http://www.mcs.anl.gov/petsc/documentation/index.html) for
detailed information about these options.

MOOSE provides MultiApp coupling algorithms in all its executioners for tightly-coupled multiphysics simulations.
MultiApps of two groups, those executed before and after the main app, and the main app are solved sequentially within one app coupling iteration.
The execution order of MultiApps within one group is undefined.
Relevant data transfers happen before and after each of the two groups of MultiApps runs.

Because MultiApp allows wrapping another levels of MultiApps, the design enables multi-level app coupling iterations automatically.
App coupling iterations can be relaxed to improve the stability of the convergence.
When a MultiApp is a subapp of a main application and is also the main application for its own subapps, MOOSE allows relaxation of the MultiApp solution
within the main coupling iterations and within the coupling iterations, where the MultiApp is the main application, independently.
More details about the MultiApp coupling algorithms may be found in [FixedPointAlgorithms/index.md])

## Automatic and Default Preconditioning

For most simulations there are two types of solve types that will be used: Newton or Preconditioned
Jacobian Free Newton Krylov (PJFNK). The type is specified using the "solve_type" parameter within the
Executioner block.

Regardless of solve type, NEWTON or PJFNK, preconditioning is an import part of any simulation
(see [Preconditioning/index.md]). By default block diagonal preconditioning is used for all
solves, with two exceptions. If "solve_type" is set to NEWTON or LINEAR and the Preconditioning block is
not defined, single matrix preconditioning (SMP) is used (see [SingleMatrixPreconditioner.md])
with all entries enabled ("full=true"). For NEWTON and LINEAR solves, the auto creation of an SMP objects can be
disabled by setting "auto_preconditioning=false" within the Executioner block (see [CreateExecutionerAction.md]).







# Executors System

See [this page](See executors/Executor.md) for Executor system details.

## Example Input File Syntax




# Functions System

## Overview

`Function`s are used to define functions depending only on time and spatial
position: $f(t,x,y,z)$. These objects can serve a wide variety of purposes,
including (but not limited to) the following:

- defining initial conditions,
- defining residual contributions (sources, boundary conditions, etc.), and
- defining post-processing quantities.

Note that there are exceptions to the rule that `Function`s only depend on
space and time; for example, [MooseParsedFunction.md] may depend on post-processor
values (which may depend on the solution) and scalar variable values.

Moose `Function`s should override the following member functions:

- `Real value(Real, Point)` - the value of the function at a point in space and time
- `Real value(ADReal, ADPoint)` - the AD enabled version of the above function
- `Real timeDerivative(Real, Point)` - the derivative of the function with respect to the first argument (time)
- `RealVectorValue gradient(Real, Point)` -  the spatial derivative with respect to the second argument

and may optionally override the following member functions, which is only needed
for some particular functionality:

- `Real timeIntegral(Real t1, Real t1, const Point & p)`, which computes the
  time integral of the function at the spatial point `p` between the time values
  `t1` and `t2`.

For vector valued functions

- `RealVectorValue vectorValue(Real, Point)` - returning a vector value at a point in space and time
- `RealVectorValue curl(Real, Point)` - returning the curl of the function at a point in space and time
- `Real div(Real, Point)` - returning the divergence of the function at a point in space and time

can be overridden. The optional `Real integral()` and `Real average()` methods
can also be overridden. Note that two overloads exist for the `value()` member
function. This enables evaluation of functions with dual numbers. As most legacy
function do not implement  an AD overload of the `value()` function, the
`Function` base class automatically provides one that uses the non-AD `value()`,
`timeDerivative()`, and `gradient()` member functions to construct an AD result.
Check out `PiecewiseBilinear` to see how to update a function to support AD by
using a templated `valueInternal()` function with virtual `value()` forwarders.


### Functions as Functors

Functions are [Functors](syntax/Functors/index.md). Functors are an abstraction, a base class, for
objects that can compute values at a location in space and time.

As `Functors`, they may be specified to objects such as the
[FunctorAux.md] in their [!param](/AuxKernels/FunctorAux/functor) parameter. This vastly expands the number
of objects that can use `Functions` to compute spatial quantities.

When making a new object using `Functions` to contribute back to MOOSE,
we ask that you consider using [Functors](syntax/Functors/index.md) instead
to naturally enable its use with variables and functor material properties.




# FunctorMaterials

Much like regular materials declare regular material properties, functor materials declare functor material properties.
Functor material properties are properties that are evaluated on-the-fly.
Along with multiple other classes of MOOSE objects, they are [Functors](syntax/Functors/index.md). This allows
for the creation of objects with considerable inter-operability between systems.

## Using functor materials

Following a producer/consumer model, `FunctorMaterials` produce functor material properties, which kernels, boundary conditions, other
functor materials, etc, may consume.
Both regular and functor material properties support a wide array of data types (scalar, vector, tensors,
[automatic differentiation](automatic_differentiation/index.md) versions of all of these). Functor materials, because they are evaluated on-the-fly
and call other functors on-the-fly as well, do not require dependency ordering.

All functor materials support caching in some capacity. This can avoid expensive material property computations, but is
disabled by default due to the potential memory cost. The reader is referred to the [Functors caching documentation](syntax/Functors/index.md#caching).

Functor material properties and regular material properties are generally +NOT+ compatible with each other. Functor material properties can only be used as regular material properties using a
[MaterialFunctorConverter.md] to process them.

Functor materials are created within the `[FunctorMaterials]` block.

If a Functor is reported as missing by the simulation, and it was supposed to be created by a `FunctorMaterial`,
you may use the `Debug/`[!param](/Debug/SetupDebugAction/show_functors) parameter to get more information about what functors were
created and requested.

## Developing with functor materials

### Evaluating functors

See the [Functor system documentation](syntax/Functors/index.md#using-functors) for information on
how to retrieve a functor material property value in a kernel, boundary condition, ... even another functor
material property.

### Creating functor material properties

The functor material property system introduces APIs slightly different from the traditional
material property system for declaring/adding and getting properties. To add a
functor property:

- `addFunctorProperty<TYPE>`

where `TYPE` can be anything such as `Real, ADReal, RealVectorValue, ADRealVectorValue`
etc. To get a functor material property:

- `getFunctor<TYPE>`

It's worth noting that whereas the traditional regular material property system
has different methods to declare/get non-AD and AD properties, the new functor
system has single APIs for both non-AD and AD property types.

Functor material property evaluations are defined using the API:

```c++
template <typename T, typename PolymorphicLambda>
const Moose::FunctorBase<T> &
FunctorMaterial::addFunctorProperty(const std::string & name,
                                    PolymorphicLambda my_lammy,
                                    const std::set<ExecFlagType> & clearance_schedule = {
                                        EXEC_ALWAYS});
```

where the first argument will be the functor name stored in the problem functor database (all functor names must be unique), the second argument is a lambda
defining the property evaluation, and the third optional argument is a set defining at which execution stages the functor evaluation cache should be cleared. The lambda must be callable with two arguments, the first
corresponding to space, and the second corresponding to time, and must return the type `T` of the
`FunctorMaterialProperty`. An example of adding a constant functor material property that returns
a `Real` looks like:

```c++
    addFunctorProperty<Real>(
        "foo", [](const auto &, const auto &) -> Real { return 1.; });
```

An example of a functor material property that depends on a fluid properties user object and pressure and temperature functors looks like

```c++
  addFunctorProperty<ADReal>(_density_name,
                             [this](const auto & r, const auto & t) -> ADReal
                             { return _fluid.rho_from_p_T(_pressure(r, t), _temperature(r, t)); });
```

In the above example, we simply forward the calling arguments along to the captured functors.
`_pressure` and `_temperature` are captured in the lambda function because they are attributes to the local
`FunctorMaterial` class, and `[this]` in the function definition captures all attributes from the class.
Variable functor implementation is described in [MooseVariableBase.md#functor-vars]. A test functor material
class to setup a dummy Euler problem is shown in


### Spatial arguments

See the general [Functor documentation](syntax/Functors/index.md#spatial-overload) for an explanation about the spatial arguments that
may be used for functor material properties.

### Value Caching

See the general [Functor documentation](syntax/Functors/index.md#caching) for an explanation about the
caching capabilities that may be used with functor material properties.

# Functor system

Functors are an abstraction, existing as a base class, that is available to several systems in MOOSE:

- [Variables](syntax/Variables/index.md)
- [Auxiliary variables](syntax/AuxVariables/index.md)
- [Functor material properties](syntax/FunctorMaterials/index.md)
- [Functions](syntax/Functions/index.md)
- [Post-processors](syntax/Postprocessors/index.md)

All functors can be called using the same interfaces. This enables considerable code re-use.
For example, instead of having a kernel for each type of coupled forcing term, like
[CoupledForce.md], [BodyForce.md], [MatCoupledForce.md], [ADMatCoupledForce.md], we could just have a single object
`FunctorForce` and have the force term be a functor.

`Functions` provide a good analogy to `Functors`. Both `Functions` and `Functors` are evaluated on-the-fly at a location in space and time,
but for `Functors`, the space arguments can be an element, a point in an element,
a face of an element, and so on. The time arguments represent the state of the functor : current, previous value (whether in time or iteration),
or value before that previous one.

Note that when using post-processors, instead of being evaluated on-the-fly at
a point in space and time, the most recently computed value is used, in accordance
with the `execute_on` for the post-processor.

If a Functor is reported as missing by the simulation, you may use the `Debug/`[!param](/Debug/SetupDebugAction/show_functors)
parameter to get more information about which functors were created and requested.

## Developing with functors

Functors are stored on the `SubProblem`, a derived class of [Problems](syntax/Problem/index.md) that is
used for solving nonlinear systems. As such, classes do not need to have memory ownership of functors;
they may simply store a reference or a pointer.

In the header of a class using a `Functor` `_functor` you will have:

```
const Moose::Functor<T> & _functor
```

to store a reference to `_functor`, where `T` is the return type of the functor.
For a variable, it should be `ADReal`, while for a vector variable, it should be `ADRealVectorValue`.
If the object using the functor is not leveraging
[automatic differentiation (AD)](automatic_differentiation/index.md), it may be `Real` or `RealVectorValue`.
Note that functors are automatically converted between `AD` and `non-AD` types when retrieved, so
when you retrieve a functor, you must only consider whether the object *using*
the functor (i.e., the "consumer") needs `AD` types. When you create a functor (for example, a
[functor material property](syntax/FunctorMaterials/index.md)) it's best practice to always use the `AD`
return type so as to never discard some derivatives.

The following table summarizes which functors are AD or non-AD (before possible conversion):

| Functor | AD Type |
| :- | :- |
| Variables | AD |
| Auxiliary variables | AD |
| Functor material properties | AD or non-AD (user-defined) |
| Functions | non-AD |
| Post-processors | non-AD |

Functor consumers that derive from `ADFunctorInterface` will report an error
if you attempt to retrieve a functor with a non-AD type when that functor is
an AD type. Functor consumers that instead derive from `NonADFunctorInterface`
such as aux kernels and post-processors, may freely convert an AD functor to
its corresponding non-AD type.

In the constructor of the same class, you will have:

```
CLASSNAME::CLASSNAME(const InputParameters & parameters) :
  ...
  _functor(getFunctor<T>("<functor_parameter_name>")),
  ...
```

where `CLASSNAME` is the name of the class, `T` is still the required return type of the functor, and `<functor_parameter_name>` is
the name of the parameter used for providing the functor in the input.

### Evaluating functors id=using-functors

Functors are evaluated on-the-fly. E.g. they can be viewed as functions of the current location in
space (and time). Functors provide several overloads of the
`operator()` method for different "geometric quantities". One example of a
"geometric quantity" is based around an element, e.g. for an `FVElementalKernel`, the
value of a functor material property in a cell-averaged sense can be obtained by
the syntax

- `_foo(makeElemArg(_current_elem), determineState())`

where here `_foo` is a functor data member of the kernel, `makeElemArg` is a helper routine for creating a
functor element-based spatial argument, and `determineState()` is a helper routine for determining the correct
time state to evaluate at, e.g. the current time for an implicit kernel and the old time for an explicit kernel.

### Spatial arguments to functors id=spatial-overloads

In the following subsections, we describe the various spatial arguments that functors can be evaluated at.
Almost no functor developers should have to concern
themselves with these details as most functor definitions should just appear as functions of
space and time, e.g. the same lambda defining the property evaluation should apply across all
spatial and temporal arguments. However, in the case that a functor developer wishes to
create specific implementations for specific arguments (as illustrated in `IMakeMyOwnFunctorProps`
test class) or simply wishes to know more about the system, we give the details below.

Any call to a functor looks like the following
`_foo(const SpatialArg & r, const TemporalArg & t)`. Below are the possible type overloads of
`SpatialArg`.

#### FaceArg

A `struct` defining a "face" evaluation calling argument. This is composed of

- a face information object which defines our location in space
- a limiter which defines how the functor evaluated on either side of the face should be
  interpolated to the face
- a boolean which states whether the face information element is upwind of the face
- a boolean to indicate whether to correct for element skewness
- a pointer to an element indicating if there is sidedness to the face, and if so, the side of the face.
  If null, the evaluation should use information from both sides of the face, if the functor is defined on both sides.
  If not null, the evaluation should ignore information from the other element.

#### ElemArg

Argument for requesting functor evaluation at an element. This is often used to evaluate
constant monomial or finite volume variables.
Data in the argument:

- The element of interest
- Whether to correct for element skewness

#### ElemQpArg

Argument for requesting functor evaluation at a quadrature point location in an element. Data
in the argument:

- The element containing the quadrature point
- The quadrature point index, e.g. if there are `n` quadrature points, we are requesting the
  evaluation of the ith point
- The quadrature rule that can be used to initialize the functor on the given element

If functors are functions of nonlinear degrees of freedom, evaluation with this
argument will likely result in calls to libMesh `FE::reinit`.

#### ElemSideQpArg

Argument for requesting functor evaluation at quadrature point locations on an element side.
Data in the argument:

- The element
- The element side on which the quadrature points are located
- The quadrature point index, e.g. if there are `n` quadrature points, we are requesting the
  evaluation of the ith point
- The quadrature rule that can be used to initialize the functor on the given element and side

If functors are functions of nonlinear degrees of freedom, evaluation with this
argument will likely result in calls to libMesh `FE::reinit`.

#### ElemPointArg

Argument for requesting functor evaluation at a point located inside an element.
Data in the argument:

- The element containing the point
- The point to evaluate the functor at
- Whether to correct for element skewness

#### Nodes

There is currently no nodal argument to functors.
Please contact a MOOSE developer if you need this.

### Functor caching

By default, functors are always (re-)evaluated every time they are called with
`operator()`. However, the base class `Moose::Functor` has a
`setCacheClearanceSchedule(const std::set<ExecFlagType> & clearance_schedule)` API that allows
control of evaluations (in addition to the `clearance_schedule` argument to `addFunctorProperty` introduced above).
Supported values for the `clearance_schedule` are any combination of
`EXEC_ALWAYS`, `EXEC_TIMESTEP_BEGIN`, `EXEC_LINEAR`, and `EXEC_NONLINEAR`. These will cause cached
evaluations of functors to be cleared always (in fact not surprisingly in this
case we never fill the cache), on `timestepSetup`, on `residualSetup`, and on `jacobianSetup`
respectively. If a functor is expected to depend on nonlinear degrees of freedom, then the cache
should be cleared on `EXEC_LINEAR` and `EXEC_NONLINEAR` (the default `EXEC_ALWAYS` would obviously also work) in
order to achieve a perfect Jacobian. Not surprisingly, if a functor evaluation is cached, then
memory usage will increase.

Functor caching is only currently implemented for `ElemQpArg` and `ElemSideQpArg` spatial
overloads. This is with the idea that calls to `FE::reinit` can be fairly expensive whereas for the
other spatial argument types, evaluation of the functors may be relatively
inexpensive compared to the memory expense incurred from caching. We may definitely implement
caching for other overloads, however, if use cases call for it.

# FVBCs System

For an overview of MOOSE FV please see [/fv_design.md].

The finite volume method (FVM) distinguishes between two types of boundary conditions.

* `FVDirichletBC` prescribes values of the FVM variables on the boundary. This boundary condition acts similarly to Dirichlet boundary conditions in FEM but it is implemented
using a ghost element method.

* `FVFluxBC` prescribes the flux on a boundary. This boundary condition is similar to
integrated boundary conditions in FEM.

Currently, the `FVDirichletBC` category only contains a single class
that applies a fixed value on the boundary. In the future, more specialized
classes will be added.

## FVBCs block

FVM boundary conditions are added to simulation input files in the `FVBCs` as in the example below.

         block=FVBCs
         id=first_fv_bc_example
         caption=Example of the FVBCs block in a MOOSE input file.

In this example input, a diffusion equation with flux boundary conditions on the left and Dirichlet boundary conditions on the right is solved. To understand the differences between
these two boundary conditions, let's start with the diffusion equation:

\begin{equation}
  - \nabla \cdot D \nabla v = 0.
\end{equation}

and the boundary conditions on the left:

\begin{equation}
  - D  \nabla v \cdot \vec{n}= 5,
\end{equation}

where $\vec{n}$ is the outward normal and on the right:

\begin{equation}
  v = 42.
\end{equation}

For seeing how the flux boundary condition is applied, the diffusion equation is integrated
over the extent of an element adjacent to the left boundary and Gauss' theorem is applied to the divergence:

\begin{equation}
  -\int_{\Omega} \nabla \cdot D \nabla v dV =
  -\int_{\partial \Omega_l} D \nabla v \cdot \vec{n} dA
  -\int_{\partial \Omega \setminus \partial \Omega_l} D \nabla v \cdot \vec{n} dA
  = 5 A_{\partial \Omega_l}
  -\int_{\partial \Omega \setminus \partial \Omega_l} D \nabla v \cdot \vec{n} dA=0,
\end{equation}

where $\Omega$ is the element volume, $\partial \Omega_l$ are all faces that belong to the left sideset, $\partial \Omega$ are all faces, and $A_{\partial \Omega_l}$ is the area of face.
Flux boundary conditions are applied by replacing appropriate terms in the FVM balance by the value of the flux prescribed on the boundary.

Dirichlet boundary conditions are applied differently. Let us first write a balance equation for an element that is adjacent to the right boundary:

\begin{equation}
  -\int_{\partial \Omega_r} D \nabla v \cdot \vec{n} dA
  -\int_{\partial \Omega \setminus \partial \Omega_r} D \nabla v \cdot \vec{n} dA  =0,
\end{equation}

MOOSE uses the ghost element method to apply Dirichlet boundary conditions for FVM.
The process of using a ghost elements is the following:

1. Place a virtual element across the Dirichlet boundary.

2. Compute the value of $v$ in the ghost element as the extrapolation of the element value and the desired value on the boundary.

3. Assign the value of $v$ in the ghost element.

4. Evaluate the numerical fluxes as if you were on an interior face.

For implementing the ghost element method an extrapolation must be selected. Currently,
MOOSE FVM only supports linear extrapolation. If the value of the Dirichlet boundary condition is denoted by $v_D$ and the value in the element is denoted by $v_E$, then the ghost element value $v_G$ is:

\begin{equation}
  v_G = 2 v_D - v_E.
\end{equation}

The parameters available in boundary conditions are equivalent to [FEM boundary conditions](syntax/BCs/index.md) and are not discussed in detail here.

## FVBCs source code: FVDirichletBC

`FVDirichletBC` objects assigns a constant value on a boundary.
Implementation of a FVM Dirichlet boundary condition usually only requires overriding the
`boundaryValue` method. The `boundaryValue` method must return the value
of the variable on the Dirichlet boundary.

         start=#include
         end=""
         id=fv_dirichlet_code
         caption=Example source code for `FVDirichletBC`.

## FVBCs source code: FVFluxBC

`FVNeumannBC` objects assign a constant flux on a boundary.
Implementation of a flux boundary condition usually only requires overriding
the `computeQpResidual()` method. `FVNeumannBC` reads a constant value from the
parameters and then returns it in `computeQpResidual()`.

         start=#include
         end=""
         id=fv_neumann_code
         caption=Example source code for `FVNeumannBC`.

## FVBCs source code: FVBurgersOutflowBC

Flux boundary conditions can be more complicated than assigning
a constant value. In this example, the outflow contribution for
the Burgers' equation is computed. The relevant term is (note 1D):

\begin{equation}
\frac{1}{2}  \int \frac{\partial}{\partial x}v^2 dx
= \frac{1}{2}  \left(v^2_R n_R + v^2_L n_L\right),
\end{equation}

where $v_R$ and $v_L$ are the values of $v$ on the left and right
boundaries of the element and $n_R$ and $n_L$ are the outward normals on these
faces. Let's assume that the left side is a boundary face where the `FVBurgersOutflowBC` is applied. On that boundary we have $n_L = -1$.
The `FVBurgersOutflowBC` boundary condition uses upwinding, i.e. it uses the element value $v$
as boundary values on outflow faces.

The code listed below first checks if the left is actually an outflow side by using the cell value of the $v$ (element average, upwinding!) and dotting it with the normal. If $v n_L > 0$, then the left is an outflow side.
In this case the contribution $1/2 v^2 n_L$ is added, otherwise no contribution is added.

         start=FVBurgersOutflowBC::computeQpResidual()
         end=""
         id=fv_burgers_outflow_bc
         caption=Outflow boundary condition for the Burgers' equation.

In this case, the boundary condition does not represent a fixed inflow, but rather
a free outflow condition.


# FVICs System

## Description

The `FVICs` block within an input file is used to define the initial (starting) conditions for
the finite volume variables within your simulation. Initial conditions may be applied to both the "unknowns"
(nonlinear) or auxiliary variables.
It computes the values of the variable at the cell centroids.

## FVICs Block

The preferred syntax is to create a top-level "FVICs" block with subblocks defining the initial
conditions for one or more variables.


## FVICs from an Exodus File

MOOSE contains a shortcut syntax for reading solutions from an Exodus file for the initial
condition from right within the [Variables](Variables/index.html). The name of the variable and the time step from which to read the solution must be supplied.


## Sanity checks on FVICs

- Multiple FV initial conditions may not be applied to the same variable on the same block
- Global initial conditions will conflict with subdomain or boundary restricted ICs on the same variable




# FVInterfaceKernels System

For an overview of MOOSE FV please see [/fv_design.md].

`FVInterfaceKernels` are meant to communicate data at interfaces between
subdomains. An `FVInterfaceKernel` may contribute to the residuals/Jacobians of
a single variable, specified with the parameter `variable1`, or to multiple
variables by also using the `variable2` parameter. There are two additional
critical/required parameters: `subdomain1` and `subdomain2`. In cases for which an
`FVInterfaceKernel` is operating on two variables, `subdomain1` should
correspond to the subdomain(s) neighboring the `boundary` parameter that
`variable1` lives on, and similarly for `subdomain2` and `variable2`. By
checking the `subdomain` parameters against the subdomain IDs of the
`FaceInfo::elem` and `FaceInfo::neighbor` members a `FVInterfaceKernel`
developer can be sure that they are fetching and using sensical data. For
instance, a developer may want to create an `FVInterfaceKernel` that uses
`prop1` on the `subdomain1` side of the `boundary` and `prop2` on the
`subdomain2` side of the boundary. However, MOOSE only provides these APIs for
fetching material properties: `get(AD)MaterialProperty` and
`getNeighbor(AD)MaterialProperty`. The return value of `get(AD)MaterialProperty`
will always correspond to a material property evaluation on the `FaceInfo::elem`
side of a (inter)face, while the return value of
`getNeighbor(AD)MaterialProperty` will always correspond to a material property
evaluation on the `FaceInfo::neighbor` side of a (inter)face. However, when
moving along an interface, it is possible that the `FaceInfo::elem` side of the
interface is sometimes the `subdomain1` side and sometimes the `subdomain2`
side. So making use of the `subdomain` parameters, we provide a protected method
called `elemIsOne()` that returns a boolean indicating whether the
`FaceInfo::elem` side of the interface corresponds to the `subdomain1` side of
the interface. This allows the developer to write code like the following:

```
FVFooInterface::FVFooInterface(const InputParameters & params)
  : FVInterfaceKernel(params),
    _coeff1_elem(getADMaterialProperty<Real>("coeff1")),
    _coeff2_elem(getADMaterialProperty<Real>("coeff2")),
    _coeff1_neighbor(getNeighborADMaterialProperty<Real>("coeff1")),
    _coeff2_neighbor(getNeighborADMaterialProperty<Real>("coeff2"))
{
}

ADReal
FVFooInterface::computeQpResidual()
{
  const auto & coef_elem = elemIsOne() ? _coeff1_elem : _coeff2_elem;
  const auto & coef_neighbor = elemIsOne() ? _coeff2_neighbor : _coeff1_neighbor;

  /// Code that uses coef_elem and coef_neighbor
}
```

and have confidence that they have good data in `coef_elem` and `coef_neighbor`
and have clarity about what is happening in their code.

When using an FVInterfaceKernel which connects variables that belong to different nonlinear systems,
create two kernels with flipped variable and material property parameters. The reason behind this
is that the interface kernel will only contribute to the system which `variable1` belongs to.
For an example, see:



# FVKernels System

For an overview of MOOSE FV please see [/fv_design.md].

For the finite volume method (FVM), `FVKernels` are the base class for `FVFluxKernel`, `FVElementalKernel`. These specialized objects satisfy the following tasks:

* `FVFluxKernel` represents numerical fluxes evaluate on the element faces.
  These terms originate from applying Gauss' divergence theorem.

* `FVElementalKernel` represents terms that do not contain a spatial
  derivative so that Gauss' theorem cannot be applied. These terms include
  time derivatives, externally imposed source terms, and reaction terms.

Note: Currently, the `FVElementalKernel` category only contains kernels
(subclasses) representing time derivatives. Kernels representing externally
imposed sources or reaction terms will be added in the near future.

In the documentation that follows, we will use '-' and '+' to represent
different sides of a face. This is purely notation. In the MOOSE code base, the
'-' side is represented with an `_elem` suffix and the '+' side is represented
with a `_neighbor` suffix. We could just as well have chosen `_left` and
`_right`, or `_1` and `_2`, or `_minus` and `_plus`, but for consistency with previous MOOSE framework
code such as discontinuous Galerkin kernels and node-face constraints, we have
elected to go with the `_elem` and `_neighbor` suffixes.

## FVKernels block

FVM kernels are added to simulation input files in the `FVKernels` block.  The
`FVKernels` block in the example below sets up a transient diffusion problem
defined by the equation:

\begin{equation}
  \frac{\partial v}{\partial t} - \nabla \cdot D \nabla v = 0.
\end{equation}

The time derivative term corresponds to the kernel named `time`, while
the diffusion term is represented by the kernel named `diff`.

         block=FVKernels
         id=first_fv_kernel_example
         caption=Example of the FVKernels block in a MOOSE input file.

The `FVTimeKernel` in the example derives from `FVElementalKernel` so it's a
volumetric contribution to the residual, while the `FVDiffusion` kernel is an
`FVFluxKernel` and it's a face contribution to the residual. The remaining
MOOSE syntax is what you would expect to see in finite element kernel objects:

* `variable` refers to the variable that this kernel is acting on (i.e. into
  which equation does the residual of this term go).  This must be a
  finite-volume variable (defined with `fv = true`) for all FVM kernels.

* `coeff` in kernel `diff` is a material property corresponding to the heat conduction or diffusion coefficient.

The next example shows an `FVKernels` block that solves the one-dimensional
Burgers' equation. The Burgers' equation for speed `v` is given by:

\begin{equation}
  \frac{\partial v}{\partial t} + \frac{1}{2}\frac{\partial }{\partial x} v^2 = 0.
\end{equation}

         block=FVKernels
         id=second_fv_kernel_example
         caption=Example of the FVKernels block in a MOOSE input file for solving one-dimensional Burgers' equation.

Note that the `FVBurgers1D` kernel only works for one-dimensional problems. In
this example, the exact same time derivative kernels as for the diffusion
example is used, but the spatial derivative term is different.

Boundary conditions are not discussed in these examples. Look at
[syntax files](syntax/FVBCs/index.md) for details about boundary conditions.


## FVKernel source code: FVDiffusion example

First, `FVFluxKernels` are discussed.  `FVFluxKernels` are used to calculate
numerical flux contributions from face (surface integral) terms to the
residual. The residual contribution is implemented by overriding the
`computeQpResidual` function.

In the FVM, one solves for the averages of the variables over each element.
The values of the variables on the faces are unknown and must be computed
from the cell average values. This interpolation/reconstruction determines the accuracy
of the FVM.
The discussion is based on the example of `FVDiffusion` that discretizes the diffusion term using a central difference approximation.

         start=template
         end=registerADMooseObject("MooseApp", FVMatAdvection);
         id=fv_diffusion_code
         caption=Example source code for a finite volume kernel discretizing the diffusion term using a central difference.

The kernel `FVDiffusion` discretizes the diffusion term $-\nabla \cdot D(v,\vec{r}) \nabla v$.
Integrating over the extend of an element and using Gauss' theorem leads to:

\begin{equation}
-  \int_{\Omega} \nabla \cdot D(v,\vec{r}) \nabla v dV =  \int_{\partial \Omega} \left(-D(v, \vec{r}) \vec{n}\cdot \nabla v \right) dS.
\end{equation}

The term in parenthesis in the surface integral on the right hand side must be
implemented in the `FVKernel`. However, there is one more step before we can
implement the kernel. We must determine how the values of $D$ and $\nabla v$
depend on the values of $D$ and $v$ on the '+' and '-' side of the face
$\partial \Omega$.  In this example, the following approximation is used:

\begin{equation}
    \left(-D(\vec{r}) \vec{n}\cdot \nabla v \right) \approx \frac{D(v_L,\vec{r}_L) + D(v_R,\vec{r}_R)}{2} \frac{v_R - v_L}{\|\vec{r}_R - \vec{r}_L\|}
\end{equation}

This is a central difference approximation of the gradient on the face that neglects cross
diffusion terms.

Now, the implementation of this numerical flux into `FVDiffusion::computeQpResidual`
is discussed.

* the kernel provides the '-' and '+' values of the variable $v$ as `_u_elem[_qp]` and `_u_neighbor[_qp]`

* the values of the material properties on the '-' side of the face is obtained by `_coeff_elem(getADMaterialProperty<Real>("coeff"))` while
the '+' side value is obtained by calling `getNeighborADMaterialProperty<Real>("coeff")`.

* geometric information about the '-' and '+' adjacent elements is available from the `face_info` object.

The implementation is then straight forward. The first line of the code computes `dudn` which corresponds to the term:

\begin{equation}
 \text{dudn} = \frac{v_R - v_L}{\|\vec{r}_R - \vec{r}_L\|}
\end{equation}

while the second line computes `k` corresponding to:

\begin{equation}
  \text{k} = \frac{D(v_L,\vec{r}_L) + D(v_R,\vec{r}_R)}{2} .
\end{equation}

The minus sign originates from the minus sign in the original expression. Flow from '-' to '+ is defined to be positive.

## FVKernel source code: FVMatAdvection example

In this example the advection term:

\begin{equation}
  \nabla \cdot \left( \vec{u} v \right)
\end{equation}

is discretized using upwinding. The velocity is denoted by $\vec{u}$ and $v$
represents a passive scalar quantity advected by the flow. Upwinding is a
strategy that approximates the value of a variable on a face by taking the
value from the upwind element (i.e. the element where the flow originates from).

         start=FVMatAdvection::
         end=" "
         id=fv_mat_advection_code
         caption=Example source code for a finite volume kernel discretizing advection of a passive scalar.

Integrating the advection term over the element and using Gauss' theorem leads to:

\begin{equation}
   \int_{\Omega}   \nabla \cdot \left( \vec{u} v \right) dV =
   \int_{\partial \Omega} \left(\vec{n} \cdot \vec{u} v \right) dS.
\end{equation}

This term in parenthesis on the right hand side is approximated using upwinding:

\begin{equation}
   \vec{n} \cdot \vec{u} v \approx  \tilde{\vec{u}}\cdot \vec{n}
   \tilde{v}
   ,
\end{equation}

where

\begin{equation}
   \tilde{\vec{u}} = \frac{1}{2} \left( \vec{u}_L + \vec{u}_R \right)
\end{equation}

and  $\tilde{v} = v_L$ if $\tilde{\vec{u}} \cdot \vec{n} > 0$ and $\tilde{v} = v_R$ otherwise.
By convention, the normal $\vec{n}$ points from the '-' side to the '+' side.

The implementation is straight forward. In the constructor the '-' and '+'
velocities are obtained as `RealVectorValue` material properties. The average
is computed and stored in variable `v_avg`. The direction of the flow is
determined using the inner product of `v_avg * _normal` and the residual is
then computed using either the '-' value of $v$ given by `_u_elem[_qp]` or
the '+' value given by `_u_neighbor [_qp]`.

## FVKernel source code: FVTimeKernel

This example demonstrates source code for an `FVElementalKernel`. `FVElementalKernel`
are volumetric terms. In this case, the kernel is `FVTimeKernel`.

         start=FVTimeKernel::computeQpResidual()
         end=template <>
         id=fv_time_code
         caption=Example source code for the finite volume time kernel.

This kernel implements the term:

\begin{equation}
  \frac{\partial v}{\partial t}
\end{equation}

The implementation is identical to the implementation of FEM kernels except that
the FVM does not require multiplication by the test function.

# GlobalParams System

## Overview

The global parameters system is used to define global parameter values in an
input file. Every parameter in the `GlobalParams` block will be inserted into
every block/sub-block where that parameter name is defined. This can be a
useful mechanism of reducing duplication in input files.

Be very careful when using the `GlobalParams` block that you do not accidentally
insert parameter values where you do not intend, as these errors can be
difficult to find. Be particularly wary of parameter names that seem like they
could be very general to a number of different objects and systems.

## Example Input File Syntax

Suppose you have a number of similar objects that share a common parameter
`my_common_parameter`. Then instead of having to list this parameter for each
of your objects:

```
[SomeSystem]
  [objA]
    type = SomeClass
    my_common_parameter = some_value
  []
  [objB]
    type = SomeClass
    my_common_parameter = some_value
  []
[]
```

you can instead list the parameter in the `GlobalParams` block, thus eliminating
some duplication in the input file:

```
[GlobalParams]
  my_common_parameter = some_value
[]

[SomeSystem]
  [objA]
    type = SomeClass
  []
  [objB]
    type = SomeClass
  []
[]
```

Note that the parameter need not belong to the same class or even the same
system; the `GlobalParams` block will insert its parameters into every possible
occurrence of that parameter name in the input file.

If any block/sub-block ever needs a different value than the global value,
then it can simply locally override the value:

```
[GlobalParams]
  my_common_parameter = some_value
[]

[SomeSystem]
  [objA]
    type = SomeClass
  []
  [objB]
    type = SomeClass
    my_common_parameter = some_different_value
  []
[]
```




# HDG Boundary Conditions

HDG boundary conditions implement boundary conditions for physics
implemented in [HDGKernels/index.md]. All hybridized boundary conditions
should inherit from `HDGIntegratedBC` as at the present time all
hybridized boundary conditions are imposed weakly. Classes derived from
`HDGIntegratedBC` must implement the `onBoundary` virtual method. Like
their `HDGKernel` counterparts, hybridized boundary conditions should
populate the data members `_PrimalMat`, `_LMMat`, `_PrimalLM`, `_LMPrimal`,
`_PrimalVec`, and `_LMVec`.

# HDG Kernels

HDG kernels and their boundary condition counterparts,
[HDGBCs/index.md], are advanced systems that should only be developed by
users with a fair amount of finite element experience. For background on
hybridization, we encourage the user to read [!citep](cockburn2009unified) which
presents a unified framework for considering hybridization of discontinuous
Galerkin, mixed, and continuous Galerkin methods for elliptic
problems. [!citep](cockburn2008superconvergent) presents a single-face
hybridizable discontinuous Galerkin (HDG) method for an elliptic problem, in which a
non-zero stabilization term is added to only one face of a given
element. [!citep](nguyen2010hybridizable) presents an HDG method for Stokes
flow. [!citep](nguyen2011implicit) extends HDG to Navier-Stokes. More HDG
literature may be found by looking at the research of Bernardo Cockburn, his
former postdoc Sander Rhebergen, and Rhebergen's former postdoc Tamas
Horvath. Work by Tan Bui-Thanh on upwind HDG methods, like in
[!citep](bui2015godunov) is also worth noting.

A hybridized finite element formulation starts with some primal finite element
discretization. Then some continuity property of the finite element space is
broken. For instance Raviart-Thomas finite elements may be used to solve a mixed
formulation description of a Poisson problem. The Raviart-Thomas elements ensure
continuity of the normal component of the vector field across element faces. We
break that continuity in the finite element space used in the hybridized method
and instead introduce degrees of freedom, that live only on the mesh skeleton
(the faces of the mesh), that are responsible for ensuring the continuity that
was lost by breaking the finite element space. In libMesh/MOOSE implementation
terms, when hybridizing the Raviart-Thomas description of the Poisson problem,
we change from using a `RAVIART_THOMAS` basis to an `L2_RAVIART_THOMAS` basis
and introduce a `SIDE_HIERARCHIC` variable whose degrees of freedom live on the
mesh skeleton. We will refer to the variables that exist "before" the
hybridization as primal variables and the variable(s) that live on the mesh
skeleton as Lagrange multipliers (LMs) or dual variable(s).

We note that some classes of HDG methods, such as the LDG method in
[!citep](cockburn2008superconvergent), have the gradient as an independent
primal variable. With these methods, for diffusion or diffusion-dominated
problems, the primal gradient and primal scalar variable fields can be used to
postprocess a scalar field that converges with order $k + 2$ in the $L^2$ norm,
where $k$ is the polynomial order of the primal scalar variable. However, as
advection becomes dominant, the higher order convergence is lost and
consequently so is the value of having the gradient as an independent
variable. In advection-dominated cases, interior penalty HDG methods, such as
that outlined in [!citep](rhebergen2017analysis), may be a good choice.

## Implementation in MOOSE

HDG kernels derive from [Kernels](Kernels/index.md). However, the methods
that must be overridden are quite different. These are `onElement` and
`onInternalSide`, which implement integrations in the volume of elements and on
internal faces respectively. External boundary condition integration occurs in
[HDGBCs/index.md].

Within `onElement` and `onInternalSide`, hybridized kernel developers have eight
different data structures they need to populate. Six are inherited from the `HDGData`
class). These are

```
  /// Matrix data structures for on-diagonal coupling
  EigenMatrix _PrimalMat, _LMMat;
  /// Vector data structures
  EigenVector _PrimalVec, _LMVec;
  /// Matrix data structures for off-diagonal coupling
  EigenMatrix _PrimalLM, _LMPrimal;
```
And the two declared in `HDGKernel`:
```
  /// Containers for the global degree of freedom numbers for primal and LM variables
  /// respectively
  std::vector<dof_id_type> _primal_dof_indices;
  std::vector<dof_id_type> _lm_dof_indices;
```

The `_PrimalMat` holds the Jacobian entries for the dependence of primal degrees
of freedom on primal degrees of freedom; `_LMMat` is dependence of LM dofs on LM
dofs; `_PrimalLM` is dependence of primal dofs on LM dofs; `_LMPrimal` is
dependence of LM dofs on primal dofs. The `_PrimalVec` and `_LMVec` objects hold
the residuals for the primal and LM degrees of freedom
respectively. `_primal_dof_indices` and `_lm_dof_indices` hold the primal and LM
global degree of freedom numbers respectively for the current
element. `HDGIntegratedBC` classes also inherit from `HDGData` and must also fill
the six matrix and vector structures within their `onBoundary` method.

Note that local finite element assembly occurs twice within a single iteration
of Newton's method. The first assembly occurs prior to the linear solve and adds
into the global residual and Jacobian data structures which represent only the
trace/Lagrange-multiplier degrees of freedom. The linear solve then occurs which
computes the Newton update for the Lagrange multiplier degrees of freedom. This
Lagrange multiplier increment is then used in the second assembly
post-linear-solve to compute the primal variable solution increment. Because
only the Lagrange multiplier variables and their degrees of freedom participate
in the global solve, they are the only variables that live in the nonlinear
system. The primal variables live in the auxiliary system.

# ICs System

## Description

The `ICs` block within an input file is utilized to define the initial (starting) conditions for
the variables within your simulation. Initial conditions may be applied to both the "unknowns"
(nonlinear or scalar variables) or auxiliary variables. The interface for defining an Initial
Condition is to support a function that returns a value at a "Point", and optionally higher order
derivatives at that point (e.g. Gradient, Second).

## ICs Block

The preferred syntax is to create a top-level "ICs" block with subblocks defining the initial
conditions for one or more variables.


## ICs from an Exodus File

MOOSE contains a shortcut syntax for reading solutions from an Exodus file for the initial
condition from right within the [Variables](Variables/index.html). The name of the variable
and the time step from which to read the solution must be supplied.


## Initial Condition Coupling

Initial Conditions objects in MOOSE can couple to other variables in the system. When this occurs
MOOSE will automatically evaluate dependencies and evaluate initial conditions in an order that
supports the valid inspection of variables when computing initial conditions for other variables.

## Gradients

Some shape function families support gradient degrees of freedom (Hermite). To properly initialize
these DOFs, the initial condition system has an optional override for supplying gradient values.

## Inspecting Current Node or Element Pointers

The initial condition system uses a generic projection algorithm for setting the initial condition
for each supported discretization scheme. In the general case, the projection system may choose
to sample anywhere within the domain and not necessarily right on a mesh node or at an element center
position. However, for common FE discretizations such as Lagrange, all of the initial condition
samples are taken at nodes. To support these common cases, InitialCondition derived objects have
access to pointers to both current nodes and current elements. These will be non-null when
samples are taken at the corresponding mesh entity and null otherwise.

## Sanity checks on ICs

- Multiple initial conditions may not be applied to the same variable on the same block
- Multiple initial conditions may not be applied to the same variable on the same boundary
- Global initial conditions will conflict with subdomain or boundary restricted ICs on the same variable

## Block/Boundary Restrictions

The ICs system support both the [BlockRestrictable.md] and
[BoundaryRestrictable.md] interfaces.  When using nodal variables with block
restriction, there is an ambiguity that can occur at inter-block interfaces
where a node sits in elements of two or more different blocks.  To resolve
this ambiguity on multi-block nodes, MOOSE chooses the IC object defined on
the lowest block ID for a node to "win" along the interface; the winning
object's variable *must* be defined on the block - otherwise the IC for the
next lowest block ID for the node is used - and so forth until one has the
variable defined.

## Old and Older ICs

The ICs system supports the ability to set ICs on old and older states. This can be useful for initializing old and older states of variables needed for various time integration schemes. It can be set with the [!param](/ICs/ConstantIC/state) parameter and specifying `OLD` or `OLDER`.







# InterfaceKernels System

Interface kernels are meant to assist in coupling different physics across sub-domains. The most straightforward example is the case in which one wants to set the flux of a specie A in subdomain 0 equal to the flux of a specie B in subdomain 1 at the boundary between subdomains 0 and 1. In mathematical terms, we might be interested in establishing the condition:

\begin{equation}
-D_0 \frac{\partial c_0}{\partial x} = -D_1 \frac{\partial c_1}{\partial x}
\end{equation}

where $D_i$ is the diffusion coefficient of specie $i$ in subdomain $i$, and $c_i$ is the concentration of specie $i$ in subdomain $i$. An example of this condition is shown in the MOOSE test directory; see files below:

[2d_interface/coupled_value_coupled_flux.i]

[/InterfaceDiffusion.C]

[/InterfaceDiffusion.h]

Interface kernels can be used to provide any general flux condition at an interface, and even more generally can be used to impose any interfacial condition that requires access to values of different variables and gradients of different variables on either side of an interface. In an input file, the user will specify at a minimum the following parameters:

- `type`: The type of interface kernel to be used
- `variable`: This is the "primary" variable. Note that the primary variable must exist on the same subdomain as the sideset specified in the `boundary` parameter. The existence of a "primary" and "secondary" or "neighbor" variable ensures that the interface kernel residual and jacobian functions get called the correct number of times. `variable` could be $c_0$ from our example above.
- `neighbor_var`: The "secondary" variable. This could be $c_1$ from our example above.
- `boundary`: The interfacial boundary between the subdomains. Note that this must be a sideset and again must exist on the same subdomain as the primary variable. The fact that this boundary is a sideset allows access to variable gradients.

For additional information about the interface kernel system, don't hesitate to contact the [MOOSE Discussion forum](https://github.com/idaholab/moose/discussions).

## Multiple system support

Using multiple nonlinear system with interface kernels is currently not supported.
The only feature supported, which can at times suffice, notably when using
[MultiApps](syntax/MultiApps/index.md) to couple equations, is to use an auxiliary
variable as the `neighbor_var`.




# Kernels System

A "Kernel" is a piece of physics. It can represent one or more operators or terms in the weak form of
a partial differential equation.  With all terms on the left-hand-side, their sum is referred to as
the "residual". The residual is evaluated at several integration quadrature points over the problem
domain. To implement your own physics in MOOSE, you create your own kernel by subclassing the MOOSE
`Kernel` class.

The Kernel system supports the use of [!ac](AD) for residual calculations, as such
there are two options for creating Kernel objects: `Kernel` and `ADKernel`. To further understand
automatic differentiation, please refer to the [automatic_differentiation/index.md] page for more
information.

In a `Kernel` subclass the `computeQpResidual()` function +must+ be overridden.  This is where you
implement your PDE weak form terms.  For non-AD objects the following member functions can
optionally be overridden:

- `computeQpJacobian()`
- `computeQpOffDiagJacobian()`

These two functions provide extra information that can help the numerical solver(s) converge faster
and better.

Inside your Kernel class, you have access to several member variables for computing the
residual and Jacobian values in the above mentioned functions:

- `_i`, `_j`: indices for the current test and trial shape functions respectively.
- `_qp`: current quadrature point index.
- `_u`, `_grad_u`: value and gradient of the variable this Kernel operates on;
  indexed by `_qp` (i.e. `_u[_qp]`).
- `_test`, `_grad_test`: value ($\psi$) and gradient ($\nabla \psi$) of the
  test functions at the q-points; indexed by `_i` and then `_qp` (i.e., `_test[_i][_qp]`).
- `_phi`, `_grad_phi`: value ($\phi$) and gradient ($\nabla \phi$) of the
    trial functions at the q-points; indexed by `_j` and then `_qp` (i.e., `_phi[_j][_qp]`).
- `_q_point`: XYZ coordinates of the current quadrature point.
- `_current_elem`: pointer to the current element being operated on.

## Optimized Kernel Objects id=optimized

Depending on the residual calculation being performed it is sometimes possible to optimize the
calculation of the residual by precomputing values during the finite element assembly of
the residual vector. The following table details the various Kernel base classes that can be used
for as base classes to improve performance.

| Base | Override | Use |
| :- | :- | :- |
| Kernel\\ +ADKernel+ | computeQpResidual | Use when the term in the [!ac](PDE) is multiplied by both the test function and the gradient of the test function (`_test` and `_grad_test` must be applied) |
| KernelValue\\ +ADKernelValue+ | precomputeQpResidual | Use when the term computed in the [!ac](PDE) is only multiplied by the test function (do not use `_test` in the override, it is applied automatically) |
| KernelGrad\\ +ADKernelGrad+ | precomputeQpResidual | Use when the term computed in the [!ac](PDE) is only multiplied by the gradient of the test function (do not use `_grad_test` in the override, it is applied automatically) |

## Custom Kernel Creation

To create a custom kernel, you can follow the pattern of the [`Diffusion`](/Diffusion.md) or
[`ADDiffusion`](/ADDiffusion.md) objects implemented and included in the MOOSE framework.
Additionally, [Example 2](examples/custom_kernel.md optional=True) in MOOSE provides a step-by-step
overview of creating your own custom kernel. The following describes that calculation of the
diffusion term of a PDE.

The strong-form of the diffusion equation is defined on a 3-D domain $\Omega$ as: find $u$ such
that

\begin{aligned}
-\nabla\cdot\nabla u &= 0 \in \Omega\\
u|_{\partial\Omega_1} &= g_1\\
\nabla u\cdot \hat{n} |_{\partial\Omega_2} &= g_2,
\end{aligned}

where $\partial\Omega_1$ is defined as the boundary on which the value of $u$ is fixed to a known
constant $g_1$, $\partial\Omega_2$ is defined as the boundary on which the flux across the boundary
is fixed to a known constant $g_2$, and $\hat{n}$ is the boundary outward normal.

The weak form is generated by multiplying by a test function ($\psi_i$) and integrating over the
domain (using inner-product notation):

(-\nabla\cdot\nabla u_h, \psi_i) = 0\quad \forall\,\psi_i

and then integrating by parts which gives the weak form:

(\nabla u_h, \nabla \psi_i) - \langle g_2, \psi_i\rangle = 0\quad \forall\,\psi_i,

where $u_h$ is known as the trial function that defines the finite element discretization, $u
\approx u_h = \sum_{j=1}^N u_j \phi_j$, with $\phi_j$ being the basis functions.

The Jacobian, which is the derivative of [weak-form] with respect to $u_j$
$\left(\frac{\partial (.)}{\partial u_j}\right)$, is defined as:

(\nabla \phi_j, \nabla \psi_i)\quad \forall\,\psi_i

As mentioned, the `computeQpResidual` method must be overridden for both flavors of kernels non-AD
and AD. The `computeQpResidual` method for the non-AD version, [`Diffusion`](/Diffusion.md), is
provided in [non-ad-residual].

         re=Real\nDiffusion::computeQpResidual.*?}
         caption=The C++ weak-form residual statement of [weak-form] as implemented in the Diffusion kernel.

This object also overrides the `computeQpJacobian` method to define Jacobian term of [jacobian] as
shown in [non-ad-jacobian].


         re=Real\nDiffusion::computeQpJacobian.*?}
         caption=The C++ weak-form Jacobian statement of [jacobian] as implemented in the Diffusion kernel.


The AD version of this object, [`ADDiffusion`](/ADDiffusion.md), relies on an optimized kernel object
(see [#optimized]), as such it overrides `precomputeQpResidual` as follows.

         re=ADDiffusion::precomputeQpResidual.*?}
         caption=The C++ pre-computed portions of the weak-form residual statement of [weak-form] as implemented in the ADDiffusion kernel.


## Time Derivative Kernels

You can create a time-derivative term/kernel by subclassing `TimeKernel` instead of `Kernel`.  For
example, the residual contribution for a time derivative term is:

\left(\frac{\partial u_h}{\partial t}, \psi_i\right)

where $u_h$ is the finite element solution, and

\frac{\partial u_h}{\partial t}
\equiv
\frac{\partial}{\partial t}
\left(
    \sum_k u_k \phi_k
\right)
= \sum_k \frac{\partial u_k}{\partial t} \phi_k

because you can interchange the order of differentiation and summation.

In the equation above, $\frac{\partial u_k}{\partial t}$ is the time derivative of the $k$th finite
element coefficient of $u_h$. While the exact form of this derivative depends on the time stepping
scheme, without much loss of generality, we can assume the following form for the time derivative:

\frac{\partial u_k}{\partial t} = a u_k + b

for some constants $a$, $b$ which depend on $\Delta t$ and the timestepping method.

The derivative of equation [time-derivative] with respect to $u_j$ is then:

\frac{\partial}{\partial u_j} \left(
    \sum_k \frac{\partial u_k}{\partial t} \phi_k
\right) =
\frac{\partial }{\partial u_j} \left(
    \sum_k (a u_k + b) \phi_k
\right)
 = a \phi_j

So that the Jacobian term for equation [time-derivative] is

\left(a \phi_j, \psi_i\right)

where $a$ is what we call `du_dot_du` in MOOSE.

Therefore the `computeQpResidual()` function for our time-derivative term kernel looks like:

```cpp
return _test[_i][_qp] * _u_dot[_qp];
```

And the corresponding `computeQpJacobian()` is:

```cpp
return _test[_i][_qp] * _phi[_j][_qp] * _du_dot_du[_qp];
```

## Coupling with Scalar Variables

If the weak form has contributions from scalar variables, then this contribution can be
treated similarly as coupling from other spatial variables. See the
[`Coupleable`](source/interfaces/Coupleable.md) interface for how to obtain the variable
values. Residual contributions are simply added to the `computeQpResidual()` function.
Jacobian terms from the test spatial variable and incremental scalar variable are added by
overriding the function `computeQpOffDiagJacobianScalar()`.

Contributions to the scalar variable weak equation (test scalar variable terms) are not
natively treated by the `Kernel` class. Inclusion of these residual and Jacobian contributions
are discussed within [`ScalarKernels`](syntax/ScalarKernels/index.md) and specifically
[`KernelScalarBase`](source/kernels/KernelScalarBase.md).

## Further Kernel Documentation

Several specialized kernel types exist in MOOSE each with useful functionality.  Details for each are
in the sections below.


# Limiters

Limiters, generally speaking, limit the slope when doing high-order (e.g. accuracy order greater than
1, e.g. non-constant polynomial) interpolations from finite volume cell
centroids to faces. This limiting is done to avoid creating oscillations in the
solution field in regions of steep gradients or discontinuities. Slope limiters,
or flux limiters, are generally employed to make the solution Total Variation
Diminishing (TVD). Borrowing notation from
[here](https://en.wikipedia.org/wiki/Total_variation_diminishing), the Total
Variation when space and time have been discretized can be defined as

\begin{equation}
TV(u^n) = TV(u(\centerdot,t^n)) = \sum_j \vert u_{j+1}^n - u_j^n \vert
\end{equation}

where $u$ is the discretized approximate solution, $n$ denotes the time index,
and $u_j^n = u(x_j,t^n)$. A numerical method is TVD if

\begin{equation}
TV(u^{n+1}) \leq TV(u^n)
\end{equation}

Different formulations are used for compressible and incompressible/weakly-compressible
flow.

## Limiting Process for Compressible Flow

Borrowing notation from [!citep](greenshields2010implementation), we will now
discuss computation of limited quantities, represented by $\bm{\Psi}_{f\pm}$ where
$+$ represents one side of a face, and $-$ represents the other side. To be
clear about notation: the equations that follow will have a lot of $\pm$ and
$\mp$. When computing the top quantity (e.g. $+$ for $\pm$) we select the top
quantities throughout the equation, e.g. we select $+$ for $\pm$ and $-$ for
$\mp$. Similarly, when computing bottom quantities we select the bottom
quantities throughout the equation. We will also have a series of "ors" in the
text. In general left of "or" will be for top quantities and right of "or" will
be for bottom quantities.

Interpolation of limited quantities proceeds as follows:

\begin{equation}
\bm{\Psi}_{f\pm} = \left(1 - g_{f\pm}\right)\bm{\Psi}_{\pm} +
g_{f\pm}\bm{\Psi}_{\mp}
\end{equation}

where $\bm{\Psi}_{\pm}$ denotes the $+$ or $-$ cell centroid value of the
interpolated quantity and

\begin{equation}
g_{f\pm} = \beta\left(r_{\pm}\right)\left(1 - w_{f\pm}\right)
\end{equation}

where $\beta\left(r_{\pm}\right)$ represents a flux limiter function and

\begin{equation}
\label{eq:weighting}
w_{f\pm} = \vert \bm{d}_{f\mp}\vert/\left(\vert \bm{d}_{f+}\vert +
\vert\bm{d}_{f-}\vert\right)
\end{equation}

where $\vert\bm{d}_{f-}\vert$ is the norm of the distance from the face to the
$-$ cell centroid and $\vert\bm{d}_{f+}\vert$ is the norm of the distance from
the face to the $+$ cell centroid. Note that this definition of $w_{f\pm}$
differs slightly from that given in [!citep](greenshields2010implementation) in
which the denominator is given by $\vert\bm{d}_{-+}\vert$, the norm of the
distance between the $-$ and $+$ cell centroids. The definition given in
[eq:weighting] guarantees that $w_{f+} + w_{f-} = 1$. Note that for a
non-skewed mesh the definition in [eq:weighting] and
[!citep](greenshields2010implementation) are the same.

The flux limiter function $\beta(r_{\pm})$ takes different forms as shown in
[limiter_summary_compressible]. $r_{\pm}$ is computed as follows

\begin{equation}
r_{\pm} = 2 \frac{\bm{d}_{\pm}\cdot\left(\nabla
\bm{\Psi}\right)_{\pm}}{\left(\nabla_d \bm{\Psi}\right)_{f\pm}} - 1
\end{equation}

where $\left(\nabla \bm{\Psi}\right)_{\pm}$ corresponds to the $+$ or $-$ cell
centroid gradient and $\left(\nabla_d \bm{\Psi}\right)_{f\pm} =
\bm{\Psi}_{\mp} - \bm{\Psi}_{\pm}$.

The following limiters are available in MOOSE. We have noted the convergence
orders of each (when considering that the solution is smooth), whether they are
TVD, and what the functional form of the flux limiting function $\beta(r)$ is.

| Limiter class name  | Convergence Order | TVD | $\beta(r)$                                   |
| ------------------- | ----------------- | --- | -------------------------------------------- |
| `VanLeer`           | 2                 | Yes | $\frac{r +\text{abs}(r)}{1 + \text{abs}(r)}$ |
| `Upwind`            | 1                 | Yes | 0                                            |
| `CentralDifference` | 2                 | No  | 1                                            |
| `MinMod`            | 2                 | Yes | $\text{max}(0, \text{min}(1, r))$            |
| `SOU`               | 2                 | No  | $r$                                          |
| `QUICK`             | 2                 | No  | $\frac{3+r}{4}$                              |

## Limiting Process for Incompressible and Weakly-Compressible flow

A full second-order upwind reconstruction is used for incompressible and weakly-compressible solvers. In this reconstruction, the limited quantity at the face is expressed as follows:

\begin{equation}
\bm{\Psi}_f = \bm{\Psi}_C + \beta(r) ((\nabla \bm{\Psi})_C \cdot \bm{d}_{fC})
\end{equation}

where:

- $\bm{\Psi}_f$ is the value of the variable at the face
- $\bm{\Psi}_C$ is the value of the variable at the cell
- $(\nabla \bm{\Psi})_C$ is the value of the gradient at the cell, which is computed with second-order methods (Green-Gauss without skewness correction and Least-Squares for skewness corrected)
- $\bm{d}_{fC}$ is the distance vector from the face to the cell used in the interpolation
- $\beta(r)$ is the limiting function

Two kinds of limiters are supported: slope-limited and face-value limited. These limiters are defined below.

For slope-limiting, the approximate gradient ratio (or flux limiting ratio) $r$ is defined as follows:

\begin{equation}
r = 2 \frac{\bm{d}_{NC} \cdot (\nabla \bm{\Psi})_C}{\bm{d}_{NC} \cdot (\nabla \bm{\Psi})_f} - 1
\end{equation}

where:

- $\bm{d}_{NC}$ is the vector between the neighbor and current cell adjacent to the face
- $(\nabla \bm{\Psi})_f$ is the gradient of the variable at the face, which is computed by linear interpolation of second-order gradients at the adjacent cells to the face

For face-value limiting, the limiting function is defined as follows:

\begin{equation}
r =
\begin{cases}
    \frac{|\Delta_f|}{\Delta_{\text{max}}} & \text{if } \Delta_f > 0 \\
    \frac{|\Delta_f|}{\Delta_{\text{min}}} & \text{if } \Delta_f \leq 0
\end{cases}
\end{equation}

where:

- $\Delta_f = (\nabla \bm{\Psi})_C \cdot \bm{d}_{fC}$ is the increment at the face
- $\Delta_{\text{max}} = \bm{\Psi}_{\text{max}} - \bm{\Psi}_C$ is the maximum increment
- $\Delta_{\text{min}} = \bm{\Psi}_{\text{min}} - \bm{\Psi}_C$ is the minimum increment

The maximum and minimum variable values, $\Delta_{\text{max}}$ and $\Delta_{\text{min}}$, respectively, are computed with a two-cell stencil. In this method, the maximum value is determined as the maximum cell value of the two faces adjacent to the face and their neighbors, respectively. Similarly, the minimum value is computed as the minimum cell value for these cells.

Each of the limiters implemented along with the implementation reference, limiting type, whether they are TVD, and the functional form of the flux limiting function $\beta(r)$ is shown in [limiter_summary_incompressible].

| Limiter class name                              | Limiting Type | TVD | $\beta(r)$                                                        |
| ----------------------------------------------- | ------------- | --- | ----------------------------------------------------------------- |
| `VanLeer` [!citep](harten1997)                  | Slope         | Yes | $\frac{r +\text{abs}(r)}{1 + \text{abs}(r)}$                      |
| `MinMod` [!citep](harten1997)                   | Slope         | Yes | $\text{max}(0, \text{min}(1, r))$                                 |
| `QUICK` [!citep](harten1997)                    | Slope         | Yes | $\text{min}(1,\text{max}(\text{min}(\frac{1 + 3r}{4}, 2r, 2),0))$ |
| `SOU` [!citep](harten1997)                      | Face-Value    | No  | $\text{min}(1,1/r)$                                               |
| `Venkatakrishnan` [!citep](venkatakrishnan1993) | Face-Value    | No  | $\frac{2r+1}{r(2r+1)+1}$                                          |

To illustrate the performance of the limiters, a dispersion analysis is developedand presented in [dispersion].
This consists of the advection of a passive scalar in a Cartesian mesh at 45 degrees.
The exact solution, without numerical diffusion, is a straight line at 45 degrees
dividing the regions with a scalar concentration of 1 and 0.

In general, we recomment using `VanLeer` and `MinMod` limiters for most of the
applications considering that they provide truly bounded solutions.

      style=display: block;margin-left:auto;margin-right:auto;width:40%;
      id=dispersion
      caption=Dispersion problem, advection in a Cartesian mesh at 45 degrees.

The results and performance of each of the limiters are shown in [dispersion_line].
This image provides an idea of the limiting action and results that
can be expected for each of the limiters.

      style=display: block;margin-left:auto;margin-right:auto;width:40%;
      id=dispersion_line
      caption=Performance of each of the limiters in a line perpendicular to the advection front.


# LinearFVBCs System

The difference between `LinearFVBCs` and `FVBCs` is that the boundary quantities
computed by the former (boundary values, gradients, etc.) are used in routines
within linear FV kernels. This is due to the fact that boundary conditions may need to be
applied in different manners for different terms in the partial differential equation.
This means that the `LinearFVBCs` only provide objects to specify these boundary quantities,
and would not contribute to the system matrix and right hand side directly (only through kernels).

For more information on general design choices in this setting [click here](/linear_fv_design.md)

## LinearFVBCs block

FVM boundary conditions are added to simulation input files in the `LinearFVBCs` as in the example below.

         block=LinearFVBCs
         caption=Example of the LinearFVBCs block in a MOOSE input file.

In this example input, an advection equation with Dirichlet boundary condition on the left
and outflow boundary conditions on the right is solved. To understand the differences between
these two boundary conditions, let's start with the advection equation:

\begin{equation}
  \nabla \cdot (\vec{v} u) = S,
\end{equation}

with $\vec{v}$ denoting the velocity vector, $u$ the solution, and $S$ a potentially space-dependent
source term. The boundary condition on the left can be expressed as:

\begin{equation}
  u_b = f(x_b),
\end{equation}

while the outflow boundary expresses outward advection with the solution value
on the boundary and a predefined velocity.

Both boundary conditions can be applied in an integral sense through the discretized
advection term on the cell adjacent to the boundary:

\begin{equation}
  \int\limits_{V_b} \nabla \cdot (\vec{v} u) dV \approx \left(\sum\limits_i \vec{n}_i
  \cdot \vec{v}_i u_{f,i}|S_i|\right) + \vec{n}_b \cdot \vec{v}_b u_b |S_b|~,
\end{equation}

where the $i$ index denotes internal faces of the cell, while $b$ denotes the only face on the boundary.
This means that the only thing we need to supply to this formula is a way to compute the contributions to
the system matrix and right hand side from the boundary value $u_b$.
For example for the Dirichlet boundary $u_b = f(x)$,
while for the outflow boundary it can be either the cell centroid value ($u_b = u_C$)
or an extrapolated value. This also means that the Dirichlet boundary contributes to
the right hand side of the system only, whereas the outflow boundary condition can contribute to both.

## Functions to override:

Different linear finite volume kernels might use the quantities provided by these boundary
conditions differently, but these APIs should be implemented for boundary conditions of linear systems:

- `computeBoundaryValue` computes the boundary value of the field.
- `computeBoundaryNormalGradient` computes the normal gradient of the variable on this boundary.

For derived classes of linear system boundary conditions, we recommend following the same design pattern as the
`LinearAdvectionDiffusionBC` parent class.
For all boundary conditions (Neumann and Dirichlet) for an advection-diffusion problem,
we implemented the following four APIs:

- `computeBoundaryValueMatrixContribution` computes the matrix contribution that would come from
  the boundary value of the field, extensively used within advection kernels.
  For example, on an outflow boundary in an advection problem,
  without using linear extrapolation, one can use the cell value
  as an approximation for the boundary value: $u_b = u_C$. In this case, we can treat the outflow term
  implicitly by adding a $\vec{v} \cdot \vec{n} |S_b|$ term to the matrix which comes from
  $\vec{v} \cdot \vec{n} u_C |S_b|$ outward flux term. This function will return
  $1$ (as it is just the cell value) and the $\vec{v} \cdot \vec{n} |S_b|$ multipliers are added
  in the advection kernel.
- `computeBoundaryValueRHSContribution` computes the right hand side contributions for terms that
  need the boundary value of the field, extensively used within advection kernels.
  Using the same example as above, by employing an extrapolation to the boundary face to determine the
  boundary value, we get the following expression: $u_b = u_C+\nabla u_C d_{Cf}$, where $d_{Cf}$ is
  the vector pointing to the face center from the cell center. In this case, besides the same matrix
  contribution as above, we need to add the following term to the right hand side:
  $\vec{v} \cdot \vec{n} \nabla u_C d_{Cf} |S_b|$. Therefore, this function returns $\nabla u_C d_{Cf}$
  (as it is just the value contribution) and the other multipliers are added in the advection kernel.
- `computeBoundaryGradientMatrixContribution` computes the matrix contributions for terms that need the
  boundary gradient of the field, extensively used within diffusion kernels. Let us take a Dirichlet
  boundary condition and a diffusion kernel for example. The integral form of the diffusion term
  requires the computation of the surface normal gradient which can be approximated on an orthogonal grid as:
  \begin{equation}
    -\int\limits_{S_f}D\nabla u \vec{n}dS  \approx -D\frac{u_b - u_C}{|d_Cf|}|S_f|,
  \end{equation}
  which means that the term including $u_C$ can go to the matrix of coefficients. Therefore, this
  function will return $\frac{1}{|d_Cf|}$ with additional multipliers added at the kernel level.
- `computeBoundaryGradientRHSContribution` computes the right hand side contributions
  for terms that need the boundary gradient of the field, extensively used within diffusion kernels.
  Using the same example as above, the remaining part of the expression belongs to the right hand side
  meaning that a $\frac{u_b}{|d_Cf|}$ term will be added with additional multipliers
  applied at the kernel level.

## LinearFVBCs source code: LinearFVAdvectionDiffusionFunctorDirichletBC

`LinearFVAdvectionDiffusionFunctorDirichletBC` object assigns a value on a boundary. This value is computed using a moose
functor. For more information on the functor system in moose, see [Functors/index.md].

         start=#include
         end=""
         caption=Example source code for `LinearFVAdvectionDiffusionFunctorDirichletBC`.


# LinearFVKernels System

For the finite volume method (FVM) when used without Newton's method, `LinearFVKernel` is the base class for `LinearFVFluxKernel` and `LinearFVElementalKernel`. These specialized objects satisfy the following tasks:

* `LinearFVFluxKernel` adds contributions to system matrices and right hand sides coming from flux terms over
  the faces between cells and boundaries. Diffusion and advection terms in PDEs serve as good examples
  for these kernels.

* `LinearFVElementalKernel` adds contributions to system matrices and right hand sides from volumetric integrals.
  Volumetric source terms or reaction terms serve as good examples for these kernels.

For more information on general design choices in this setting [click here](/linear_fv_design.md)

## LinearFVKernels block

FVM kernels which contribute to systems that are not solved via Newton's method
are added to simulation input files in the `LinearFVKernels` block.  The
`LinearFVKernels` block in the example below sets up a steady-state diffusion problem
defined by the equation:

\begin{equation}
  - \nabla \cdot D \nabla u = S.
\end{equation}

The diffusion term is represented by the kernel named `diffusion`.

         block=LinearFVKernels
         caption=Example of the LinearFVKernels block in a MOOSE input file.

The `LinearFVSource` in the example derives from `LinearFVElementalKernel` so it's a
volumetric contribution to the right hand side, while the `LinearFVDiffusion` is an
`LinearFVFluxKernel` and it's a face contribution to the system matrix and right hand side.
The remaining MOOSE syntax is what you would expect to see in finite element kernel objects.
The `variable` parameter refers to the variable that this kernel is acting on (i.e. into
which equation do the contributions of this term go). This must be a linear finite-volume
variable in this case.

Boundary conditions are not discussed in these examples. We recommend visiting the
[LinearFVBCs/index.md) page for details about boundary conditions.


# Line Search System

This system is meant for creating custom line searches. In general the line
searches associated with the underlying non-linear solver library should be
sufficient. Custom line searches should inherit from `LineSearch` (a pure
virtual) and implement some line-searching capability.

# Materials System

The material system is the primary mechanism for defining spatially varying properties. The system
allows properties to be defined in a single object (a `Material`) and shared among the many other
systems such as the [Kernel](syntax/Kernels/index.md) or [BoundaryCondition](syntax/BCs/index.md)
systems. Material objects are designed to directly couple to solution variables as well as other
materials and therefore allow for capturing the true nonlinear behavior of the equations.

The material system relies on a producer/consumer relationship: `Material` objects +produce+
properties and other objects (including materials) +consume+ these properties.

The properties are produced on demand, thus the computed values are always up to date. For example, a
property that relies on a solution variable (e.g., thermal conductivity as function of temperature)
will be computed with the current temperature during the solve iterations, so the properties are
tightly coupled.

The material system supports the use of automatic differentiation for property calculations, as such
there are two approaches for producing and consuming properties: with and without automatic
differentiation. The following sections detail the producing and consuming properties using the
two approaches. To further understand automatic differentiation, please refer to the
[automatic_differentiation/index.md] page for more information.

The proceeding sections briefly describe the different aspects of a `Material` object for
producing and computing the properties as well as how other objects consume the properties. For an
example of how a `Material` object is created and used please refer to
[ex08_materials.md optional=True].

## Producing/Computing Properties

Properties must be produced by a `Material` object by declaring the property with one of two methods:

1. `declareProperty<TYPE>("property_name")` declares a property with a name "property_name" to be
   computed by the `Material` object.
1. `declareADProperty<TYPE>` declares a property with a name "property_name" to be
   computed by the `Material` object that will include automatic differentiation.

The `TYPE` is any valid C++ type such an `int` or `Real` or `std::vector<Real>`. The properties must
then be computed within the `computeQpProperties` method defined within the object.

The property name is an arbitrary name of the property, this name should be set such that it
corresponds to the value be computed (e.g., "diffusivity"). The name provided here is the same name
that will be used for consuming the property. More information on names is provided in
[#property-names] section below.

For example, consider a simulation that requires a diffusivity term. In the `Material` object
header a property is declared (in the C++ since) as follows.


All properties will either be a `MaterialProperty<TYPE>` or `ADMaterialProperty<TYPE>`
and must be a non-const reference. Again, the `TYPE` can be any C++ type. In this example, a scalar
`Real` number is being used.

In the source file the reference is initialized in the initialization list using the aforementioned
declare functions as follows. This declares the property (in the material property sense) to be
computed.


The final step for producing a property is to compute the value. The computation occurs within a
`Material` object `computeQpProperties` method. As the method name suggests, the purpose of the
method is to compute the values of properties at a quadrature point. This method is a virtual method
that must be overridden. To do this, in the header the virtual method is declared (again in the C++
sense).


In the source file the method is defined. For the current example this definition computes the
"diffusivity" as well another term, refer to [ex08_materials.md optional=True].


The purpose of the content of this method is to assign values for the properties at a quadrature
point. Recall that "_diffusivity" is a reference to a `MaterialProperty` type. The `MaterialProperty`
type is a container that stores the values of a property for each quadrature point. Therefore, this
container must be indexed by `_qp` to compute the value for a specific quadrature point.

`ExampleMaterial` can call `isPropertyActive(_diffusivity.id())` in its `computeQpProperties` to
check whether this property is consumed during the run-time. This function provides a capability
of skipping evaluations of certain material properties within a material when such evaluations are
costly for performance optimization. MOOSE calls materials to do the evaluations when needed.
This `isPropertyActive` routine gives code developers a finer control on the material property
evaluation.

## Consuming Properties

Objects that require material properties consume them using one of two functions

1. `getMaterialProperty<TYPE>("property_name")` retrieves a property with a name "property_name" to be
   consumed by the object.
1. `getADMaterialProperty<TYPE>("property_name")` retrieves a property with a name "property_name" to be
   consumed by the object that will include automatic differentiation.

For an object to consume a property the same basic procedure is followed. First in the consuming
objects header file a `MaterialProperty` with the correct type (e.g., `Real` for the diffusivity
example) is declared (in the C++ sense) as follows. Notice, that the member variable is a +const+
reference. The const is important. Consuming objects cannot modify a property, it only uses the
property so it is marked to be constant.


In the source file the reference is initialized in the initialization list using the aforementioned
get methods. This method initializes the `_diffusivity` member variable to reference the
desired value of the property as computed by the material object.


The name used in the get method, "diffusivity", in this case is not arbitrary. This name corresponds
with the name used to declare the property in the material object.

If a material property is declared for automatic differentiation (AD) using `declareADProperty`
then it +must+ be consumed with the `getADMaterialProperty`. The same is true for non-automatic
differentiation; properties declared with `declareProperty` +must+ be consumed with the
`getMaterialProperty` method.

### Optional Properties

Objects can weakly couple to material properties that may or may not exist.

1. `getOptionalMaterialProperty<TYPE>("property_name")` retrieves an optional property with a name "property_name" to be consumed by the object.
1. `getOptionalADMaterialProperty<TYPE>("property_name")` retrieves an optional property with a name "property_name" to be consumed by the object that will include automatic differentiation.

This API returns a reference to an optional material property
(`OptionalMaterialProperty` or  `OptionalADMaterialProperty`). If the requested
property is not provided by any material this reference will evaluate to
`false`. It is the consuming object's responsibility to check for this before
accessing the material property data. Note that the state of the returned
reference is only finalized _after_ all materials have been constructed, so a
validity check must _not_ be made in the constructor of a material class but
either at time of first use in `computeQpProperties` or in `initialSetup`.

## Property Names id=property-names

When creating a Material object and declaring the properties that shall be computed, it is often
desirable to allow for the property name to be changed via the input file. This may be accomplished
by adding an input parameter for assigning the name. For example, considering the example above
the following code snippet adds an input parameter, "diffusivity_name", that allows the input
file to set the name of the diffusivity property, but by default the name remains "diffusivity".

```c++
params.addParam<MaterialPropertyName>("diffusivity_name", "diffusivity",
                                      "The name of the diffusivity material property.");
```

In the material object, the declare function is simply changed to use the parameter name rather
than string by itself. By default a property will be declared with the name "diffusivity".


However, if the user wants to alter this name to something else, such as "not_diffusivity" then
the input parameter "diffusivity_name" is simply added to the input file block for the
material.

```text
[Materials]
  [example]
    type = ExampleMaterial
    diffusivity_name = not_diffusivity
  []
[]
```

On the consumer side, the get method will now be required to use the name "not_diffusivity" to
retrieve the property. Consuming objects can also use the same procedure to allow for custom
property names by adding a parameter and using the parameter name in the get method in the same
fashion.


## Default Material Properties

The `MaterialPropertyName` input parameter also provides the ability to set default values for scalar
(`Real`) properties. In the above example, the input file can use number or
parsed function (see [MooseParsedFunction.md]) to define a the property value. For example, the input
snippet above could set a constant value.

```text
[Materials]
  [example]
    type = ExampleMaterial
    diffusivity_name = 12345
  []
[]
```

## Stateful Material Properties

In general properties are computed on demand and not stored. However, in some cases values of
material properties from a previous timestep may be required. To access properties two
methods exist:

- `getMaterialPropertyOld<TYPE>` returns a reference to the property from the previous timestep.
- `getMaterialPropertyOlder<TYPE>` returns a reference to the property from two timesteps before the
  current.

This is often referred to as a "state" variable, in MOOSE we refer to them as "stateful material
properties." As stated, material properties are usually computed on demand.


When a stateful property is requested through one of the above methods this is no longer the
case. When it is computed the value is also stored for every quadrature point on every element. As
such, stateful properties can become memory intensive, especially if the property being stored is a
vector or tensor value.

## Material Property Output

Output of `Material` properties is enabled by setting the "outputs" parameter. The following example
creates two additional variables called "mat1" and "mat2" that will show up in the output file.


`Material` properties can be of arbitrary (C++) type, but not all types can be output. The following
table lists the types of properties that are available for automatic output.

| Type | AuxKernel | Variable Name(s) |
| :- | :- | :- |
| Real | `MaterialRealAux` | prop |
| RealVectorValue | `MaterialRealVectorValueAux` | prop_1, prop_2, and prop_3 |
| RealTensorValue | `MaterialRealTensorValueAux` | prop_11, prop_12, prop_13, prop_21, etc. |

## Material sorting

Materials are sorted such that one material may consume a property produced by
another material and know that the consumed property will be up-to-date,
e.g. the producer material will execute before the consumer material. If a
cyclic dependency is detected between two materials, then MOOSE will produce an
error.

## Functor Material Properties id=functor-props

Functor materials are a special kind of materials used for on-the-fly material property evaluation.
Please refer to the [syntax page for FunctorMaterials](FunctorMaterials/index.md) for more information.

## Advanced Topics

### Evaluation of Material Properties on Element Faces

MOOSE creates three copies of a *non-boundary restricted* material for evaluations on quadrature points of elements, element faces on both the current element side and the neighboring element side.
The name of the element interior material is the material name from the input file, while the name of the element face material is the material name appended with `_face` and the name of the neighbor face material is the material name appended with `_neighbor`.
The element material can be identified in a material with its member variable `_bnd=false`.
The other two copies have `_bnd=true`.
The element face material and neighbor face material differentiate with each other by the value of another member variable `_neighbor`.
If a material declares multiple material properties and some of them are not needed on element faces, users can switch off their declaration and evaluation based on member variable `_bnd`.

### Interface Material Objects

MOOSE allows a material to be defined on an internal boundary of a mesh with a specific material type `InterfaceMaterial`.
Material properties declared in interface materials are available on both sides of the boundary.
Interface materials allows users to evaluate the properties on element faces based on quantities on both sides of the element face.
Interface materials are often used along with [InterfaceKernel](syntax/InterfaceKernels/index.md).

### Discrete Material Objects

A "[Discrete](http://www.dictionary.com/browse/discrete)" `Material` is an object that may be
detached from MOOSE and computed explicitly from other objects. An object inheriting from
[MaterialPropertyInterface](http://www.mooseframework.org/docs/doxygen/moose/classMaterialPropertyInterface.html)
may explicitly call the compute methods of a `Material` object via the `getMaterial` method.

The following should be considered when computing `Material` properties explicitly.

- It is possible to disable the automatic computation of a `Material` object by MOOSE by setting
  the `compute=false` parameter.
- When `compute=false` is set the compute method (`computeQpProperties`) is +not+ called by MOOSE,
  instead it must be called explicitly in your application using the `computeProperties` method
  that accepts a quadrature point index.
- When `compute=false` an additional method should be defined, `resetQpProperties`, which sets the
  properties to a safe value (e.g., 0) for later calls to the compute method. Not doing this can
  lead to erroneous material properties values.

The original intent for this functionality was to enable to ability for material properties to be
computed via iteration by another object, as in the following example. First, consider define a
material (`RecomputeMaterial`) that computes the value of a function and its derivative.

f(p) = p^2v

and

f'(p) = 2pv,

where v is known value and not a function of p. The following is the compute portion of this object.


Second, define another material (`NewtonMaterial`) that computes the value of $p: f(p)=0$ using
Newton iterations. This material declares a material property (`_p`) which is what is solved for by
iterating on the material properties containing `f` and `f'` from `RecomputeMaterial`. The
`_discrete` member is a reference to a `Material` object retrieved with `getMaterial`.


To create and use a "Discrete" `Material` use the following to guide the process.

1. Create a `Material` object by, in typical MOOSE fashion, inheriting from the `Material` object in
   your own application.
1. In your input file, set `compute=false` for this new object.
1. From within another object (e.g., another Material) that inherits from `MaterialPropertyInterface`
   call the `getMaterial` method. Note, this method returns a reference to a `Material` object, be
   sure to include `&` when calling or declaring the variable.
1. When needed, call the `computeProperties` method of the `Material` being sure to provide the
   current quadrature point index to the method (`_qp` in most cases).





# Mesh System

## Overview

There are two primary ways of creating a mesh for use in a MOOSE simulation: "offline generation" through
a tool like [CUBIT](https://cubit.sandia.gov/) from [Sandia National Laboratories](http://www.sandia.gov/), and
"online generation" through programmatic interfaces. CUBIT is useful for creating complex geometries, and can be
licensed from Coreform for a fee depending on the type of organization and work
being performed. Other mesh generators can work as long as they output a file format that is
supported by the [FileMesh](/FileMesh.md) object.

## Example Syntax and Mesh Objects

Mesh settings are applied with the `[Mesh]` section in input files, for example the basic input file
syntax for generating a simple square mesh is shown below. For additional information on the other types
of Mesh objects refer to the individual object pages listed below.





## MeshGenerator System

The MeshGenerator System is useful for programmatically constructing a mesh. This includes generating the mesh
from a serious of points and connectivity, adding features on the fly, linearly transforming the mesh, stitching
together pieces of meshes, etc. There are several built-in generators but this system is also extendable. MeshGenerators
may or may not consumer the output from other generators and produce a single mesh. They can be chained together
through dependencies so that complex meshes may be built up from a series of simple processes.

### Mesh Generator development

Mesh generator developers should call `mesh->set_isnt_prepared()` at the end of
the `generate` routine unless they are confident that their mesh is indeed
prepared. Examples of actions that render the mesh unprepared are

- Translating, rotating, or scaling the mesh. This will conceptually change the
  mesh bounding box, invalidate the point locator, and potentially change the
  spatial dimension of the mesh (e.g. rotating a line from the x-axis into the
  xy plane, etc.)
- Adding elements. These elements will need their neighbor links set in order
  for things like finite volume to work
- Changing element subdomains. This will invalidate the mesh subdomain cached
  data on the `libMesh::MeshBase` object
- Changing boundary IDs. This invalidates global data (e.g. data aggregated
  across all processes) in the `libMesh::BoundaryInfo` object

When in doubt, the mesh is likely not prepared. Calling `set_isnt_prepared` is a
defensive action that at worst will incur an unnecessary `prepare_for_use`,
which may slow down the simulation setup, and at best may save follow-on mesh
generators or simulation execution from undesirable behavior.

### DAG and final mesh selection id=final

When chaining together several MeshGenerators, you are implicitly creating a DAG (directed acyclic graph).
MOOSE evaluates and generates the individual objects to build up your final mesh. If your input file has
multiple end points, (e.g. B->A and C->A) then MOOSE will issue an error and terminate. Generally, it doesn't
make sense to have multiple end points since the output of one would simply be discarded anyway. It is possible
to force the selection of a particular end point by using the [!param](/Mesh/MeshGeneratorMesh/final_generator)
parameter in the Mesh block. This parameter can be used on any generator whether there is ambiguity or not in the generator dependencies.


## Outputting The Mesh

Since MOOSE contains a lot of ability to read/generate/modify meshes - it's often useful to be able to run all of
the Mesh related portions of the input file and then output the mesh.  This mesh can then be viewed (such as
with Peacock) or used in other MOOSE input files for further combination/modification.

This can be achieved by using the command line option `--mesh-only`.  By default `--mesh-only` will write a
mesh file with `_in.e` (the opposite of the `_out.e` that is appended from the output system)
appended to the input file name.  You can also optionally provide a mesh filename to
write out using `--mesh-only output_file.e`. When using the `--mesh-only` option, by default any extra element integers
defined on the mesh will also be outputted to the output Exodus file. To prevent extra element ids from being
output, the parameter `output_extra_element_ids` should be set to `false` in the `[Outputs]` block of the
input file as shown below:

```
[Outputs]
  [out]
    type = Exodus
    output_extra_element_ids = false
  []
[]
```

Alternatively, if only a subset of extra element ids should be outputted to the Exodus file, the parameter
`extra_element_ids_to_output` should be set in the `[Outputs]` block of the input file like so:

```
[Outputs]
  [out]
    type = Exodus
    output_extra_element_ids = true
    extra_element_ids_to_output = 'id_to_output1 id_to_output2 ...'
  []
[]
```

Here are a couple of examples showing the usage of `--mesh-only`:

```
# Will run all mesh related sections in input_file.i and write out input_file_in.e
./myapp-opt -i input_file.i --mesh-only

# Will do the same but write out mesh_file.e
./myapp-opt -i input_file.i --mesh-only mesh_file.e

# Run in parallel and write out parallel checkpoint format (which can be read as a split)
mpiexec -n 3 ./myapp-opt -i input_file.i Mesh/parallel_type=distributed --mesh-only mesh_file.cpr
```

## Named Entity Support

Human-readable names can be assigned to blocks, sidesets, and nodesets. These names will be
automatically read in and can be used throughout the input file. Mesh generators such as CUBIT will
generally provide the capability internally.  Any parameter that takes entity IDs in the input file
will accept either numbers or "names". Names can also be assigned to IDs on-the-fly in existing
meshes to ease input file maintenance (see example). On-the-fly names will also be written to
Exodus/XDA/XDR files. An illustration for mesh in exodus file format.


## Replicated and Distributed Mesh id=replicated-and-distributed-mesh

The core of the mesh capabilities are derived from [libMesh], which has two underlying
parallel mesh formats: "replicated" and "distributed".

The replicated mesh format is the default format for MOOSE and is the most appropriate format to
utilize for nearly all simulations. In parallel, the replicated format copies the complete mesh to
all processors allowing for efficient access to the geometry elements.

The distributed mesh format is useful when the mesh data structure dominates memory usage. Only the
pieces of the mesh "owned" by a processor are actually stored on the processor. If the mesh is too
large to read in on a single processor, it can be split prior to the simulation.

Both the "replicated" and "distributed" mesh formats are parallel with respect to the execution of
the finite element assembly and solve. In both types the solution data is distributed, which is
the portion of the simulation that usually dominates memory demands.

### Distributed Mesh Output Format (Nemesis)

When running a simulation with `DistributedMesh` it is generally desirable to avoid serializing
the mesh to the first rank for output. In the largest case this may cause your simulation to run
out of memory, in smaller cases, it may just cause unnecessary communication to serialize your
parallel data structure. The solution is to use "nemesis" output.

Nemesis creates separate Exodus files that are automatically read by Paraview and displayed as
if a normal Exodus mesh had been output. The output files have the following naming convention:

```
<filename>.e.<num_processors>.<rank>

# For example, on a 4 processor run, you can expect filenames like this:
out.e.4.0
out.e.4.1
out.e.4.2
out.e.4.3
```

## Mesh splitting

For large meshes, MOOSE provides the ability to pre-split a mesh for use in the "distributed"
format/mode. To split and use a mesh for distributed runs:

```
// For input files with a file-based mesh:
$ moose-app-opt -i your_input-file.i --split-mesh 500,1000,2000 // comma-separated list of split configurations
Splitting 500 ways...
    - writing 500 files per process...
Splitting 1000 ways...
    - writing 1000 files per process...
...

// MOOSE automatically selects the pre-split mesh configuration based on MPI processes
$ mpiexec -n 1000 moose-app-opt -i your_input-file.i --use-split
```

For more details see "[Mesh Splitting](/Mesh/splitting.md)".

## Displaced Mesh

Calculations can take place in either the initial mesh configuration or, when requested, the
"displaced" configuration. To enable displacements, provide a vector of displacement variable names
for each spatial dimension in the 'displacements' parameters within the Mesh block.


Once enabled, the any object that should operate on the displaced configuration should set the
"use_displaced_mesh" to true. For example, the following snippet enables the computation of a
[Postprocessor](/Postprocessors/index.md) with and without the displaced configuration.


## Mixed Dimension Meshes

MOOSE will function properly when running simulations on meshes containing mixed dimension elements
(e.g. 1D and 2D, 1D and 3D, etc.). Residual calculation, material evaluation, etc should all work properly.


## Unique IDs

There are two "first-class" id types for each mesh entity (elements or nodes): "id and unique_id". Both the id
and unique_id field are unique numbers for the current active set of mesh entities. Active entities are those
that are currently representing the domain but doesn't include "coarse parents" of some elements that may become
active during a coarsening step. The difference however is that unique_ids are never reused, but ids +might+ be.
Generally the id is "good-enough" for almost all use, but if you need guarantees that an element id is never
recycled (because it might be a key to an important map), you should use unique_id.

## Periodic Node Map

The MooseMesh object has a method for building a map (technically a multimap) of paired periodic nodes in the
simulation. This map provides a quick lookup of all paired nodes on a periodic boundary. in the 2D and 3D cases
each corner node will map to 2 or 3 other nodes (respectively).

## Extra integer IDs

Extra integer IDs for all the elements of a mesh can be useful for handling complicated material assignment, performing specific calculations on groups of elements, etc.
Often times, we do not want to use subdomain IDs for these tasks because otherwise too many subdomains could be needed, and in turn large penalty on run-time performance could be introduced.

MooseMesh[MooseMesh.md] has a parameter `extra_integers` to allow users to introduce more integer IDs for elements each identified with a name in the parameter.
When this parameter is specified, extra integers will be made available for all elements through `Assembly` in MOOSE objects such as kernels, aux kernels, materials, initial conditions, element user objects, etc.
To retrieve the integer on an element, one needs to simply call

```
getElementID(integer_name_parameter, comp),
```

within the initialization list of your constructor.
`integer_name_parameter` is the name of the parameter in type of `std::vector<ExtraElementIDName>` of this object listing all integer names.
`comp` is the index into the integer names if multiple are specified for `integer_name_parameter`.
It is noticed that the returned value of this function call must be in type of `const dof_id_type &`, which is used to refer the value set by MOOSE in `Assembly`.
The returned reference should be held in a class member variable for later use.
Based on this ID, one can proceed with any particular operations, for example, choosing a different set of data for evaluating material properties.

IDs can be assigned to the mesh elements with `MeshGenerators` in a similar way to assigning subdomain IDs.
We note that the element IDs are part of the mesh and will be initialized properly for restart/recover.

## Mesh meta data

Mesh generators can declare mesh meta data, which can be obtained later in Actions or in UserObjects.
Mesh meta data can only be declared in the constructors of mesh generators so that they can be restarted without re-running mesh generators.
Mesh meta data can be useful for setting up specific postprocessors, kernels, etc. that require certain geometry information.
Mesh meta data are not possible or extremely hard to be derived directly from libMesh mesh object.
A simple example of mesh meta data is the `num_elements_x` provided by [GeneratedMeshGenerator](GeneratedMeshGenerator.md), which can be used as an indicator for a mesh regular in x direction.

## Debugging in-MOOSE mesh generation id=troubleshooting

The MOOSE mesh generation [tutorial](tutorial04_meshing/index.md optional=true) is the most comprehensive resource on learning how to mesh within MOOSE. We summarize here
only a few techniques.

Mesh generation in MOOSE is a sequential tree-based process. Mesh generators are executed sorted by dependencies,
and the output of each generator may be fed to multiple other generators. To succeed in this process, you must decompose
the creation of the mesh into many individual steps. To debug this process, one can:

- use the `show_info(=true)` input parameter on each mesh generator. This will output numerous pieces of metadata about the mesh
  at each stage of the generation process. You can check there if all the subdomains that you expected at this stage
  are present in the mesh and if they are of the expected size, both in terms of number of elements but also bounding box.
- use the `output` input parameter on the mesh generator right before the problematic stage. This will output the mesh,
  by default using the [Exodus.md] format with the name `<mesh_generator_name>_in.e`, so you may visualize it
  before it gets acted upon by the next mesh generator(s).

For a narrow selection of mesh issues, listed in its documentation, the [MeshDiagnosticsGenerator.md] may be used to detect
unsupported features in meshes.

## Examining meshes id=examination

The results of finite element/volume simulations are highly dependent on the quality of the mesh(es) used.
It happens regularly that results are excellent and meeting all predictions using a regular Cartesian grid mesh,
but significantly deteriorate or do not converge on the real system mesh, often created outside MOOSE.

We point out in this section a few things to look for.
- Sidesets in MOOSE are oriented. If you place a Neumann/flux boundary condition on a sideset, the direction of
  the flux will depend on the orientation of the sideset.
- MOOSE generally does not support non-conformal meshes for regular kernels, except when they arise from online mesh refinement.
  When inspecting your mesh, you should not see any hanging nodes or surfaces not exactly touching. If you are using such
  a mesh, you +MUST+ use interface kernels, mortar or other advanced numerical treatments.
- Many physics will give better results with high element quality and smooth distributions of element volumes.
  You may examine the spatial distribution of these quantities using the [ElementQualityAux.md] and [VolumeAux.md]
  respectively.

## Coordinate Systems id=coordinate_systems

The following are the coordinate systems currently available in MOOSE:

- `XYZ`: 3D Cartesian.
- `RZ`: 2D axisymmetric coordinates.
- `RSPHERICAL`: 1D spherical coordinates with the origin at $(0,0,0)$.

Coordinate systems may be specified in the input file or within code.

### Specifying coordinate systems in the input file

In an input file, coordinate systems may be specified in the [Mesh](Mesh/index.md)
block.
First, [!param](/Mesh/GeneratedMesh/coord_type) is used to specify the coordinate
system type. If you would like to use multiple coordinate systems in your
application, you can supply multiple entries in this parameter. Then you must
specify [!param](/Mesh/GeneratedMesh/coord_block) to specify the corresponding
blocks to which each coordinate system applies.

If the `RZ` coordinate system is used, there are two options for how to specify
the coordinate axis(es) in an input file:

- Specify [!param](/Mesh/GeneratedMesh/rz_coord_axis) to choose a single `RZ`
  coordinate system, using the $\hat{x}$ or $\hat{y}$ direction and starting at $(0,0,0)$.
  If the former is used, then the axial coordinate is $x$, and the radial coordinate
  is $y$; if the latter is used, these are switched.
- Specify the following three parameters:

  - [!param](/Mesh/GeneratedMesh/rz_coord_blocks): The list of blocks using an
    `RZ` coordinate system (all must be specified).
  - [!param](/Mesh/GeneratedMesh/rz_coord_origins): The list of origin points
    for the axisymmetric axes corresponding to each block in [!param](/Mesh/GeneratedMesh/rz_coord_blocks).
  - [!param](/Mesh/GeneratedMesh/rz_coord_directions): The list of direction vectors
    for the axisymmetric axes corresponding to each block in [!param](/Mesh/GeneratedMesh/rz_coord_blocks).
    Note that these direction vectors need not be unit vectors, just nonzero vectors.

The second option has greater flexibility, as it allows the following, which the
first option does not:

- Multiple axisymmetric coordinate systems can be defined.
- Any point can be used for the origin of the coordinate system, not just $(0,0,0)$.
- Any direction can be used for the axisymmetric axis, not just the $\hat{x}$ or $\hat{y}$ direction.

Note that the [Transfers](Transfers/index.md) ability for the second option is
more limited

### Specifying coordinate systems within code

To specify coordinate systems within code, `MooseMesh::setCoordSystem(blocks, coord_sys)` is used,
where `blocks` and `coord_sys` have the same behavior as the [!param](/Mesh/GeneratedMesh/coord_block)
and [!param](/Mesh/GeneratedMesh/coord_type) parameters, respectively.

If the `RZ` coordinate system is used, there are two options for how to specify
the coordinate axis(es) within the code, just like in the input file:

- Call `MooseMesh::setAxisymmetricCoordAxis(rz_coord_axis)`, where
  `rz_coord_axis` is like [!param](/Mesh/GeneratedMesh/rz_coord_axis).
- Call `MooseMesh::setGeneralAxisymmetricCoordAxes(blocks, axes)`, where
  `blocks` is similar to [!param](/Mesh/GeneratedMesh/rz_coord_blocks)
  and `axes` pairs up the origins and directions, similar to combining the parameters
  [!param](/Mesh/GeneratedMesh/rz_coord_origins) and [!param](/Mesh/GeneratedMesh/rz_coord_directions).

# MeshDivisions

The `MeshDivisions` system is designed to be able to subdivide the mesh arbitrarily.
It associates a contiguously numbered single-indexing to regions of the mesh.
It can match many of the pre-existing ways of sub-dividing the mesh:

- using subdomains with [SubdomainsDivision.md]
- using extra element integers with [ExtraElementIntegerDivision.md]
- using a nearest-neighbor algorithm with [NearestPositionsDivision.md]

Some new simple ways to subdivide the mesh:

- using the values of a [Functor](Functors/index.md) with [FunctorBinnedValuesDivision.md]
- using a Cartesian grid with [CartesianGridDivision.md]
- using a cylindrical grid with [CylindricalGridDivision.md]
- using a spherical grid with [SphericalGridDivision.md]

Divisions can be combined through nesting, using a [NestedDivision.md]. The onus lies
on the user to have the nesting make sense.

An alternative option to distribute a division object would be to use a [Positions](syntax/Positions/index.md)
object within the definition of the object, for example the center of a [CylindricalGridDivision.md].
This has not been implemented yet. Please reach out to a MOOSE developer if this is of interest.

## Indexing the entire mesh or not

Each `MeshDivision` object can keep track of whether the entire mesh is indexed by the `MeshDivision`.
This can be expensive to check at any point, because the mesh could deform or because the bins
of the `MeshDivision` for the divisions change. Each `MeshDivision` object should either perform
a rigorous check before considering that the entire mesh is indexed, or make a conservative assumption
that the entire mesh is not indexed in the division.

## Postprocessing with MeshDivisions

For now, the mesh divisions can only be output using a [MeshDivisionAux.md].
We are planning to be able to compute averages, integrals, and various reductions
on mesh divisions, please stay tuned.

## Transferring with MeshDivisions

This feature is a work in progress.

Please let us know on [GitHub Discussions](https://github.com/idaholab/moose/discussions)
how you are using the `MeshDivisions` system so we can include your techniques on this page!

## Multi-dimensional indexing

This feature is not implemented. We always boil down nested binning (in X, Y and Z for example)
down to a single division index. If you cannot do so for your problem, we could consider introducing multi-dimensional
indexes. Please get in touch with a MOOSE developer to discuss this.

# MeshModifiers

The `MeshModifiers` system is designed to modify the [MooseMesh.md] during the
simulation.

Please let us know on [GitHub Discussions](https://github.com/idaholab/moose/discussions)
how you are using the `MeshModifiers` system so we can include your techniques on this page!




This is a placeholder for the actual `Modules` syntax for allowing modules syntax to
build correctly. The actual content explaining the `Modules` block is defined in
`modules/doc/content/syntax/Modules/index.md`.

# MultiApp System

## Overview

MOOSE was originally created to solve fully-coupled systems of [!ac](PDEs), but not all systems need to
be or are fully coupled:

- multiscale systems are generally loosely coupled between scales;
- systems with both fast and slow physics can be decoupled in time; and
- simulations involving input from external codes might be solved somewhat decoupled.

To MOOSE these situations look like loosely-coupled systems of fully-coupled equations. A `MultiApp`
allows you to simultaneously solve for individual physics systems.

Each sub-application (app) is considered independent. There is always a
"main" app that is doing the primary solve. The "main" app can then have any number of
`MultiApp` objects. Each `MultiApp` can represent many (hence Multi) "sub-applications" (sub-apps).
The sub-apps can be solving for completely different physics from the main application.  They can be
other MOOSE applications, or might represent external applications. A sub-app can, itself, have
`MultiApps`, leading to multi-level solves, as shown below.

       caption=Example multi-level MultiApp hierarchy.

## Input File Syntax

`MultiApp` objects are declared in the `[MultiApps]` block and require a "type" just like any other block.

The [!param](/MultiApps/TransientMultiApp/app_type) is the name of the `MooseApp` derived app that is going
to be executed. Generally, this is the name of the application being
executed, therefore if this parameter is omitted it will default as such. However this system
is designed for running another applications that are compiled or linked into the current app.

Sub-apps are created when a MultiApp is added by MOOSE.

A `MultiApp` can be executed at any point during the main solve by setting the
[!param](/MultiApps/TransientMultiApp/execute_on) parameter.
MultiApps at the same point are executed sequentially.
Before the execution, data on the main app are transferred to sub-apps of all the MultiApps and data on sub-apps are transferred back after the execution.
The execution order of all MultiApps at the same point is not determined.
The order is also irrelevant because no data transfers directly among MultiApps.
To enforce the ordering of execution, users can use multi-level MultiApps or set the MultiApps executed at different points.
If a `MultiApp` is set to be executed on timestep_begin or timestep_end, the formed loosely-coupled systems of fully-coupled
equations can be solved with [Fixed Point iterations](syntax/Executioner/index.md).


The input file(s) for the sub-app(s) are specified using the [!param](/MultiApps/TransientMultiApp/input_files)
parameter. If only one input file is provided, then this input file is used for all
sub-apps in this `MultiApp`.

The ability to specify multiple input files per application, e.g.,

```
subapp-opt -i input1.i input2.i
```

will not work correct in [!param](/MultiApps/TransientMultiApp/input_files), as
each input file in is interpreted as a different application.

## Positions id=multiapp-positions

Each sub-app has a "position" relative to the parent app, interpreted as the
translation vector to apply to the sub-app's coordinate system to put it in the correct
physical position in the parent app. For instance, suppose one is modeling a
fuel assembly with multiple fuel rods, and the parent app contains the mesh of
the assembly matrix, excluding the fuel rods. A `MultiApp` can be created where
each sub-app corresponds to a single fuel rod. A single input file may be created
for a fuel rod, where the rod starts at $(0,0,0)$, and the parent app can specify
that multiple instances of this sub-app be created, translated to the correct
physical positions in the assembly matrix. See [multiapps_pos] for an example
illustration.

       caption=Example of MultiApp object position.

The following are the options for specifying the position(s) of the sub-app(s):

- Use the [!param](/MultiApps/TransientMultiApp/positions) parameter to specify
  a list of position vectors directly. Each set of three values corresponds to
  one position vector. For example, `positions = '1 2 3 4 5 6'` creates two position vectors,
  $(1,2,3)$ and $(4,5,6)$. If multiple input files are specified via [!param](/MultiApps/TransientMultiApp/input_files),
  then the number of positions vectors must match the number of input files.
- Use the [!param](/MultiApps/TransientMultiApp/positions_file) parameter to specify
  a list of files containing position vectors. If a single input file is specified
  via [!param](/MultiApps/TransientMultiApp/input_files), then the positions files
  are treated as if their entries were all in a single positions file. If multiple input files
  are specified, then each positions file corresponds to an input file. Each positions
  file must be formatted with one positions vector per row. The entries in each
  row may be delimited by space, comma, or tab, so long as this is consistent
  throughout the file. For example, the following creates two positions vectors, $(1,2,3)$ and $(4,5,6)$:

  ```
  1 2 3
  4 5 6
  ```
- Use the [!param](/MultiApps/TransientMultiApp/positions_objects) parameter to specify
  a list of names of [Positions](Positions/index.md) objects. If a single input file is specified
  via [!param](/MultiApps/TransientMultiApp/input_files), then the `Positions` objects
  are treated as if they were merged into a single `Positions` object. If multiple input files
  are specified, then each `Positions` object corresponds to an input file.
- Omit all of these parameters, which defaults to the single position vector $(0,0,0)$.

## Mesh optimizations

The [!param](/MultiApps/TransientMultiApp/clone_parent_mesh) parameter allows for re-using the
main application mesh in the sub-app. This avoids repeating mesh creation operations. This does
not automatically transfer the mesh modifications performed by [Adaptivity](syntax/Adaptivity/index.md)
on either the main or sub-app, though it does transfer initial mesh modification work such as uniform
refinement.

When using the same mesh between two applications, the [MultiAppCopyTransfer.md] may be
utilized for more efficient transfers of field variables.

## Parallel Execution

The `MultiApp` system is designed for efficient parallel execution of hierarchical problems. The
main application utilizes all processors.  Within each `MultiApp`, all of the processors are split
among the sub-apps. If there are more sub-apps than processors, each processor will solve for
multiple sub-apps.  All sub-apps of a given `MultiApp` are run simultaneously in parallel. Multiple
`MultiApps` will be executed one after another.


## Dynamically Loading MultiApps

If building with dynamic libraries (the default) other applications can be loaded without adding them
to your Makefile and registering them. Simply set the proper `type` in your input file
(e.g. `AnimalApp`) and MOOSE will attempt to find the other library dynamically.

- The path (relative preferred) can be set in your input file using the parameter
  [!param](/MultiApps/TransientMultiApp/library_path); this path needs to point to the `lib` folder
  within an application directory.
- The `MOOSE_LIBRARY_PATH` may also be set to include paths for MOOSE to search.


Each application must be compiled separately since the main application Makefile does not have
knowledge of any sub-app application dependencies.

## Restart and Recover

General information about restart/recover can be found at [Restart/Recovery](restart_recover.md optional=True).
When running a multiapp simulation you do not need to enable checkpoint output in each sub-app input file.
The main app stores the restart data for all sub-apps in its file.
When restarting or recovering, the main app restores the restart data of all sub-apps into MultiApp's *backups*
(a data structure holding all the current state including solution vectors, stateful material properties,
post-processors, restartable quantities declared in objects and etc. of the sub-apps), which are used by
sub-apps to restart/recover the calculations in their initial setups.
The same backups are also used by multiapps for saving/restoring the current state during fixed point iterations.

A sub-app may choose to use a restart file instead of the main backup file by setting [!param](/Problem/FEProblem/force_restart) to true.

[!param](/Problem/FEProblem/force_restart) is experimental.




# NodalKernels System

Nodal kernels are used to solve equations that strictly belong on a node.
Some examples include:

- solving ordinary differential equations at every node. The following `NodalKernels` were implemented for that purpose:
  - [ConstantRate.md]
  - [TimeDerivativeNodalKernel.md]
  - [UserForcingFunctionNodalKernel.md]

- bounding a nodal variable's value at nodes. The following `NodalKernels` were implemented for that purpose:
  - [LowerBoundNodalKernel.md]
  - [UpperBoundNodalKernel.md]

- assigning mass to nodes instead of elements, as performed in the SolidMechanics module
  (see [NodalGravity](nodalkernels/NodalGravity.md optional=True) for example)


Even though we are not using an elemental quadrature in nodal kernels, [Variables](syntax/Variables/index.md) values
should still be accessed at the index `_qp` (=0) for consistency with other kernels' code.

Nodal kernels may be block and boundary restricted. Naturally for boundary restriction, the nodal kernel is only defined on the
nodes that are part of a boundary. For block restriction, all nodes that are part of elements in a block are considered.




# NodalNormals System

The `NodalNormals` system is used to define the outward-facing normal of a boundary at a node.
The system is mostly used through the [AddNodalNormalsAction.md].

The nodal normals are stored in auxiliary Lagrange variables named `nodal_normal_x`/`y`/`z`.
They may be of first or second order to accommodate both mesh orders.

The nodal normals on boundaries are computed in two steps:
- first a [NodalNormalsPreprocessor.md] populates the `nodal_normal_x`/`y`/`z` variables with the local quadrature weight times the gradient of the shape function
- then a [NodalNormalsEvaluator.md] normalizes each component so that the nodal normal has a norm of 1

On corners, the first step is replaced by obtaining the normal from the [Assembly](source/base/Assembly.md).




# Output System

The output system is designed to be just like any other system in MOOSE: modular and expandable.

## Short-cut Syntax

To enable output in an application it must contain an `[Outputs]` block.  The simplest method for
enabling output is to utilize the short-cut syntax as shown below, which enables
[outputs/Exodus.md] output for writing spatial data. A complete list of output types and the
associated short-cut syntax for the framework is included in [output-types].

[Outputs]
  exodus = true
[]

Developers may refer to [CommonOutputAction.md] for more information about implementing short-cut
syntax for new Output types.

## Block Syntax

To take full advantage of the output system, the use of sub-blocks is required. The block listed
below is nearly identical, with respect to the internal implementation, to [output-shortcut], including
the block name (i.e., the short-cut syntax builds this exact block). The one difference between
the short-cut and block syntax is the default output filename assigned

[Outputs]
  [exodus]
    type = Exodus
  []
[]

## Filenames

The resulting filenames produced by different syntax is important. The default naming scheme for
output files utilizes the input file name (e.g., input.i) with a suffix that differs depending on
how the output is defined:

- An "_out" suffix is used for `Outputs` created using the short-cut syntax.
- The sub-block syntax uses the actual sub-block name as the suffix.

For example, if the input file (input.i) contained the following `[Outputs]` block, two files would be created: input_out.e and input_other.e.

[Outputs]
  console = true
  exodus = true    # creates input_out.e
  [other]        # creates input_other.e
     type = Exodus
  []
[]

Note, the use of "file_base" anywhere in the `[Outputs]` block disables all default naming behavior.

## Available Output Types

[output-types] provides a list of the most common output types, including the short-cut syntax
as well as the type to be used when creating a sub-block. A complete list of all available
output objects is provided below.



## Multiple Output Blocks

It is possible to create multiple output objects for outputting:

- at specific time or timestep intervals,
- custom subsets of variables, and
- to various file types.
- Supports common parameters and sub-blocks.

[Outputs]
  vtk = true
  [console]
    type = Console
    perf_log = true
    max_rows = true
  []
  [exodus]
    type = Exodus
    execute_on = 'timestep_end'
  []
  [exodus_displaced]
    type = Exodus
    file_base = displaced
    use_displaced = true
    interval = 3
  []
[]

## Common Parameters

The Outputs block supports common parameters. For example, "execute_on" may be specified outside of
individual sub-blocks, indicating that all sub-blocks should output the initial condition, for
example.

If within a sub-block the parameter is given a different value, the sub-block parameter takes
precedence.

The input file snippet below demonstrate the usage of a common values as well as the use of
multiple output blocks.

`Console`-based outputs have special inheritance of common parameters: the `execute_on` parameter,
as detailed below, does not get inherited.

[Outputs]
  execute_on = 'timestep_end' # disable the output of initial condition
  interval = 2                # only output every 2 timesteps
  vtk = true                  # output VTK file
  print_perf_log = true       # enable the performance log
  [initial]
    type = Exodus
    execute_on = 'initial'    # this ExodusII file will contain ONLY the initial condition
  []
  [displaced]
    type = Exodus
    use_displaced = true
    interval = 3              # this ExodusII will only output every third time step
  []
[]

Developers may refer to [CommonOutputAction.md] for more information about implementing new
common output parameters.

## Controlling output frequency

Several parameters are available common to all output objects to control the frequency with which
output occurs.

- `interval = N` will cause output objects to output only every _Nth_ simulation step
- if `start_time` and/or `end_time` are specified, outputs will only happen after the given start time and/or before the given end time
- `sync_times = 't1 t2 t3 ... tN` will cause MOOSE to hit each listed simulation time _t1 .. tN_ exactly. With `sync_only = true` outputs will _only_ happen at the specified sync times.
- `minimum_time_interval = dt` will suppress any output if the previous output happened at an earlier time that is more recent than _dt_ time units ago (specifically this means that outputs during linear iterations are not suppressed, as they are happening at the _same_ simulation time, and output from failed, cut steps do not lead to output suppression in repeated steps as they happened in the future)

## Outputs and execute_on

Outputs utilize the "execute_on" parameter like other systems in MOOSE, by default:

- All objects have `execute_on = 'initial timestep_end'`, with `Console` objects being the exception.
- `Console` objects append `'initial timestep_begin linear nonlinear failed'` to the "execute_on"
  settings at the common level.

A list of available "execute_on" flags for Output objects is provided in [output-execute-on] and
a convenience parameter, "additional_execute_on", allows appending flags to the existing
"execute_on" flags.

When debugging output, use the `--show-outputs` flag when executing your application. This will add a
section near the top of the simulation that shows the settings being used for each output object.

- The toggles shown below provide additional operate by appending to the "execute_on" flags.
- Currently, the following output execution times are available:

| Text Flag | Description |
| :- | :- |
| "none"           | disables the output |
| "initial"        | executes the output on the initial condition (on by default) |
| "linear"         | executes the output on each linear iteration |
| "nonlinear"      | executes the output on each non-linear iteration |
| "timestep_end"   | calls the output method at the end of the timestep (on by default) |
| "timestep_begin" | executes the output method at the beginning of the timestep |
| "final"          | calls the output method on the final timestep |
| "failed"         | executes the output method when the solution fails |

As detailed in the [#custom-output] section, there are two types of outputs
classes: `BasicOutput` and `AdvancedOutput`. Advanced outputs have additional control beyond
`execute_on`, as detailed in the table below.

| Input Parameter | Method Controlled |
| :- | :- |
| execute_postprocessors_on | `outputPostprocessors` |
| execute_vector_postprocessors_on | `outputVectorPostprocessors` |
| execute_elemental_on | `outputElementalVariables` |
| execute_nodal_on | `outputNodalVariables` |
| execute_scalar_on | `outputScalarVariables` |
| execute_system_information_on | `outputSystemInformation` |
| execute_input_on | `outputInput` |

Each of the output controls accept the same output execution flags that `execute_on` utilizes. In
`AdvancedOutput` objects, the `execute_on` settings are used to set the defaults for each of the
output type controls. For example, setting `execute_on = 'initial timestep_end'` causes all of the
output types (e.g., postprocessors, scalars, etc.) to execute on each timestep and the initial
condition.

## Mesh Displacements and Higher Order Meshes

The displaced mesh may be output by setting 'use_displaced = true' within your output sub-blocks. To
output both the original and displaced mesh an additional output block is required.

In general, it is not necessary to output the displace mesh, since most visualization tools
automatically apply displacements. Because of this, writing the displaced mesh can result in
visualizations that apply displacements multiple times.

If a simulation is using a higher order mesh, oversampling may be required to provide an accurate
representation of the finite element solution. Visualization tools generally perform linear
interpolation between data, regardless of the mesh order. Oversampling, which is controlled by
setting the "refinements" parameter, will evaluate the finite element solution on a uniformly refined
mesh during output to provide a improved view of the existing solution.

[Outputs]
  console = true
  exodus = true
  [oversample]
     type = Exodus
     refinements = 2
     use_displaced = true
  []
[]

## In-Block Output Control

For certain objects it is possible to control output within the block itself, these objects include:
Postprocessors, VectorPostprocessors, Indicators, Markers, Variables, and AuxVariables. For example,
consider the following input file that has three output objects defined and a single postprocessor as well.

```text
[Postprocessors]
  [pp]
    type = EmptyPostprocessor
    outputs = 'csv'
  []
[]

[Outputs]
  exodus = true
  csv = true
  [vtk]
    type = VTK
    interval = 2
  []
[]
```

The outputs that should include the postprocessor value may be listed in the "outputs" parameter.

The "outputs" parameter limits the defined postprocessor to output only to the `csv` output
object. This highlights the need to understand the naming convention utilized by the short-cut
syntax. It is also possible to remove the postprocessor from all outputs by specifying
"outputs = none".

## Non-linear/Linear Residual Output

Any object inheriting from PetscOutput has the ability to output data on non-linear and/or linear
iterations. To enable this add "nonlinear" and/or "linear" to the "execute_on" input parameter.

```text
[Outputs]
  [exodus]
    type = Exodus
    execute_on = 'timestep_end linear nonlinear'
  []
[]
```

When outputting nonlinear/linear iterations the time is changes from the actual simulation time by
creating pseudo time steps.  For example, if the `[Outputs]` block above was associated with a
simulation that was taking a time step of 0.1 the resulting output times would use the following
convention:

| Output Time | Description |
| :- | :- |
| 0.2        | Converged solve for time = 0.2 |
| 0.2001     | First non-linear iteration for time = 0.3 |
| 0.2001001  | First linear iteration for the first non-linear iteration |
| 0.2001002  | Second linear iteration for the first non-linear iteration |
| 0.2002     | Second non-linear iteration for time = 0.3 |
| 0.2002001  | First linear iteration for the second non-linear iteration |
| 0.2002002  | Second linear iteration for the second non-linear iteration |
| 0.3        | Converged solve for time = 0.3 |

## Creating Custom Output Object id=custom-output

When creating a new output object, the new object must inherit from one of two templated base
classes: `BasicOutput` or `AdvancedOutput`.

For either base class, the template parameter should be one of the following four output classes:

| Base Class | Description |
| :- | :- |
| `Output` | the most general output base class, this should be used for simple output classes that require very little control over execution, see [`MaterialPropertyDebugOutput`](http://www.mooseframework.com/docs/doxygen/moose/classMaterialPropertyDebugOutput.html) |
| `PetscOutput` | provides the ability to execute output calls on linear and nonlinear residual calculations. |
| `FileOutput` | adds the basic functions and parameters need to write to a file. |
| `OversampleOutput` | adds the ability to utilize an oversampled mesh for outputting. |

Note, the four classes listed above inherit from each other, so `FileOutput` is a `PetscOutput`, see
the inheritance diagram for a visual representation:
[`Output`](http://www.mooseframework.com/docs/doxygen/moose/classOutput.html).

## Creating a BasicOutput

Basic output objects are designed for simple output cases that perform a single output task and do
not require control over individual types of output.

- When creating a basic output object, the user must override a single virtual method: `output(const
  OutputExecFlagType & type)`.
- This method should perform all the necessary commands to perform the output.
- The `OutputExecFlagType` specifies what execute flag the output is currently being called
  with(e.g., "initial"). This type is a proper Enum and the possible values are listed in
  `include/base/Moose.h`.

## Creating an AdvancedOutput id=advanced-output

Advanced output objects provide additional control over various output types (e.g., postprocessors).
When creating an advanced output object a call to the static method `enableOutputTypes` must exist in
the new objects `validParams` method that indicates which types of outputs the new object will be
responsible for outputting. For example, the Exodus output `validParams` method includes:

```cpp
InputParameters params = AdvancedOutput<OversampleOutput>::validParams();
params += AdvancedOutput<OversampleOutput>::enableOutputTypes("nodal elemental scalar
                                                              postprocessor input");
```

Each of the keywords listed in this method enable a call to the associated output method, as detailed
in the following table.

| Enable Keyword         | Associated Method |
| :-                     | :-                |
| "nodal"                | `outputNodalVariables` |
| "elemental"            | `outputElementalVariables` |
| "scalar"               | `outputScalarVariables` |
| "postprocessor"        | `outputPostprocessors` |
| "vector_postprocessor" | `outputVectorPostprocessors` |
| "input"                | `outputInput` |
| "system_information"   | `outputSystemInformation` |

These methods are the virtual methods that must be overloaded in the custom output object. For
example, if "nodal" output in enabled the `outputNodalVariables` should be overloaded. Each of these
methods includes the `OutputExecFlagType` as an input variable to the method.

# Physics system

The `Physics` system is meant to standardize the process of adding an equation and its discretization
to a simulation. It is based on the [Action system](source/actions/Action.md), with additional APIs
defined to support the definition of an equation.

## Interaction with Components

The interaction with Components is one of the main goals of the Physics system. Stay tuned for future developments.

## Generating a traditional input from a Physics input

By substituting the traditional [Problem](syntax/Problem/index.md) in your simulation for the [DumpObjectsProblem.md],
you can generate the equivalent input using the traditional Kernel/BCs/etc syntax to an input using `Physics`.
This is useful for debugging purposes.

This is not currently possible for thermal hydraulics inputs which use a specific problem.

## Implementing your own Physics

If you have *not* created the kernels, boundary conditions, and so on, the `Physics` system is not a good place
to start. You must start with a working implementation of your equations before attempting to create a `Physics` object.

If you do have a working set of kernels, boundary conditions, and other MOOSE objects, that let you solve an equation in MOOSE,
you should consider the following before implementing a `Physics`:

- is user-friendliness a priority for the expansion of my work?
- is the current workflow unsatisfactory in that regard?
- would creating objects programmatically reduce the potential for user-error while allowing sufficient flexibility?

If the answer is yes to all three, then you may start implementing a `Physics` object for your equation.
The simple concepts behind the simulation setup in a `Physics` is that the `add<various MOOSE object>` routines
are all called on the `Physics` and they are all called at the same time in the setup as with a regular input file.

So for example, to make a `DiffusionPhysics` create a finite element diffusion kernel, one can override `addFEKernels` like this:

```
void
DiffusionPhysics::addFEKernels()
{
  {
    const std::string kernel_type = "ADDiffusion";
    InputParameters params = getFactory().getValidParams(kernel_type);
    params.set<NonlinearVariableName>("variable") = _temperature_name;  // we saved the name of the variable as a class attribute
    getProblem().addKernel(kernel_type, name() + "_diffusion", params);
  }
}
```

Notice how we use the `PhysicsBase::getFactory()` routine to get access to the `Factory` that will get the parameters we
need to fill, and the `PhysicsBase::getProblem()` to get access to the `Problem` which stores the objects created.
We want the `Physics` to be able to be created with various types of `Problem` classes.

If you already have an `Action` defined for your equations, converting it to a `Physics` should be fairly straightforward. The principal advantages of doing so are:

- benefit from new APIs implemented in the `Physics` system
- a standardized definition of the equation, which will help others maintain your `Action`
- future ability to leverage the `Components` system to define a complex system

### Advice on implementation

#### Add a lot of checks

Please add as much parameter checking as you can. The `PhysicsBase` class inherits the `InputParameterCheckUtils` that implements
routines like the ones below that let you check that the user inputs to your physics are correct.


Using this utility, consider checking that:

- the size of vector, vector of vectors, `MultiMooseEnum` and map parameters are consistent
- if a parameter is passed it must be used, for example if one parameter conditions the use of other parameters
- the block restrictions are consistent between the `Physics` and objects it defines

#### Separate the definition of the equation from its discretization

You may consider creating a `PhysicsBase` class to hold the parameters that are shared between all the
implementations of the equations with each discretization. This will greatly facilitate switching between discretizations
for users. It will also maximize code re-use in the definition and retrieval of parameters, and in the attributes of the
various discretized `Physics` classes.

Physics and spatial discretizations are as separated as we could make them, but they are still very much intertwined. So
when you are adding a parameter you need to think about:

- is this more tied to the strong form of the equation? If so then it likely belongs in a `XYZPhysicsBase` base class
- is this more tied to the discretization of the equation? If so then it likely belong in the derived, user-instantiated,
  `XYZPhysics(CG/DG/HDG/FV/LinearFV)` class.

#### Rules for implementation of Physics with regards to restarting variables or using initial conditions

It is often convenient to define initial conditions in the `Physics`, and also to be able to
restart the variables defined by the `Physics` automatically with minimal user effort. User-defined initial conditions
are convenient to keep the input syntax compact, and default initial conditions are useful to avoid
non-physical initial states. However, all these objectives conflict when the user defines parameters for initialization in
a restarted simulation. To make things simple, developers of `Physics` should follow these rules, which we developed based on user
feedback.

- if the `initialize_variables_from_mesh_file` parameter is set to true, then:
  - skip adding initial conditions
  - error if an initial condition parameter is passed by the user to the `Physics`
- if the `Physics` is set to use (define kernels for) variables that are defined outside the `Physics`, then:
  - skip adding initial conditions
  - error if an initial condition parameter is passed by the user to the `Physics`
- else, if the user specifies initial conditions for variables in the `Physics`
  - always obey these parameters and add the initial conditions, even if the simulation is restarting
  - as a sanity check, the [FEProblemBase.md] will error during restarts, unless [!param](/Problem/FEProblem/allow_initial_conditions_with_restart) is set to true
- else, if the user does not specify initial conditions in the `Physics`, but the `Physics` does define default values for the initial conditions
  - if the simulation is restarting (from [Checkpoint.md] notably), skip adding the default initial conditions
  - (redundant due to the first rule) if the `initialize_variables_from_mesh_file` parameter is set to true, skip adding the default initial conditions
  - (redundant due to the second rule) if the `Physics` is set to use (define kernels for) variables that are defined outside the `Physics`, skip adding the default initial conditions

For `initialize_variables_from_mesh_file` to work correctly, you must use the `saveNonlinearVariable()` and `saveAuxiliaryVariable()` `Physics` routines
in the constructor of your `Physics` on any variable that you desire to be restarted.

# Positions

Positions are used to keep track of the locations of objects during MOOSE-based simulations.

By default, they are updated when the mesh changes and on every execution. The execution schedule
is by default very limited, but may be expanded using the `execute_on` parameter of every `Positions`
object.

`Positions` support initialization from another `Positions` object. The name of the initialization
object should be specified using the [!param](/Positions/InputPositions/initial_positions) parameter.

## Combining positions

`Positions` from multiple sources may be concatenated using the [ReporterPositions.md].

## Example uses

`Positions` may be used to spawn subapps of a `MultiApp` at various locations, using the
[!param](/MultiApps/FullSolveMultiApp/positions_objects) parameter. The positions
of the subapps will be updated with the `Positions`.

The number of `Positions` should currently stay constant during the simulation.




# Postprocessor System

A postprocessor is an object that computes a single scalar (`Real`) value,
such as a value sampled from the solution at a point in the domain, or an integral/average
over some subdomain or boundary. This value may be used purely for output purposes,
or it may be retrieved by other systems via the `getPostprocessorValue` method,
which is available in most MOOSE objects. Furthermore, postprocessors are also
[functors](Functors/index.md), which allows them to be retrieved into various
objects via the `getFunctor<Real>` method.

MOOSE includes a large number of postprocessors within the framework, the complete list is
provided in [Available Objects list](#available-objects) section.

The [Reporters/index.md] is a newer, more flexible system for computing aggregate values. It is recommended
that new objects for aggregate calculations use the Reporter system.

## Example Input File

The following input file snippet demonstrates the use of the
[ElementExtremeValue](ElementExtremeValue.md) to compute the minimum and maximum of the solution
variable "u".


This snippet is a part of a test that may be executed using the MOOSE test application as follows.

```bash
cd ~/projects/moose/test
make -j8
cd tests/postprocessors/element_extreme_value
~/projects/moose/test/moose_test-opt -i element_extreme_value.i
```

The data from this calculation is reported in the terminal output by default and if [Exodus.md]
output is enabled the values will automatically be included in the output file. It is also possible
to export the data to a comma separated value (csv) file by enabling the [CSV.md]
object within the [Outputs](syntax/Outputs/index.md) block.

```bash
Postprocessor Values:
+----------------+----------------+----------------+
| time           | max            | min            |
+----------------+----------------+----------------+
|   0.000000e+00 |   0.000000e+00 |   0.000000e+00 |
|   1.000000e+00 |   9.788675e-01 |   2.113249e-02 |
+----------------+----------------+----------------+
```

## Coupling Example Code

The values computed within a Postprocessor object may be used within other objects that inherit
from the [PostprocessorInterface](interfaces/PostprocessorInterface.md), which is nearly every
system within MOOSE. For example, the [PostprocessorNeumannBC.md] object allows for a
Neumann boundary condition to be set to a value computed from a postprocessor; this object will
be used as example to demonstrate how coupling is performed.

To understand how the coupling is coded it is beneficial to first see how the coupling is defined
via the input file. The following input file snippet shows that a [PointValue.md] postprocessor
is created and named "right_pp" and the [PostprocessorNeumannBC.md] uses this value to set the
boundary condition.


This first step of coding this type of coupling begins by adding the necessary input file syntax to
the object that requires a postprocessor value, PostprocessorNeumannBC in this example. In all MOOSE
objects input file syntax is governed by the validParams function of an object. To add the ability
to couple a postprocessor, simply add a new parameter using the `PostprocessorName` type, as shown
below. Notice, that the add parameters call includes a default value that makes the use of the
postprocessor optional.


The actual postprocessor value must be assigned to a member variable of the class, thus in the header
a member variable must be created, which should always be a constant reference to a
`PostprocessorValue` type. Since this is a reference it must be initialized, this occurs in the
source file by calling the `getPostprocessorValue` method and providing the name used in the
validParams function. The following snippets show declaration of the reference in the header and
the initialization of this reference in the source file.  The `_value` member variable is then
available for use anywhere inside the object, for the case of the boundary condition it is utilized
in the computation of the residual.



### Coupling to other values

Just as Postprocessor values can be used in other objects, Postprocessors themselves can couple to
Functions and Scalar Variables. See the following example that couples a scalar variable into a
Postprocessor:


## Creating a `Postprocessor` Object

In general, every Postprocessor object has two methods that must be defined "execute" and
"getValue".

First, consider the execute method. This method is called by MOOSE at different time
depending on the type of postprocessor object. Therefore, when creating a Postprocessor object
the new object should inherit from one of the following C++ classes:

- +GeneralPostprocessor+: "execute" is called once on each execution flag.
- +NodalPostprocessor+: "execute" is called for each +node+ within the mesh on each execution flag.
- +ElementalPostprocessor+: "execute" is called for each +element+ within the mesh on each execution
   flag.
- +InternalSidePostprocessor+: "execute" is called for each +side+, that is not on a boundary,
   within the mesh on each execution flag.
- +SidePostprocessor+: "execute" is called for each +side+, that is on a boundary, within the mesh
   on each execution flag.

The use of execution flags is discussed in the [Execute On](#execute-on) section.

The getValue method is responsible for returning the value of the postprocessor object, this
value is what is used by all objects that are coupled to the postprocessor. In some cases the
necessary communication is performed within this method, but in general this following is preferred.

### Parallel Considerations

When creating a postprocessor it is often necessary to perform some parallel communication
to ensure that the value being computed is correct across processes and threads. Three additional
methods exists for making this process as simple as possible.

- `initialize`: This is called prior to the execution of the postprocessor and should be used
   to setup the object to be in a known state. It is important to point out that execution
   in this context includes all calls to the execute method. For example, for a `NodalPostprocessor`
   object the initialize method is called and then the execute method is called for all nodes.
- `finalize`: This is called after the execution of the postprocessor and is intended to perform
   communication to prepare the object for the call to the getValue method.
- `threadJoin`: This is called after the execution of the postprocessor and is intended to perform
   aggregation for shared memory parallelism.

To understand the use of these methods the [AverageNodalVariableValue.md] postprocessor shall be
used as an example. As the name suggests this postprocessor computes the average of the value
of a variable at the nodes. To perform this calculation the variable values from each node
are summed as is the number of values within the execute method. Then the getValue method
returns the average by returning the sum divided by the count. The following snippet shows the
these two methods: the `_u[_qp]` is the value of the variable at the current node that comes
from a shared base class and  `_sum` and `_n` are a member variables defined within class for
performing the calculation.


In parallel, the calls to the execute method occur on each process or thread on a subset of the
domain, in this case nodes. Therefore, the computed values must be combined to get the actual
summations required to compute the average value. The first step is to setup the state
of this calculation within the initialize method, which in this example sets the
`_sum` and `_n` member variables to zero.


After the aforementioned execute method is called for each node the computed values for `_sum` and
`_n` must be aggregated from across processes to the root processes. For this problem a gather
operation is required to collect the values computed on all processes to the root process. This is
accomplished via the `gatherSum` method.


Of course, the type of communication necessary depends on the calculation being performed. The
[UserObject.md] base class includes helper methods for common parallel communications functions.

The initialize and finalize methods are utilized to aggregate for message passing (MPI) based
parallelism. For shared memory parallelism the threadJoin method is used. This method is called,
like finalize, after execution is complete and includes a single argument. This argument is a
reference to a UserObject, which is a base class of Postprocessor objects. The purpose of this
method is to enable the aggregation for the Postprocessor objects that were executed on other
threads to the object on the root thread. For the AverageNodalVariableValue postprocessor the
values for `_sum` and `_n` on the root process object are updated to include the these same values
from the other threads.


## Execute On... id=execute-on

Postprocessor objects inherit from the [SetupInterface.md] that allows the objects to execute and
varying and multiple times during a simulation, such as during initialization and at the end of
each time step. Refer to the [SetupInterface.md] for additional information.

## Using Old and Older values

MOOSE maintains previously computed values in the postprocessor system for using lagged information
in a computation. Both the previous time step's value and the value computed two steps back may
be retrieved. One reason you might use older values is to break cyclic dependencies. MOOSE does
not consider a dependence on an old value when considering the order of evaluation among objects
with dependencies.




# Preconditioning System

## Overview

See [Steady.md] for more details on how preconditioning is used in solving nonlinear systems in MOOSE.
The `Preconditioning` block allows you to define which type of preconditioning matrix to build and what process to apply.
You can define multiple blocks with different names, allowing you to quickly switch out preconditioning options.
Within the sub-blocks you can also provide other options specific to that type of preconditioning matrix.
You can also override PETSc options here.
Only one block can be active at a time.

## Default Preconditioning Matrix

Consider the fully coupled system of equations:

\begin{aligned}
\nabla \cdot k(s,T) \nabla T  &= 0 \\
\nabla \cdot D(s,T) \nabla s  &= 0 ,
\end{aligned},

the fully coupled Jacobian is then approximated using a block-diagonal approach:

\boldsymbol{R}'(s,T) =
 \begin{bmatrix}
   (\boldsymbol{R}_T)_T & (\boldsymbol{R}_T)_s
   \\
   (\boldsymbol{R}_s)_T & (\boldsymbol{R}_s)_s
 \end{bmatrix}
 \approx
 \begin{bmatrix}
   (\boldsymbol{R}_T)_T & \boldsymbol{0}
   \\
   \boldsymbol{0}       & (\boldsymbol{R}_s)_s
 \end{bmatrix} .

Thus, for this example, the default preconditioning matrix is defined as:

\boldsymbol{M} \equiv
    \begin{bmatrix}
      (k(s,T) \nabla \phi_j, \nabla \psi_i) & \boldsymbol{0} \\
      \boldsymbol{0} & (D(s,T) \nabla \phi_j, \nabla\psi_i)
    \end{bmatrix} \approx \boldsymbol{R}'(s,T) .

## Example Input File Syntax

A single preconditioner may be specified as below:

[Preconditioning]
  [my_prec]
    type = SMP
    # SMP Options Go Here!
    # Override PETSc Options Here!
  []
[]

Nested preconditioners may be specified as below, for the [FieldSplitPreconditioner.md]
for example:





# Problem system overview

The Problem class is one of the core extension points in MOOSE. Problems
are designed to hold the `EquationSystems` objects (from libMesh) that
house the numerical systems we are ultimately solving for our computing.

Fortunately when you are first getting started with MOOSE you normally
don't have to worry or do anything special with the Problem object. MOOSE
automatically constructs a suitable Problem for your simulation type
taking into account the other types of objects present in the input file.
Most simulations use the `FEProblem` class, which contains a single
`NonlinearSystem` and single `AuxiliarySystem` or a single `MooseEigenSystem`
and single `AuxiliarySystem`. The `NonlinearSystem` or `MooseEigenSystem`
contains the matrix and vectors used for solving the equations implemented
through a combination of other objects in your simulations (`Kernels`, `BCs`,
etc.). The `AuxiliarySystem` houses the solution vectors use to hold
computed solutions or values.

As your application grows in complexity, you may find it useful or
necessary to create your own problems to extend default behavior provided
by the core MOOSE framework. Common examples include, specialized
convergence tests, etc.

# Automatic Problem Creation

The automatic problem creation is handled for you by MOOSE. In a normal
input file that does not contain a special `[Problem]` block, MOOSE
will create a suitable Problem for you. If however, you need to change
specific system related parameters you may find yourself adding a
`[Problem]` block with name/value pairs. Different types of Problems
may be instantiated by using the `/Problem/type` whose default value is
`FEProblem`.

# Problem System




# ProjectedStatefulMaterialStorage System

The `ProjectedStatefulMaterialStorage` Action sets up the required objects to
store old material state projected onto finite element basis functions. See the
documentation for
[ProjectedStatefulMaterialStorageAction](ProjectedStatefulMaterialStorageAction.md)
for details.




# Reporter System

The Reporter system may be considered a generalization of the [Postprocessor](Postprocessors/index.md)
and [VectorPostprocessor](VectorPostprocessors/index.md) systems. Each Reporter
object may declare any number of values with any types. By contrast, post-processors
each declare a single, scalar, `Real` value, and while vector post-processors declare
any number of values, they must all be of type `std::vector<Real>`. Reporters can declare
both scalar and vector data of any type, including complex data and arbitrary
classes/structs. The only requirement on the data type is that the types must
have associated `dataLoad` and `dataStore` specializations (see [DataIO.md]).

The reporter system uses a producer/consumer relationship: reporter objects
"produce" data values, which then may be "consumed" by other objects.

## Producing Reporter Data

As noted above, Reporter objects declare any number of values of any type.
Note that these values are automatically registered as
[restartable](restart_recover.md optional=True). For complex types, data serialization routines
might be needed; see [DataIO.md] for more information.

In the Reporter header file, Reporter values are declared as non-const reference
members of the desired types, for example:


These references are initialized using the `declareValue` and `declareValueByName` methods.
Note that it is possible to indicate how the value is to be computed, with respect to parallelism, by setting
the calculation mode; see [#reporter-modes] for more information. The `declareValueByName` method
uses the supplied string directly as the value name, while the `declareValue` method
gets the value name from the supplied `ReporterValueName` parameter declared in
`validParams`. For example, in `validParams`,


Then the Reporter data can be declared using `declareValue`:


Note that in this example, an initial value is supplied for the data.

The calculation of the value(s) occurs by overriding the `execute` method and updating the values:


## Consuming Reporter Data

Any object that inherits from the `ReporterInterface` may consume a value produced by a Reporter.
Values are retrieved in a similar fashion as declared, but use a constant reference. For example,
values to be consumed should create a reference in the class definition:


In the initialization list, the `getReporterValue` or `getReporterValueByName`
method is used to initialize the reference:


Similarly to `declareValue` and `declareValueByName`, `getReporterValue` uses
the provided string for the value name, whereas `getReporterValueByName` gets
the value name from the parameter named by the provided string.
In the example above, the following appears in `validParams`:


The get methods accept a `ReporterName` object, which is simply the combination of the name
of the producing Reporter object and the name of the reporter value.
In the input file, the ReporterName is provided as follows, where "a" is the name of the
Reporter object in the `[Reporters]` block of the input file that is producing data
with the name "int", which is the name given to the data within the
`declareValue`/`declareValueByName` method of that object:


## Outputting Reporter Data id=reporter-output

Reporter values may be output in two formats: [!ac](CSV) and [!ac](JSON). [!ac](CSV) output
is limited to Reporter values with a type of `Real` or `std::vector<Real>`. [!ac](JSON) output will
work for any type that has a `to_json` function; see [JSONOutput.md] for more details.

## Reporter Context and Modes id=reporter-modes

Reporter values use a context system for performing parallel operations automatically. The default
context allows Reporter values to be produced and consumed in various modes. Depending on the mode
produced/consumed, parallel operations will be performed automatically. The following modes exist for
the default context:

- +REPORTER_MODE_ROOT+: Values exist only on the root processor.
- +REPORTER_MODE_REPLICATED+: Values exist and are identical on all processors.
- +REPORTER_MODE_DISTRIBUTED+: Values exist and are different across processors.

Values can be produced or consumed in any of the prescribed modes. When consumed, the mode of
production is checked against the mode of consumption. [producer-consumer-modes] details the
actions taken by the various possible modes of production and consumption for a Reporter value.

               on the modes of production and consumption. The prefix `REPORTER_MODE_` is omitted
               for clarity.
       id=producer-consumer-modes
| Producer Mode | Consumer Mode | Operation |
| :- | :- | :- |
| ROOT | ROOT | Do nothing |
| REPLICATED | ROOT | Do nothing |
| REPLICATED | REPLICATED | Do nothing |
| DISTRIBUTED | DISTRIBUTED | Do nothing |
| ROOT | REPLICATED | MPI Broadcast |
| ROOT | DISTRIBUTED | Error |
| REPLICATED | DISTRIBUTED | Error |
| DISTRIBUTED | ROOT | Error |
| DISTRIBUTED | REPLICATED | Error |

The `declareValue` and `declareValueByName` methods allow for non-default context to be defined. For
example, the following line declares a Reporter value to use the gather context object. A list of
available contexts follows the code snippet.

                                           replace=["\n", "", " ", "", ",", ", "]


`ReporterBroadcastContext`\\
Automatically performs an MPI broadcast of a specified value on the root processor to all processors.

`ReporterScatterContext`\\
Automatically performs an MPI scatter of a vector of data on the root processor to all processors.

`ReporterGatherContext`\\
Automatically performs an MPI gather to a vector of data on the root processor from all processors.

## Reporter Debug Output

The [ReporterDebugOutput.md] output can be added to output to screen all of the Reporter values that were declared and requested, along with their types, producers, contexts, consumers, and consumer modes. This debug output can also be enabled with the `Debug/show_reporters` parameter.




# Samplers System

The sampler system within MOOSE provides an API for creating samples of distributions, primarily for
use with the Stochastic Tools module.


# ScalarKernels System

Scalar kernels are used to define systems of ordinary differential equations (ODEs),
which lack spatial derivatives. These are used in initial value problems, with
time as the independent variable:
\begin{equation}
\begin{split}
  &\frac{d u}{d t} = f(u, t) \qquad t \geq 0\\
  &u(0) = u_0\\
\end{split}
\end{equation}
where $u(t)$ is the dependent variable, $f(u, t)$ is the steady-state residual
function, and $u_0$ is the initial value.

Similar to the [Kernel](syntax/Kernels/index.md) class, in a `ScalarKernel` subclass the
`computeResidual()` function +must+ be overridden.  This is where you implement
your ODE weak form terms.  For non-AD objects the following member function can
optionally be overridden:

- `computeJacobian()`
- `computeOffDiagJacobianScalar()`

## Coupling with Spatial Variables id=couple-spatial

For systems of coupled partial differential equations (PDEs) and ODEs, typically
integration over domains and manifolds are needed within the coupling terms of the
weak form. Since the `ScalarKernel` class does not provide for integration over
elements or faces, there are two options for performing needed integration using
other object classes:

1. Compute integrals for residual and diagonal Jacobian entries of the scalar
   variable within a `UserObject` and connect that value into the `ScalarKernel` object.
   Cross Jacobian terms that couple the scalar and spatial variables need to be handled
   by overridden assembly routines that access upper and lower triangular blocks of the
   Jacobian concurrently. An example of this approach is provided in the
   [AverageValueConstraint.md] and the [ScalarLagrangeMultiplier.md] objects, respectively.

2. Compute all integrals for the residual and Jacobian entries for the spatial and
   scalar variables using scalar augmentation classes that derive from the
   respective spatial variable residual object class. This approach is described below.

The principal purpose of these scalar augmentation classes is to add standard
quadrature loops and assembly routines to handle the contributions from a single added
scalar variable to that object, including the entire row of the Jacobian. 
This scalar variable is referred to as the "focus" scalar variable of that object.
Lists of interfaces for
the quadrature point routines are given in the links below. This system is currently being
developed and will extend to the other residual objects.

| Object | Scalar Augmentation Class | Example Derived Class |
| :- | :- | :- |
| Kernel\\ +ADKernel+ | [`KernelScalarBase`](source/kernels/KernelScalarBase.md) | [`ScalarLMKernel`](source/kernels/ScalarLMKernel.md) |
| IntegratedBC | Under Development |  |
| InterfaceKernel | Under Development |  |
| DGKernel | Under Development |  |
| MortarConstraint\\ +ADMortarConstraint+ | [`MortarScalarBase`](source/constraints/MortarScalarBase.md) | [`PeriodicSegmentalConstraint`](source/constraints/PeriodicSegmentalConstraint.md) |

## Automatic Differentiation

Scalar kernels have the ability to be implemented with
[automatic differentiation (AD)](automatic_differentiation/index.md).
While AD is not necessary for systems of ordinary differential equations (ODEs)
involving only scalar variables (due to the exact Jacobians offered by
[ParsedODEKernel.md], for example), ODEs involving contributions from field
variables greatly benefit from AD. For example, an elemental user object may
compute an `ADReal` value from field variable(s) on a domain, which then may
be used in a scalar equation.

To create an AD scalar kernel, derive from `ADScalarKernel` and implement the
method `computeQpResidual()`.

`ADScalarKernel` only works with MOOSE configured with global AD indexing (the default).

As a caution, if using user objects to compute
`ADReal` values, be sure to execute those user objects on `NONLINEAR` to
ensure the derivatives in the `ADReal` value are populated.




# Systems overview

There are four types of concrete systems in the MOOSE framework:

- [AuxiliarySystem.md]: This system holds auxiliary variable and degree of
  freedom information
- [DisplacedSystem.md]: This system wraps either nonlinear or auxiliary systems
  within a [displaced problem](DisplacedProblem.md) context
- [NonlinearEigenSystem.md]: This system is used for solving
  [eigen problems](EigenProblem.md) of the form $\mathbf{A}\vec{x} =
  \lambda\mathbf{B}\vec{x}$
  and interfaces with [SLEPc](https://slepc.upv.es/).
- [NonlinearSystem.md]: This system is used for solving nonlinear systems of
  equations and interfaces with [PETSc](https://petsc.org).

Both `NonlinearSystem` and `NonlinearEigenSystem` inherit from [NonlinearSystemBase.md]
which implements systems such as automatic scaling. `NonlinearSystemBase`,
`DisplacedSystem`, and `AuxiliarySystem` all inherit from [SystemBase.md] which
wraps the libMesh `System` object and provides APIs for accessing system vector
and matrix data among other things.

# Times

Times objects are used to:

- keep track of the times of events during MOOSE-based simulations
- provide a centralized place to input times, so objects can pull in the same times parameters

These tasks may be performed dynamically during the simulation, in which case a custom
`initialize()` or `execute()` routine may be implemented for the Times object.

## Combining Times

`Times` from multiple sources may be concatenated using the [ReporterTimes.md].




# Transfers System

When running simulations that contain [MultiApps](/MultiApps/index.md)---simulations running
other sub-simulations---it is often required to move data to and from the sub-applications. Transfer
objects in MOOSE are designed for this purpose.

Prior to understanding Transfers it is important to grasp the idea of [MultiApps](/MultiApps/index.md) first, so please
refer to the [MultiApps](/MultiApps/index.md) documentation for additional information.

## Example Transfer

Assuming that the concept of [MultiApps](/MultiApps/index.md) is understood, Transfers are best understood via an example
problem. First, consider a "parent" simulation that is solving the transient diffusion equation. This
parent simulation also includes two "sub" applications that rely on the average value of the unknown
from the parent application.

### The "parent" Simulation

[transfers-parent-multiapps] is an input file snippet showing the [MultiApps](/MultiApps/index.md) block that includes a
[TransientMultiApp](/TransientMultiApp.md), this sub-application will execute along with the parent
(at the end of each timestep) as time progresses.

         block=MultiApps id=transfers-parent-multiapps
         caption=The [MultiApps](/MultiApps/index.md) block of the "parent" application that contains two sub-application
                 that solves along with the parent as time progresses.

For this example, the sub-applications require that the average from the parent in the form of a
scalar AuxVariable, see the [AuxVariables] documentation for further information. Therefore the
parent will transfer the average value (computed via the
[ElementAverageValue](/ElementAverageValue.md) Postprocessor) to a scalar AuxVariable on each
sub-application. As shown in [transfers-parent-transfers], the
[MultiAppPostprocessorToAuxScalarTransfer](/MultiAppPostprocessorToAuxScalarTransfer.md) is provided
for this purpose.

         block=Transfers
         id=transfers-parent-transfers
         caption=The Transfers block of the "parent" application that contains a Transfer of a
                     Postprocessor to a scalar AuxVariable on sub-applications.

### The "sub" Simulations

For this simple example the sub-application must contain an appropriate AuxVariable to receiving
the Postprocessor value from the parent application.

         block=AuxVariables
         id=transfers-sub
         caption=The AuxVariables block of the "sub" application that contains a scalar that the
                     parent application will update.

The sub-applications do not have any "knowledge" of the parent application, and simply perform
calculations that utilize the scalar variable, regardless of how this scalar is computed. This
approach allows the sub-application input file to run in union of independent from the parent without
modification, which is useful for development and testing.

## Coordinate transformations id=coord-transform

Different applications may use different setups. For example a neutronics
simulation may be performed in Cartesian 3D space whereas a fuel performance
calculation may be performed using a 2D axisymmetric coordinate
system. Communicating information between these different configurations can be
difficult. One mechanism MOOSE provides for making this communication simpler is
the `MooseAppCoordTransform` class. Each `MooseApp` instance holds a coordinate
transformation object in its `MooseMesh` object. Users may specify
transformation information about their simulation setup on a per-application
basis in the input file `Mesh` block. The [!param](/Mesh/GeneratedMesh/coord_type)
parameter specifies the coordinate system type, e.g. XYZ, RZ, or
RSPHERICAL. [Euler angles](https://en.wikipedia.org/wiki/Euler_angles) are
available to describe extrinsic rotations. The convention MOOSE uses for
a alpha-beta-gamma Euler angle rotation is:

1. Rotation about the z-axis by [!param](/Mesh/GeneratedMesh/alpha_rotation) degrees
2. Rotation about the x-axis by [!param](/Mesh/GeneratedMesh/beta_rotation) degrees
3. Rotation about the z-axis (again) by [!param](/Mesh/GeneratedMesh/gamma_rotation) degrees


[!param](/Mesh/GeneratedMesh/length_unit) allows the user to specify
their mesh length unit. The code in `MooseAppCoordTransform`
which processes this parameter leverages the [MooseUnits](/Units.md) system. A
scaling transform will be constructed to convert a point in the mesh domain with
the prescribed mesh length unit to the reference domain with units of meters.
The last option which contributes to
transformation information held by the `MooseAppCoordTransform` class is the
[!param](/MultiApps/TransientMultiApp/positions) parameter which is described in
[MultiApps/index.md#multiapp-positions]. The value of `positions` exactly
corresponds to the translation vector set in the `MooseAppCoordTransform` object of
the sub-application. The `alpha_rotation`, `beta_rotation`, `gamma_rotation`,
and `positions` parameters essentially describe forward transformations of the
mesh domain described by the MOOSE `Mesh` block to a reference domain. Following
the ordering
[here](https://docs.microsoft.com/en-us/dotnet/desktop/winforms/advanced/why-transformation-order-is-significant?view=netframeworkdesktop-4.8),
the sequence of
transformations applied in the `MooseAppCoordTransform` class is:

1. scaling
2. rotation
3. translation
4. coordinate collapsing


The last item in the list, coordinate collapsing, is only relevant when
information has to be transferred between applications with different coordinate
systems. For transferring information from XYZ to RZ, we must collapse XYZ
coordinates into the RZ space since there is a unique mapping of XYZ coordinates
into RZ coordinates, but not vice versa, e.g. a point in RZ has infinitely many
corresponding locations in XYZ space due to rotation about the axis of
symmetry. The table below summarizes the coordinate collapses that occur when
transferring information between two different coordinate systems. The table
should be understood as follows, using the first row as an example: for a
XYZ-RZ pairing (e.g. RZ->XYZ *or* XYZ->RZ data transfers), both 'from' and 'to' points will be cast
into the RZ coordinate system for the reasoning given above: there is a unique
map from XYZ to RZ, but not vice versa. Similarly for a RZ-RSPHERICAL pairing
(e.g. RZ->RSPHERICAL *or* RSPHERICAL->RZ data transfers), both 'from' and 'to'
points will be cast into the RSPHERICAL coordinate system.

| Coordinate System 1 | Coordinate System 2 | Resulting Coordinate System for Data Transfer |
| - | - | - |
| XYZ | RZ | RZ |
| XYZ | RSPHERICAL | RSPHERICAL |
| RZ | RSPHERICAL | RSPHERICAL |

Note that there are consequences for these coordinate system collapses. When
transferring data in the 1 -> 2 directions, there are (as already stated) infinitely many points
in three-dimensional Cartesian space that correspond to a single
RZ coordinate. For example, the Cartesian points (1, 0, 0) and (0, 1, 0) map to the same
RZ coordinate (1, 0) if the z-axis is the axis of symmetry on the Cartesian
mesh. So if we are performing a nearest-node transfer of data from XYZ to RZ,
where the "to" point is (1, 0), then selection of the "from" point is arbitrary
if both (1, 0, 0) and (0, 1, 0) points (or any combination of $\sqrt{x^2+y^2}=1$
points) exist. We are considering how best to handle these situations moving
forward. One option would be to average the field data from equivalent points.

For the `RZ` coordinate system with general axes (see [Mesh/index.md#coordinate_systems]),
only translation is supported for coordinate transformations, i.e., there is
no scaling, rotation, or coordinate collapsing.

Framework transfer classes that support the coordinate transformation
processes described here are:

- [MultiAppGeometricInterpolationTransfer.md]
- [MultiAppShapeEvaluationTransfer.md]
- [MultiAppNearestNodeTransfer.md]
- [MultiAppPostprocessorInterpolationTransfer.md]
- [MultiAppProjectionTransfer.md]
- [MultiAppUserObjectTransfer.md]

### Examples

Let's consider an example. The below listing shows coordinate transformation
given in the `Mesh` block of a sub-application:


Here, the user is stating that a -90 degree alpha rotation (e.g. a point on the
y-axis becomes a point on the x-axis) should be applied to
the sub-application's domain in order to map to the reference domain (which the user has
chosen to correspond to the main application domain). Additionally, the user
wishes for the coordinate transformation object to know that one unit of mesh
length corresponds to 20 centimeters. This information from the sub-application's `Mesh` block
combined with the translation vector described by the `positions` parameter in
the main application `MultiApp` block


allows MOOSE to directly map information between the disparate application
domains. The figure below shows the variable field `v`, which is a nonlinear
variable in the sub-application and an auxiliary source variable in the main
application, in both domains, indicating a successful transfer of data after
applying the transformation order outlined above (rotation, scale, translation).



Another example leveraging the `MooseAppCoordTransform` class is a simulation in
which one application is in 3D XYZ space and another is in 2D RZ space. In this
example we wish to rotate the axis of symmetry, which is the Y-axis in the 2D RZ
simulation, in order to align with the z-axis when transferring data between the
2D RZ and 3D XYZ simulations. This simple rotation is achieved by specifying the
`beta_rotation` value below


We can see that the rotation transformation has been successful by examining the
same field in both applications (in this case the field is solved by the
nonlinear solver in the sub-application (variable `u`) and transferred to the
main application into the auxiliary field `v`).


We mentioned how forward rotation transformations can be achieved by specifying
Euler angles. Another parameter that can be used to perform rotations is
[!param](/Mesh/GeneratedMesh/up_direction). As described in the parameter
documentation string, if `up_direction` is specified, then in the
`MooseAppCoordTransform` object we will prescribe a rotation matrix that
corresponds to a single 90 degree rotation such that a point lying on the
`up_direction` axis will now lie on the y-axis. We have chosen the y-axis to be
the canonical reference frame up-direction because it is the literal
up-direction when opening an exodus file in Paraview. Additionally it is
consistent with boundary naming for cuboidal meshes generated using
[GeneratedMesh.md] or [GeneratedMeshGenerator.md] in which the upper y-boundary
is denoted as `top`.

## Available Transfer Objects

The following is a complete list of the available Transfer objects, each links to a page with further
details.




# UserObject System

The UserObject system is developing and running custom algorithms that may not fit well within
any other system in MOOSE. Examples include complex calculations that may result values that
don't associate in a one to one manner with elements, nodes, or sides. Perhaps your user object
produces values based on height in your domain or based on groups of related elements (not
necessarily associated with subdomains or other static mesh features). Often these calculations
may result in custom data structures that can be managed by the developer.

The UserObject system is the basis for the [Postprocessor](syntax/Postprocessors/index.md) system.
The only difference being that Postprocessors have an additional interface for returning values
and corresponding managed storage within the framework for retrieving those values through
well-defined interfaces \([PostprocessorInterface.md]\).

## User-defined APIs

One benefit of the UserObject system is that it is designed with user-defined APIs in mind.
UserObjects can and should define additional `public` methods that may be used to retrieve
data computed by the UserObject. The [UserObjectInterface.md] is templated so that an object
that depends on a specific type of UserObject may retrieve that specific type of UserObject
and use the interface without the use of dynamic casts.

## Types of UserObjects

- +GeneralUserObject+: "execute" is called once on each execution flag.
- +NodalUserObject+: "execute" is called for each +node+ within the mesh on each execution flag.
- +ElementalUserObject+: "execute" is called for each +element+ within the mesh on each execution
   flag.
- +InternalSideUserObject+: "execute" is called for each +side+, that is not on a boundary,
   within the mesh on each execution flag.
- +SideUserObject+: "execute" is called for each +side+, that is on a boundary, within the mesh
   on each execution flag. If the boundary is internal within the mesh, only variables, material
   properties, etc. at the primal side of the boundary are available.
- +InterfaceUserObject+: "execute" is called for each +side+, that is on an internal boundary,
   within the mesh on each execution flag. Variables, material properties, etc. at both the primary
   and the secondary side of the internal boundary are available.
- +DomainUserObject+: this object is capable of executing all the operations of
  a +ElementUserObject+, +InternalSideUserObject+, +SideUserObject+ and +InterfaceUserObject+.
- +MortarUserObject+: "execute" is called for each mortar segment element corresponding to the
  secondary-primary mortar interface pairing on each execution flag

# Execution order

Within an execution stage set by the [`execute_on`](SetupInterface.md) parameter, user objects are executed in
the following order:

1. `residualSetup` / `jacobianSetup`

   If the current `execute_on` flag is either `EXEC_LINEAR` or `EXEC_NONLINEAR` the `residualSetup`
   and `jacobianSetup` are called respectively in the following order

   1. for objects derived from `ElementUserObject`,  `SideUserObject`, `InternalSideUserObject`
      `InterfaceUserObject`, and  `DomainUserObject`.
   2. for objects derived from `NodalUserObject`.
   3. for objects derived from `ThreadedGeneralUserObject`.
   4. for objects derived from `GeneralUserObject`.

2. `initialize` is called for objects derived from `ElementUserObject`,  `SideUserObject`,
   `InternalSideUserObject` `InterfaceUserObject`, and  `DomainUserObject` in that order.

3. All active local elements are iterated over and objects derived from `ElementUserObject`,
   `SideUserObject`, `InternalSideUserObject` `InterfaceUserObject`, and  `DomainUserObject` are
   executed on elements, boundaries attached to the element, internal sides between elements, and on subdomain changes, in that order.
   The order within each type group is determined through dependency resolution.

4. `threadJoin` and `finalize` are called in the following order

   1. for objects derived from `SideUserObject`
   2. for objects derived from `InternalSideUserObject`
   3. for objects derived from `InterfaceUserObject`
   4. for objects derived from `ElementUserObject`
   5. for objects derived from `DomainUserObject`

5. `initialize` is called for objects derived from `NodalUserObject`.

6. `NodalUserObject` are looped over all local nodes and executed on each node.
   On each node, the order is determined through dependency resolution.

7. `threadJoin` and `finalize` are called for `NodalUserObject`s.

8. `initialize` is called for objects derived from `ThreadedGeneralUserObject`.

9. `execute` is called for objects derived from `ThreadedGeneralUserObject` in a threaded way.

10. `threadJoin` and `finalize` ar called for `ThreadedGeneralUserObject`s.

12. `initialize`, `execute`, and `finalize` are called in that order for each `GeneralUserObject` (which in turn are ordered through dependency resolution within the set of applicable `GeneralUserObject`s).

For additional control over the user object execution order every user object has a `execution_order_group`
parameter of type integer. This parameter can be used to force multiple execution rounds of the
above order, so it effectively supersedes all the ordering described above. All objects with the same `execution_order_group` parameter value are executed in the
same round, and groups with a lower number are executed first. The default `execution_order_group`
is 0 (zero). Negative values can be specified to force user object execution *before* the default group, and
positive values can be uses to create execution groups that run *after* the default group. Execution
order groups apply to all `execute_on` flags specified for a given object.

## Restartable Data

Since UserObjects often create and store large data structures, the developer of a UserObject
should consider whether or not those data structures needs to be declared as "restartable".
Knowing whether or not a data structure should be declared restartable is straight-forward:
If the information in a data structure is expected to persist across time steps, it +must+
be declared as restartable. Conversely, if the data in a data structure is recomputed
at each invocation of the UserObject, no action is necessary. See [restart_recover.md](restart_recover.md optional=true)
for more information.

# Variables System

## Description

The `Variables` block within an input file is utilized to define the unknowns within a system
of partial differential equations. These unknowns are often referred to as nonlinear variables
within documentation. The nonlinear variables defined within this block are used by
[Kernel objects](syntax/Kernels/index.md) to define the equations for a simulation.
Also, scalar variables that are constant in space but evolve in time can be described by
ordinary differential equations.

Documentation on the major classes of variables are presented in:

- [MooseVariableBase](source/variables/MooseVariableBase.md): for typical finite element
  nonlinear variables and scalar variables
- [MooseVariableFV](source/variables/MooseVariableFV.md): for finite volume variables

## Example

The following input file snippet demonstrates the creation of a single nonlinear variable that
is used by two Kernel objects, refer to [Example 2](ex02_kernel.md optional=True) for more details.







# VectorPostprocessors System

The VectorPostprocessors (VPP) System is designed to compute multiple related values each time it is executed.  It can be thought of as a Postprocessor that outputs multiple values. For example, if you'd like to sample a solution field across a line, a VPP is a good choice
(See [PointValueSampler](PointValueSampler.md)).  In addition to outputting the values along the line a VPP can actually output multiple vectors simultaneously.  Each vector is given a name, which is the column name.  Together, all of the vectors a VPP outputs are output in one CSV file (usually per-timestep).

The [Reporters/index.md] is a newer, more flexible system for computing aggregate values. It is recommended
that new objects for aggregate calculations use the Reporter system.

## Design

The VPP system builds off from MOOSE's [UserObject](/UserObjects/index.md) system. Each VPP contains the full interface of a UserObject but
is also expected to declare one or more vectors that will be populated and output by each VPP. There are no restrictions on the lengths of
these vectors and the state of these vectors is managed by MOOSE and is automatically "restartable".

Vectors are declared with the `declareVector` method:


This method returns a writable reference to a VectorPostprocessorValue that must be captured and stored in the object.


Developers are responsible for sizing these vectors as needed.

## Output

VPP data can vary depending on the type of data being output. Again, the "sample over line" example mentioned in the introduction,
a complete set of values will be generated each time the VPP is executed. The VPP system handles this scenario by creating separate output
files for each invocation. The form of the output is as follows:

```
<filebase>_<vector name>_<serial number>.csv

# filebase - the normal output file base
# vector name - the name of the vector postprocessor (normally the input block name for that VPP)
# serial number - a fixed-width (normally four digit) number starting from 0000 and counting up.
```

In some cases however, a VPP may be accumulating information in time. For example, a user may wish to track values at several locations
over time. The output might consist of the coordinates of those positions and the sampled value. In such a scenario, the default separate
file output may be cumbersome as each file would effectively have a single line so a script to aggregate the information from all of the
separate output files may need to be used. Instead, MOOSE supports an option, which may be of use in these cases:

```
contains_complete_history = true
```

By setting this value, you are telling MOOSE that the values in all of the vectors of the given VPP are cumulative. MOOSE will take
advantage of this information in multiple ways. First, it will turn off writing the output to separate files and will drop the serial
number from the output filename format altogether. Secondly, it will ignore any changed values in the vectors only outputting the newest
rows in each vector postprocessor.

### Parallel Assumptions

VectorPostprocessors are required to create their complete vectors on processor zero (rank 0).  They should use the `_communicator` to reduce their values to processor zero.  Objects that use VPPs must specify how they need the data by calling the `getVectorPostprocessorValue()` or `getScatterVectorPostprocessorValue()` functions with the correct arguments.

If the object needing VPP values only needs those values on processor zero it should call:

```c++
getVectorPostprocessorValue('the_vpp_parameter_name', 'the_vector_name', false)
```

The `false` in that call tells MOOSE that this object does NOT need the vector to be "broadcast" (i.e. "replicated).

If this object does indeed need the VPP data to be broadcast (replicated on all processors) it should make this call:

```c++
getVectorPostprocessorValue('the_vpp_parameter_name', 'the_vector_name', true)
```

In the very special case that a VPP is producing vectors that are `num_procs` length an object can ask for the value of a VPP to be "scattered" - which means that each processor will receive only the value that corresponds to it's rank (i.e. `_values[rank]`).  This is accomplished by calling:

```c++
getScatterVectorPostprocessorValue('the_vpp_parameter_name', 'the_vector_name')
```

`getScatterVectorPostprocessorValue()` returns a `const ScatterVectorPostprocessorValue &`... which is a single scalar value that you don't index into.  Each process receives the "correct" value and can just directly use it.


If the data in a VPP is naturally replicated on all processors a VectorPostprocessor should set `_auto_broadcast = false` in its `validParams()` like so:

```c++
params.set<bool>("_auto_broadcast") = "false";
```

This tells MOOSE that the data is already replicated and there is no need to broadcast it if another object is asking for it to be broadcast.

## TimeData

The `time_data` parameter produces an additional CSV file containing just the real time and the corresponding time step for any VectorPostprocessor output information. This file may be useful in producing animations or your simulation results.

# VectorPostprocessor List




