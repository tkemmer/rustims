from numba import jit
import tensorflow as tf
import numpy as np
from scipy.stats import norm
import math
import importlib.resources as resources

from numpy.typing import NDArray
import pandas as pd
from imspy.chemistry.mass import AMINO_ACID_MASSES, MASS_WATER, calculate_mz

from dlomix.reports.postprocessing import reshape_dims, reshape_flat, normalize_base_peak, mask_outofcharge, mask_outofrange
from typing import List


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


def to_prosit_tensor(sequences: List) -> tf.Tensor:
    """
    translate a list of fixed length numpy arrays into a tensorflow tensor
    Args:
        sequences: list of numpy arrays, representing peptide sequences

    Returns:
        tensorflow tensor
    """
    return tf.convert_to_tensor(sequences, dtype=tf.string)


def generate_prosit_intensity_prediction_dataset(sequences: List[str], charges: NDArray, collision_energies=None):
    """
    generate a tensorflow dataset for the prediction of fragment intensities with prosit
    Args:
        sequences: list of peptide sequences
        charges: list of precursor charges
        collision_energies: list of collision energies

    Returns:
        tensorflow dataset
    """

    # if no collision energies are given, use 0.35 as default (training data value)
    if collision_energies is None:
        collision_energies = np.expand_dims(np.repeat([0.35], len(charges)), 1)

    charges = tf.one_hot(charges - 1, depth=6)
    sequences = to_prosit_tensor([sequence_to_numpy(s) for s in sequences])

    return tf.data.Dataset.from_tensor_slices({"sequence": sequences,
                                               "precursor_charge": charges,
                                               "collision_energy": collision_energies})


def post_process_predicted_fragment_spectra(data_pred: pd.DataFrame) -> NDArray:
    """
    post process the predicted fragment intensities
    Args:
        data_pred: dataframe containing the predicted fragment intensities

    Returns:
        numpy array of fragment intensities
    """
    # get sequence length for masking out of sequence
    sequence_lengths = data_pred["sequence"].apply(lambda x: len(x))

    # get data
    intensities = np.stack(data_pred["predicted_intensity"].to_numpy()).astype(np.float32)
    # set negative intensity values to 0
    intensities[intensities < 0] = 0
    intensities = reshape_dims(intensities)

    # mask out of sequence and out of charge
    intensities = mask_outofrange(intensities, sequence_lengths)
    intensities = mask_outofcharge(intensities, data_pred.charge)
    intensities = reshape_flat(intensities)

    # save indices of -1.0 values, will be altered by intensity normalization
    m_idx = intensities == -1.0
    # normalize to base peak
    intensities = normalize_base_peak(intensities)
    intensities[m_idx] = -1.0
    return intensities


def reshape_pred(flat_intensities: NDArray) -> NDArray:
    """
    reshape the predicted fragment intensities to (peptide_fragment, fragment_type, charge)
    Args:
        flat_intensities: numpy array of fragment intensities

    Returns:
        numpy array of fragment intensities, reshaped to (peptide_fragment, fragment_type, charge)
    """
    return flat_intensities.reshape([29, 2, 3])


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


def calculate_b_y_ion_series(sequence: str, modifications, charge: int = 1):
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
