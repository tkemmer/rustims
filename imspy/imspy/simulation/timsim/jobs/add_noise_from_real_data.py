from typing import List

import numpy as np

from imspy.simulation.acquisition import TimsTofAcquisitionBuilderDIA
from imspy.timstof.frame import TimsFrame


def add_real_data_noise_to_frames(
        acquisition_builder: TimsTofAcquisitionBuilderDIA,
        frames: List[TimsFrame],
        intensity_max: float = 30,
        sample_fraction: float = 0.5,
        num_frames: int = 10,
) -> List[TimsFrame]:
    """Add noise to frame.

    Args:
        acquisition_builder: Acquisition builder.
        frames (List[TimsFrame]): Frames.
        intensity_max (float): Maximum intensity.
        sample_fraction (float): Sample fraction.
        num_frames (int): Number of frames to sample.

    Returns:
        List[TimsFrame]: Frames.
    """
    r_list = []

    d = acquisition_builder.frames_to_window_groups
    window_group_dict = dict(zip(d['frame'], d['window_group']))
    fragment_frames = set(window_group_dict.keys())

    for frame in frames:
        if frame.frame_id in fragment_frames:
            window_group = window_group_dict[frame.frame_id]

            noise = acquisition_builder.tdf_writer.helper_handle.sample_fragment_signal(num_frames, window_group, intensity_max, sample_fraction)
            r_list.append(frame + noise)
        else:
            noise = acquisition_builder.tdf_writer.helper_handle.sample_precursor_signal(num_frames, intensity_max, sample_fraction)
            r_list.append(frame + noise)

    return r_list
