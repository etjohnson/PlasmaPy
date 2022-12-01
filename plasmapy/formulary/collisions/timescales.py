"""
Module contains the functionality for computing different
timescales commonly associated with collisions.
"""
import astropy.units

"""
This module contains functionality for calculating the timescales
for a range of configurations.
"""

__all__ = ["Hellinger", "Hellinger_2009", "Hellinger_2010", "Hellinger_2016"]

import astropy.units as u
import numpy as np

from astropy.constants.si import eps0
from math import pi as pi
from mpmath import hyper2d
from scipy.stats import gausshyper as gh

from plasmapy.formulary.collisions import coulomb
from plasmapy.particles import Particle, ParticleList
from plasmapy.utils.decorators import validate_quantities


class validate:
    # Validate n_i argument
    def n_i(
        n_i: u.m**-3,
    ):
        if not isinstance(n_i, astropy.units.Quantity):
            raise TypeError(
                "Argument 'n_i' must be an astropy.units.Quantity, "
                f"instead got type of {type(n_i)}."
            )
        n_i = n_i.squeeze()
        if n_i.ndim != 0:
            raise ValueError(
                "Argument 'n_i' must be single value and not an array of"
                f" shape {n_i.shape}."
            )
        elif not isinstance(n_i.value, (int, float)):
            raise TypeError(
                "Argument 'n_i' must be an integer or float, received "
                f"{n_i} of type {type(n_i)}."
            )
        elif not n_i.value > 0:
            raise ValueError(
                f"Argument 'n_i' must be an positive argument, received "
                f"{n_i} of type {type(n_i)}."
            )

        return n_i

    # Validate ions argument
    def ions(
        ions: (Particle, Particle),
    ):
        if not isinstance(ions, (list, tuple, ParticleList)):
            ions = [ions]
        ions = ParticleList(ions)

        if not all(
            failed := [ion.is_ion and abs(ion.charge_number) > 0 for ion in ions]
        ):
            raise ValueError(
                "Particle(s) passed to 'ions' must be a charged"
                " ion. The following particle(s) is(are) not allowed "
                f"{[ion for ion, fail in zip(ions, failed) if not fail]}"
            )

        # Validate ions dimension
        if len(ions) != 2:
            raise ValueError(
                f"Argument 'ions' can only take 2 inputs, received {ions}"
                f"with {len(ions)} inputs. Please try again."
            )
        return ions

    # Validate any speed argument
    def speeds(
        speeds: u.m / u.s,
    ):

        if len(speeds) != 2:
            raise ValueError(
                "Argument 'speeds' can only take 2 inputs, received "
                f"{speeds} with {speeds.ndim} inputs."
            )
        return speeds

    @validate_quantities(
        T={"can_be_negative": False, "equivalencies": u.temperature_energy()},
    )
    def temp(
        T: u.K,
    ):
        # Validate temperature argument
        if T.shape != ():
            raise ValueError(
                "Argument 'T' must be single value and not an array of"
                f" shape {T.shape}."
            )
        elif not isinstance(T.value, (int, float)):
            raise TypeError(
                f"Argument 'T' must be an integer or float, received {T} "
                f"with type of {type(T)}."
            )
        elif not T.value > 0:
            raise ValueError(
                f"Argument 'T' must be a positive argument, received "
                f"{T} of type {type(T)}."
            )

        return T

    def method(
        method,
    ):
        if isinstance(method, None):
            return "classical"
        elif not isinstance(method, str):
            raise TypeError(
                "Argument 'method' is of incorrect type, got type "
                f"of {type(method)} and type of str is required."
            )


def Hellinger(
    inputs,
    version,
):
    r"""
    Compute the collisional timescale as presented in either
    :cite:t:`hellinger:2009`, :cite:t:`hellinger:2010` or
    :cite:t:`hellinger:2016`. Provide inputs for the respective
    function and then specify the version.

    Parameters
    ----------
    inputs : `~astropy.units.Quantity`
        A `Dict` containing the inputs for the desired function.

    version : `int` or `float`
        Specify which version you wish to use, currently 2009,
        2010 and 2016 are included.

    Returns
    -------
    :math:`\tau` : `~astropy.units.Quantity`
        The collisional timescale in units of seconds.

    Raises
    ------
    `TypeError`
        If version is not an instance of `int` or `float`

    `ValueError`
        If the value entered for version is not supported,
        supported values are 2009, 2010 and 2016.

    Notes
    -----

    species s on species t.

    Example
    -------
    >>> from astropy import units as u
    >>> from plasmapy.particles import Particle
    >>> from plasmapy.formulary.collisions.timescales import Hellinger
    >>> inputs = {
    ...     "T": 8.3e-9 * u.T,
    ...     "n_i": 4.0e5 * u.m**-3,
    ...     "ions": [Particle("H+"), Particle("He+")],
    ...     "par_speeds":  [500, 750] * u.m /u.s,
    ...     "logarithm": None,
    ... }
    >>>
    <Quantity 1 / s>
    """

    valid_versions = [2009, 2010, 2016]
    valid_functions = [Hellinger_2009, Hellinger_2010, Hellinger_2016]

    if not isinstance(version, (float, int)):
        raise TypeError(
            "Argument 'version' must be of type float or integer, "
            f"instead got type of {type(version)}."
        )
    elif version not in valid_versions:
        raise ValueError(
            "Argument 'version' is not a valid entry, valid entries "
            f"are {valid_versions}. Please try again."
        )

    return valid_functions[valid_versions.index(version)](**inputs)


def Hellinger_2009(
    T: u.K,
    n_i: u.m**-3,
    ions: (Particle, Particle),
    par_speeds: u.m / u.s,
    method: None
):
    r"""
    Compute the collisional timescale as presented by :cite:t:`hellinger:2009`.
    For more details please see the notes section.

    Parameters
    ----------
    T : `~astropy.units.Quantity`
        The scalar temperature magnitude in units convertible to K.

    n_i : `~astropy.units.Quantity`
        Ion number density in units convertible to m\ :sup:`-3`.  Must
        be single value and should be the ion of prime interest.

    ions :  a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an instance of the
        :term:`particle-like` object representing the ion species in
        each entry. (e.g., ``"p"`` for protons, ``"D+"`` for deuterium,
         `["p", ``D+``]).

    par_speeds : a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an `~astropy.units.Quantity` representing
        the PARALLEL velocity with units of  in each entry. (e.g [
        500 * u.m / u.s, 745 * u.m / u.s]).

    method : `str`
        A string specifying the desired method for the Coulomb
        logarithm, for options please the notes section below.

    Returns
    -------
    :math:`\tau` : `~astropy.units.Quantity`
        The collisional timescale in units of seconds.

    Raises
    ------
    `TypeError`
        If applicable arguments are not instances of
        `~astropy.units.Quantity` or cannot be converted into one.

    `ValueError`
        Number of particles in ``ions`` is not 2 or the input values
        are not valid particles

    `ValueError`
        If ``n_i`` or ``T`` is negative or not a single value.

    `TypeError`
        If ``n_i`` or ``T`` is not of type integer or float.

    `ValueError`
        Number of parallel speeds in``par_speeds`` is not 2.

    `TypeError`
        If the parallel speeds in ``par_speeds`` is not of type
        integer or float

    `TypeError`
        If the value for ``method`` is not of type string

    ~astropy.units.UnitTypeError
        If applicable arguments do not have units convertible to the
        expected units.

    Notes
    -----
    Compute the collisional timescale as presented by :cite:t:`hellinger:2009`.
    In a weakly collisional plasma with the dominance of small angle
    deflections by Coulomb collisions, the collision frequency is
    calculated. The collision frequency is of species :math:`\alpha`
    on :math:`\beta` and is given by:

    .. math::
        \nu_{\alpha \beta} = \frac{q_{\alpha}^{2}q_{\beta}^{2}n_{\beta}}
        {12\pi^{3/2}\epsilon_{0}^{2}m_{\alpha}m_{\beta}
        v_{\alpha \beta \parallel}^{3}}\ln{\Lambda_{\alpha \beta}}

    where

    .. math::
        \ln{\Lambda_{\alpha \beta}} \equiv
        \int^{b_{\rm min, \alpha \beta}}_{b_{\rm max, \alpha \beta}}
        \frac{db}{b} = \ln{\left (\frac{b_{\rm max, \alpha \beta}}{b_{\rm min, \alpha \beta}} \right)}

    and

    .. math::
        v_{\alpha \beta} = \sqrt{\frac{v_{\alpha \parallel}^{2} +
        v_{\beta \parallel}^{2}}{2}}

    such that :math:`q` is the charge of the respective species,
    :math:`n` is the ion density of the species of interest,
    :math:`m` is the mass of the respective species and
    :math:`v_{parallel}` is the parallel speed of the respective
    species.

    The following methods are supported by the Coulomb Logarithm
    1. ``"classical"`` or ``"ls"``
    2. ``"ls_min_interp"`` or ``"GMS-1"``
    3. ``"ls_full_interp"`` or ``"GMS-2"``
    4. ``"ls_clamp_mininterp"`` or ``"GMS-3"``
    5. ``"hls_min_interp"`` or ``"GMS-4"``
    6. ``"hls_max_interp"`` or ``"GMS-5"``
    7. ``"hls_full_interp"`` or ``"GMS-6"``

    Example
    _______

    """
    # Validate arguments argument
    T = validate.temp(T)
    n_i = validate.n_i(n_i)
    ions = validate.ions(ions)
    par_speeds = validate.speeds(par_speeds)
    method = validate.method(method)

    v_par = np.sqrt((par_speeds[0].value ** 2 + par_speeds[1].value ** 2) / 2)

    a = (ions[0].charge.value ** 2) * (ions[1].charge.value ** 2) * n_i.value

    b = (
        (12 * (pi**1.5))
        * (ions[0].mass.value * ions[1].mass.value)
        * (eps0**2)
        * (v_par**3)
    )

    c = coulomb.Coulomb_logarithm(T, n_i, ions,method=method)

    return ((a / b.value) * c) / u.s


def Hellinger_2010(
    T_par: u.K,
    T_perp: u.K,
    n_i: u.m**-3,
    ions: (Particle, Particle),
    par_speeds: u.m / u.s,
    method: None,
):
    r"""
    Compute the collisional timescale as presented by :cite:t:`hellinger:2010`.
    For more details please see the notes section.

    Parameters
    ----------
    T_par : `~astropy.units.Quantity`
        The parallel temperature magnitude in units convertible to K.

    T_perp : `~astropy.units.Quantity`
        The perpendicular temperature magnitude in units convertible to K.

    n_i : `~astropy.units.Quantity`
        Ion number density in units convertible to m\ :sup:`-3`.  Must
        be single value and should be the ion of prime interest.

    ions :  a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an instance of the
        :term:`particle-like` object representing the ion species in
        each entry. (e.g., ``"p"`` for protons, ``"D+"`` for deuterium,
         `["p", ``D+``]).

    par_speeds : a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an `~astropy.units.Quantity` representing
        the PARALLEL velocity with units of  in each entry. (e.g [
        500 * u.m / u.s, 745 * u.m / u.s]).

    method : `str`
        A string specifying the desired method for the Coulomb
        logarithm, for options please the notes section below.

    Returns
    -------
    :math:`\tau` : `~astropy.units.Quantity`
        The collisional timescale in units of seconds.

    Raises
    ------
    `TypeError`
        If applicable arguments are not instances of
        `~astropy.units.Quantity` or cannot be converted into one.

    `ValueError`
        Number of particles in ``ions`` is not 2 or the input values
        are not valid particles

    `ValueError`
        If ``n_i``, ``T_par`` or ``T_perp`` is negative or not a
        single value.

    `TypeError`
        If ``n_i``, ``T_par`` or ``T_perp`` is not of type
        integer or float.

    `ValueError`
        Number of parallel speeds in``par_speeds`` is not 2.

    `TypeError`
        If the parallel speeds in ``par_speeds`` is not of type
        integer or float

    `TypeError`
        If the value for ``method`` is not of type string

    ~astropy.units.UnitTypeError
        If applicable arguments do not have units convertible to the
        expected units.

    Notes
    -----
    Compute the collisional timescale as presented by :cite:t:`hellinger:2010`.
    In a weakly collisional plasma with the dominance of small angle
    deflections by Coulomb collisions, the collision frequency is
    calculated. The collision frequency is of species :math:`\alpha`
    on :math:`\beta` and is given by:

    .. math::
        \nu_{\alpha \beta} = \frac{q_{\alpha}^{2}q_{\beta}^{2}n_{\beta}}
        {20\pi^{3/2}\epsilon_{0}^{2}m_{\alpha}m_{\beta}
        v_{\alpha \beta \parallel}^{3}}\ln{\Lambda_{\alpha \beta}}
        \,_2F_1 \left (\begin{matrix}
        2, 3/2 \\
        7/2
        \end{matrix}, \, \begin{matrix}
        1 - \frac{T_{\perp}}{T_{\parallel}}
        \end{matrix} \right)

    where

    .. math::
        \ln{\Lambda_{\alpha \beta}} \equiv
        \int^{b_{\rm min, \alpha \beta}}_{b_{\rm max, \alpha \beta}}
        \frac{db}{b} = \ln{\left (\frac{b_{\rm max, \alpha \beta}}{b_{\rm min, \alpha \beta}} \right)}

    and

    .. math::
        v_{\alpha \beta} = \sqrt{\frac{v_{\alpha \parallel}^{2} +
        v_{\beta \parallel}^{2}}{2}}

    such that :math:`q` is the charge of the respective species,
    :math:`n` is the ion density of the species of interest,
    :math:`m` is the mass of the respective species and
    :math:`v_{parallel}` is the parallel speed of the respective
    species. Note :math:`\,_2F_1` is the standard Gauss hyper geometric
    function.

    The following methods are supported by the Coulomb Logarithm
    1. ``"classical"`` or ``"ls"``
    2. ``"ls_min_interp"`` or ``"GMS-1"``
    3. ``"ls_full_interp"`` or ``"GMS-2"``
    4. ``"ls_clamp_mininterp"`` or ``"GMS-3"``
    5. ``"hls_min_interp"`` or ``"GMS-4"``
    6. ``"hls_max_interp"`` or ``"GMS-5"``
    7. ``"hls_full_interp"`` or ``"GMS-6"``

    Example
    _______
    """

    # Validate other arguments
    T_par = validate.temp(T_par)
    T_perp = validate.temp(T_perp)
    n_i = validate.n_i(n_i)
    ions = validate.ions(ions)
    par_speeds = validate.speeds(par_speeds)

    if T_par == 0:
        raise ValueError("Argument 'T_par' must be a non zero value, please try again.")
    else:
        T = (2 * T_perp + T_par) / 3
        return (
            Hellinger_2009(T, n_i, ions, par_speeds, method)
            * 3
            / 5
            * gh(a=2, b=1.5, c=7 / 2, x=(1 - (T_perp / T_par)))
        )


def Hellinger_2016(
    T_par: (u.K, u.K),
    T_perp: (u.K, u.K),
    n_i: u.m**-3,
    ions: (Particle, Particle),
    par_speeds: (u.m / u.s, u.m / u.s),
    perp_speeds: (u.m / u.s, u.m / u.s),
    method: None,
):
    r"""
    Compute the collisional timescale as presented by :cite:t:`hellinger:2016`.
    For more details please see the notes section.

    Parameters
    ----------
    T_par : a `list` of length 2 containing `~astropy.units.Quantity`
        The parallel temperature magnitude in units convertible to K.

    T_perp : a `list` of length 2 containing `~astropy.units.Quantity`
        The perpendicular temperature magnitude in units convertible to K.

    n_i : `~astropy.units.Quantity`
        Ion number density in units convertible to m\ :sup:`-3`.  Must
        be single value and should be the ion of prime interest.

    ions :  a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an instance of the
        :term:`particle-like` object representing the ion species in
        each entry. (e.g., ``"p"`` for protons, ``"D+"`` for deuterium,
         `["p", ``D+``]).

    par_speeds : a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an `~astropy.units.Quantity` representing
        the PARALLEL velocity with units of  in each entry. (e.g [
        500 * u.m / u.s, 745 * u.m / u.s]).

    perp_speeds : a `list` of length 2 containing :term:`particle-like` objects
        A list of length 2 with an `~astropy.units.Quantity` representing
        the PERPENDICULAR velocity with units of  in each entry. (e.g [
        500 * u.m / u.s, 745 * u.m / u.s]).

    method : `str`
        A string specifying the desired method for the Coulomb
        logarithm, for options please the notes section below.

    Returns
    -------
    :math:`\tau` : `~astropy.units.Quantity`
        The collisional timescale in units of seconds.

    Raises
    ------
    `TypeError`
        If applicable arguments are not instances of
        `~astropy.units.Quantity` or cannot be converted into one.

    `ValueError`
        Number of particles in ``ions`` is not 2 or the input values
        are not valid particles

    `ValueError`
        If ``n_i``, ``T_par`` or ``T_perp`` is negative or not a
        single value.

    `TypeError`
        If ``n_i``, ``T_par`` or ``T_perp`` is not of type
        integer or float.

    `ValueError`
        Number of parallel speeds in``par_speeds`` or ``perp_speeds``
        is not 2.

    `TypeError`
        If the parallel speeds in ``par_speeds`` or ``perp_speeds``
        is not of type integer or float

    `TypeError`
        If the value for ``method`` is not of type string

    ~astropy.units.UnitTypeError
        If applicable arguments do not have units convertible to the
        expected units.

    Notes
    -----
    Compute the collisional timescale as presented by :cite:t:`hellinger:2016`.
    Assuming a homogeneous plasma consisting of species with
    bi-Maxwellian velocity distribution and a weakly collisional plasma
    with the dominance of small angle deflections by Coulomb collisions.
    The collision frequency is calculated of species :math:`\alpha`
    on :math:`\beta` and is given by:

    .. math::
        \nu_{\alpha \beta} = \frac{q_{\alpha}^{2}q_{\beta}^{2}n_{\alpha \beta}}
        {24\pi^{3/2}\epsilon_{0}^{2}m_{\alpha}m_{\beta}
        v_{\alpha \beta \parallel}^{3}}\ln{\Lambda_{\alpha \beta}}
        \,_2F_1 \left (\begin{matrix}
        2, 3/2 \\
        7/2
        \end{matrix}, \, \begin{matrix}
        1 - \frac{T_{\perp}}{T_{\parallel}}
        \end{matrix} \right)

    where

    .. math::
        \ln{\Lambda_{\alpha \beta}} \equiv
        \int^{b_{\rm min, \alpha \beta}}_{b_{\rm max, \alpha \beta}}
        \frac{db}{b} = \ln{\left (\frac{b_{\rm max, \alpha \beta}}{b_{\rm min, \alpha \beta}} \right)}

    and

    .. math::
        v_{\alpha \beta} = \sqrt{\frac{v_{\alpha \parallel}^{2} +
        v_{\beta \parallel}^{2}}{2}}

    such that :math:`q` is the charge of the respective species,
    :math:`n` is the ion density, :math:`m` is the mass of the
    respective species and :math:`v_{parallel}` is the parallel speed
    of the respective species.

    Note :math:`\,_2F_1` is the standard
    Gauss hyper geometric function.

    The following methods are supported by the Coulomb Logarithm
    1. ``"classical"`` or ``"ls"``
    2. ``"ls_min_interp"`` or ``"GMS-1"``
    3. ``"ls_full_interp"`` or ``"GMS-2"``
    4. ``"ls_clamp_mininterp"`` or ``"GMS-3"``
    5. ``"hls_min_interp"`` or ``"GMS-4"``
    6. ``"hls_max_interp"`` or ``"GMS-5"``
    7. ``"hls_full_interp"`` or ``"GMS-6"``

    Example
    _______
    """
    # Validate arguments
    T_par = validate.temp(T_par)
    T_perp = validate.temp(T_perp)
    n_i = validate.n_i(n_i)
    ions = validate.ions(ions)
    par_speeds = validate.speeds(par_speeds)
    perp_speeds = validate.speeds(perp_speeds)
    method = validate.method(method)

    # Check for divide by zero error with t_par
    if T_par == 0:
        raise ValueError("Argument 'T_par' must be a non zero value, please try again.")
    else:
        T = (2 * T_perp + T_par) / 3

        vstpar = np.sqrt((par_speeds[0] ** 2 + par_speeds[1] ** 2) / 2)

        Ast = (ions.mass[0] * T_perp[1] + ions.mass[1] * T_perp[0]) / (
            ions.mass[0] * T_par[1] + ions.mass[1] * T_par[0]
        )

        vs = (par_speeds[0] ** 2 + 2 * perp_speeds[0] ** 2) / 3
        vt = (par_speeds[1] ** 2 + 2 * perp_speeds[1] ** 2) / 3

        vst = vs - vt

        return Hellinger_2009(T, n_i, ions, par_speeds) * hyper2d(
            1, 1.5, 2.5, 1 - Ast, Ast * (vst**2 / 4 * vstpar**2)
        )