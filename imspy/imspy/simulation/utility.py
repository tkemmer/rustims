import json
import re
from importlib.abc import Traversable

from numba import jit
import numpy as np
from scipy.stats import norm
import math
import importlib.resources as resources

from imspy.chemistry.mass import AMINO_ACID_MASSES, MASS_WATER, calculate_mz, MODIFICATIONS_MZ

import imspy_connector as ims

from typing import List, Tuple
from numpy.typing import NDArray

import toml
from typing import Any, Dict


def get_acquisition_builder_resource_path(acquisition_mode: str = 'dia') -> Traversable:
    """ Get the path to a pretrained model

    Args:
        acquisition_mode: The name of the model to load

    Returns:
        The path to the pretrained model
    """
    assert acquisition_mode in ['dia', 'midia', 'slice', 'synchro'], \
        f"acquisition_mode needs to be one of 'dia', 'midia', 'slice', 'synchro', was: {acquisition_mode}"

    return resources.files('imspy.simulation.resources.configs').joinpath(acquisition_mode + 'pasef.toml')


def get_ms_ms_window_layout_resource_path(acquisition_mode: str) -> Traversable:
    """ Get the path to a pretrained model

    Returns:
        The path to the pretrained model
    """

    assert acquisition_mode in ['dia', 'midia', 'slice', 'synchro'], \
        f"acquisition_mode needs to be one of 'dia', 'midia', 'slice', 'synchro', was: {acquisition_mode}"

    return resources.files('imspy.simulation.resources.configs').joinpath(acquisition_mode + '_ms_ms_windows.csv')


def read_acquisition_config(acquisition_name: str = 'dia') -> Dict[str, Any]:

    file_path = get_acquisition_builder_resource_path(acquisition_name)

    with open(file_path, 'r') as config_file:
        config_data = toml.load(config_file)
    return config_data


def remove_unimod_annotation(sequence: str) -> str:
    """Remove [UNIMOD:N] annotations from the sequence."""
    pattern = r'\[UNIMOD:\d+\]'
    return re.sub(pattern, '', sequence)


def extract_unimod_patterns(input_string: str):
    """Extract [UNIMOD:N] patterns along with their start and end indices."""
    pattern = r'\[UNIMOD:\d+\]'
    return [(match.start(), match.end(), match.group()) for match in re.finditer(pattern, input_string)]


def generate_index_list(results, sequence):
    """Generate a list of indices along with amino acids and modified patterns."""
    index_list = []
    chars_removed_counter = 0

    for (start, end, mod) in results:
        num_chars_removed = end - start
        mod = sequence[start:end]

        if start != 0:
            current_aa_index = start - 1
            later_aa_index = current_aa_index - chars_removed_counter
        else:
            later_aa_index = 0

        index_list.append((later_aa_index, mod))
        chars_removed_counter += num_chars_removed

    return index_list


def calculate_modifications(index_list, stripped_sequence):
    """Calculate the sum weight of modifications for every amino acid in the original sequence."""
    mods = np.zeros(len(stripped_sequence))
    for (index, mod) in index_list:
        mods[index] += MODIFICATIONS_MZ[mod]
    return mods


def find_unimod_patterns(input_string: str):
    """Find [UNIMOD:N] patterns and calculate modifications."""
    results = extract_unimod_patterns(input_string)
    stripped_sequence = remove_unimod_annotation(input_string)
    index_list = generate_index_list(results, input_string)
    mods = calculate_modifications(index_list, stripped_sequence)
    return stripped_sequence, mods


def sequence_to_all_ions(
        sequence: str,
        charge: int,
        intensity_pred: NDArray,
        normalize: bool = True,
        half_charge_one: bool = True
) -> str:
    """Generate a list of all b and y ions for a given peptide sequence.
    Args:
        sequence: the peptide sequence
        intensity_pred: the predicted fragment intensities
        charge: the charge state of the peptide precursor
        normalize: whether to normalize the fragment intensities, will result in sum of intensities to be 1.0
        half_charge_one: whether to double the intensity of the b and y ions for charge 1

    Returns:
        JSON string of all b and y ions for the sequence
    """
    stripped_sequence, mods = find_unimod_patterns(sequence)

    r_list = []
    sum_intensity = 1.0
    max_charge = np.min([charge, 4])

    if normalize:
        sum_intensity = 0.0
        # sum all intensities, needed for normalization
        for z in range(1, np.max([max_charge, 2])):

            intensity_b = intensity_pred[:len(stripped_sequence) - 1, 1, z - 1]
            intensity_y = intensity_pred[:len(stripped_sequence) - 1, 0, z - 1]

            sum_intensity += np.sum(intensity_b) + np.sum(intensity_y)

    for z in range(1, np.max([max_charge, 2])):
        b, y = calculate_b_y_ion_series_ims(stripped_sequence, mods, charge=z)

        # extract intensity for given charge state only
        intensity_b = intensity_pred[:len(stripped_sequence) - 1, 1, z - 1]
        # reverse the intensity array to match the order of the y ions, small masses come first in prosit output
        intensity_y = intensity_pred[:len(stripped_sequence) - 1, 0, z - 1][::-1]

        if max_charge == 1 and half_charge_one:
            sum_intensity *= 2

        json_str = generate_fragments_json(stripped_sequence,
                                           b_ions=b,
                                           intensity_b=intensity_b / sum_intensity,
                                           intensity_y=intensity_y / sum_intensity,
                                           y_ions=y,
                                           charge=z
                                           )

        r_list.append(json_str)

    return json.dumps(r_list)


def generate_fragments_json(
        sequence: str,
        charge: int,
        b_ions: List[Tuple[float, str, str]],
        y_ions: List[Tuple[float, str, str]],
        intensity_b: NDArray | None = None,
        intensity_y: NDArray | None = None,
        num_decimals: int = 4,
        default_b: float = 1.0,
        default_y: float = 1.0,
):
    peptide_ion_data = {
        # "sequence": sequence,  # Example sequence
        "charge": charge,  # Example charge state
        "b_ions": [],
        "y_ions": []
    }

    # Populate b ions with a default intensity value
    for i, (mz, ion_type, _) in enumerate(b_ions):  # Adjusted to match the new structure without sequence
        if intensity_b is not None:
            default_b = np.round(intensity_b[i].astype(np.float64), 9)

        peptide_ion_data["b_ions"].append({
            "mz": float(np.round(mz, num_decimals)),
            "kind": ion_type[:-2],
            "intensity": default_b,  # Default intensity value
        })

    # Populate y ions similarly, with a default intensity value
    for i, (mz, ion_type, _) in enumerate(y_ions):  # Adjusted loop, replace with actual y ions data
        if intensity_y is not None:
            default_y = np.round(intensity_y[i].astype(np.float64), 9)
        peptide_ion_data["y_ions"].append({
            "mz": float(np.round(mz, num_decimals)),
            "kind": ion_type[:-2],
            "intensity": default_y,  # Default intensity value
        })

    return peptide_ion_data


# Function to convert a list (or a pandas series) to a JSON string
def python_list_to_json_string(lst, as_float=True, num_decimals: int = 4) -> str:
    if as_float:
        return json.dumps([float(np.round(x, num_decimals)) for x in lst])
    return json.dumps([int(x) for x in lst])


# load peptides and ions
def json_string_to_python_list(json_string):
    return json.loads(json_string)


def sequence_to_numpy(sequence: str, max_length: int = 30) -> NDArray:
    """
    translate a peptide sequence given as python string into a numpy array of characters with a fixed length
    Args:
        sequence: the peptide sequence
        max_length: the maximum length a sequence can have

    Returns:
        numpy array of characters
    """
    arr = np.full((1, max_length), fill_value="", dtype=object)
    for i, char in enumerate(sequence):
        arr[0, i] = char
    return np.squeeze(arr)


def calculate_b_y_fragment_mz(sequence: str, modifications: NDArray, is_y: bool = False, charge: int = 1) -> float:
    """
    Calculate the m/z value of a b or y fragment.
    Args:
        sequence: the peptide sequence
        modifications: potential modifications
        is_y: is the fragment a y ion
        charge: the charge state of the peptide precursor

    Returns:
        m/z value of the fragment
    """
    # return mz of empty sequence
    if len(sequence) == 0:
        return 0.0

    # add up raw amino acid masses and potential modifications
    mass = np.sum([AMINO_ACID_MASSES[s] for s in sequence]) + np.sum(modifications)

    # if sequence is n-terminal, add water mass and calculate mz
    if is_y:
        return calculate_mz(mass + MASS_WATER, charge)

    # otherwise, calculate mz
    return calculate_mz(mass, charge)


def calculate_b_y_ion_series(sequence: str, modifications: NDArray, charge: int = 1) -> Tuple[List, List]:
    """
    Calculate the b and y ion series for a given peptide sequence.
    Args:
        sequence: the peptide sequence
        modifications: potential modifications
        charge: the charge state of the peptide precursor

    Returns:
        b ion series, y ion series
    """
    b_ions, b_seqs, y_seqs = [], [], []
    y_ions, b_masses, y_masses = [], [], []

    # iterate over all possible cleavage sites
    for i in range(len(sequence) + 1):
        y = sequence[i:]
        b = sequence[:i]
        m_y = modifications[i:]
        m_b = modifications[:i]

        # calculate mz of b ions
        if len(b) > 0 and len(b) != len(sequence):
            b_mass = calculate_b_y_fragment_mz(b, m_b, is_y=False, charge=charge)
            b_ions.append(f"b{i}+{charge}")
            b_seqs.append(b)
            b_masses.append(np.round(b_mass, 6))

        # calculate mz of y ions
        if len(y) > 0 and len(y) != len(sequence):
            y_ions.append(f"y{len(sequence) - i}+{charge}")
            y_mass = calculate_b_y_fragment_mz(y, m_y, is_y=True, charge=charge)
            y_seqs.append(y)
            y_masses.append(np.round(y_mass, 6))

    return list(zip(b_masses, b_ions, b_seqs)), list(zip(y_masses, y_ions, y_seqs))


def calculate_b_y_ion_series_ims(sequence: str, modifications: NDArray, charge: int = 1) -> Tuple[List, List]:
    """
    Calculate the b and y ion series for a given peptide sequence.
    Args:
        sequence: the peptide sequence
        modifications: potential modifications
        charge: the charge state of the peptide precursor

    Returns:
        b ion series, y ion series
    """
    return ims.calculate_b_y_ion_series(sequence, modifications, charge)


def get_native_dataset_path(ds_name: str = 'NATIVE.d') -> str:
    """ Get the path to a pretrained model

    Args:
        ds_name: The name of the dataset to load

    Returns:
        The path to the pretrained model
    """
    return str(resources.files('imspy.simulation.resources').joinpath(ds_name))


@jit(nopython=True)
def generate_events(n, mean, min_val, max_val):
    generated_values = np.random.exponential(scale=mean, size=n * 10)
    filtered_values = np.empty(n, dtype=np.float32)
    count = 0

    for val in generated_values:
        if min_val <= val <= max_val:
            filtered_values[count] = float(int(val))
            count += 1
            if count == n:
                break

    return filtered_values[:count]


@jit(nopython=True)
def custom_cdf(x, mean, std_dev):
    """
    Custom implementation of the CDF for a normal distribution.
    """
    z = (x - mean) / std_dev
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


@jit(nopython=True)
def accumulated_intensity_cdf_numba(sample_start, sample_end, mean, std_dev):
    """
    Calculate the accumulated intensity between two points using the custom CDF.
    """
    cdf_start = custom_cdf(sample_start, mean, std_dev)
    cdf_end = custom_cdf(sample_end, mean, std_dev)
    return cdf_end - cdf_start


@jit(nopython=True)
def irt_to_rts_numba(irt: NDArray, new_min=0, new_max=120):
    """
    Scale an array of values from the original range (min_val, max_val) to a new range (new_min, new_max).

    Parameters
    ----------
    irt : NDArray
        Array of values to be scaled.
    new_min : float
        Minimum value of the new range.
    new_max : float
        Maximum value of the new range.

    Returns
    -------
    NDArray
        Array of scaled values.
    """
    min_val = np.min(irt)
    max_val = np.max(irt)
    scaled_values = new_min + (irt - min_val) * (new_max - new_min) / (max_val - min_val)
    return scaled_values


@jit(nopython=True)
def calculate_number_frames(gradient_length: float = 90 * 60, rt_cycle_length: float = .108) -> int:
    """ Calculate the number of frames that will be taken during the acquisition

    Parameters
    ----------
    gradient_length : float
        Length of the gradient in seconds
    rt_cycle_length : float
        Length of the RT cycle in seconds

    Returns
    -------
    int
        Number of frames that will be taken during the acquisition
    """
    return int(gradient_length / rt_cycle_length)


@jit(nopython=True)
def calculate_mobility_spacing(mobility_min: float, mobility_max: float, num_scans=500) -> float:
    """ Calculate the amount of mobility that will be occupied by a single scan

    Parameters
    ----------
    mobility_min : float
        Minimum mobility value
    mobility_max : float
        Maximum mobility value
    num_scans : int
        Number of scans that will be taken during the acquisition

    Returns
    -------
    float
        Mobility spacing
    """
    length = float(mobility_max) - float(mobility_min)
    return length / num_scans


def get_z_score_for_percentile(target_score=0.95):
    assert 0 <= target_score <= 1.0, f"target_score needs to be between 0 and 1, was: {target_score}"
    return norm.ppf(1 - (1 - target_score) / 2)


@jit(nopython=True)
def calculate_bounds_numba(mean, std, z_score):
    """
    Calculate the bounds of a normal distribution for a given z-score.

    Parameters
    ----------
    mean : float
        Mean of the normal distribution
    std : float
        Standard deviation of the normal distribution
    z_score : float
        Z-score of the normal distribution

    Returns
    -------
    float
        Lower bound of the normal distribution
    """
    return mean - z_score * std, mean + z_score * std


@jit(nopython=True)
def get_frames_numba(rt_value, times_array, std_rt, z_score):
    """
    Get the frames that will be acquired for a given retention time value.
    Parameters
    ----------
    rt_value : float
        Retention time value
    times_array : NDArray
        Array of retention times
    std_rt : float
        Standard deviation of the retention time
    z_score : float
        Z-score of the normal distribution

    Returns
    -------
    NDArray
        Array of frame indices
    """
    rt_min, rt_max = calculate_bounds_numba(rt_value, std_rt, z_score)
    first_frame = np.argmin(np.abs(times_array - rt_min)) + 1
    last_frame = np.argmin(np.abs(times_array - rt_max)) + 1
    rt_frames = np.arange(first_frame, last_frame + 1)

    return rt_frames


@jit(nopython=True)
def get_scans_numba(im_value, ims_array, scans_array, std_im, z_score):
    """
    Get the scans that will be acquired for a given ion mobility value.
    """
    im_min, im_max = calculate_bounds_numba(im_value, std_im, z_score)
    im_start = np.argmin(np.abs(ims_array - im_max))
    im_end = np.argmin(np.abs(ims_array - im_min))

    scan_start = scans_array[im_start]
    scan_end = scans_array[im_end]

    # Generate scan indices in the correct order given the inverse relationship
    im_scans = np.arange(scan_start, scan_end + 1)
    return im_scans
