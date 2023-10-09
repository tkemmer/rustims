import numpy as np
import pandas as pd
from numpy.typing import NDArray
from typing import List

import pyims_connector as pims
from pyims.frame import TimsFrame
from pyims.spectrum import MzSpectrum


class TimsSlice:
    def __int__(self):
        self.__slice_ptr = None
        self.__current_index = 0

    @classmethod
    def from_py_tims_slice(cls, slice: pims.PyTimsSlice):
        """Create a TimsSlice from a PyTimsSlice.

        Args:
            slice (pims.PyTimsSlice): PyTimsSlice to create the TimsSlice from.

        Returns:
            TimsSlice: TimsSlice created from the PyTimsSlice.
        """
        instance = cls.__new__(cls)
        instance.__slice_ptr = slice
        instance.__current_index = 0
        return instance

    @property
    def first_frame_id(self) -> int:
        """First frame ID.

        Returns:
            int: First frame ID.
        """
        return self.__slice_ptr.first_frame_id

    @property
    def last_frame_id(self) -> int:
        """Last frame ID.

        Returns:
            int: Last frame ID.
        """
        return self.__slice_ptr.last_frame_id

    def __repr__(self):
        return f"TimsSlice({self.first_frame_id}, {self.last_frame_id})"

    def filter_ranged(self, mz_min: float, mz_max: float, scan_min: int = 0, scan_max: int = 1000, intensity_min: float = 0.0, num_threads: int = 4) -> 'TimsSlice':
        """Filter the slice by m/z, scan and intensity.

        Args:
            mz_min (float): Minimum m/z value.
            mz_max (float): Maximum m/z value.
            scan_min (int, optional): Minimum scan value. Defaults to 0.
            scan_max (int, optional): Maximum scan value. Defaults to 1000.
            intensity_min (float, optional): Minimum intensity value. Defaults to 0.0.
            num_threads (int, optional): Number of threads to use. Defaults to 4.

        Returns:
            TimsSlice: Filtered slice.
        """
        return TimsSlice.from_py_tims_slice(self.__slice_ptr.filter_ranged(mz_min, mz_max, scan_min, scan_max, intensity_min, num_threads))

    def get_frames(self) -> List[TimsFrame]:
        """Get the frames.

        Returns:
            List[TimsFrame]: Frames.
        """
        return [TimsFrame.from_py_tims_frame(frame) for frame in self.__slice_ptr.get_frames()]

    def to_windows(self, window_length: float = 10, overlapping: bool = True, min_num_peaks: int = 5, min_intensity: float = 1, num_threads: int = 4) -> List[MzSpectrum]:
        """Convert the slice to a list of windows.

        Args:
            window_length (float, optional): Window length. Defaults to 10.
            overlapping (bool, optional): Whether the windows should overlap. Defaults to True.
            min_num_peaks (int, optional): Minimum number of peaks in a window. Defaults to 5.
            min_intensity (float, optional): Minimum intensity of a peak in a window. Defaults to 1.
            num_threads (int, optional): Number of threads to use. Defaults to 1.

        Returns:
            List[MzSpectrum]: List of windows.
        """
        return [MzSpectrum.from_py_mz_spectrum(spec) for spec in self.__slice_ptr.to_windows(window_length, overlapping, min_num_peaks, min_intensity, num_threads)]

    @property
    def data(self) -> pd.DataFrame:
        cols = ['frame_id', 'scan', 'tof', 'retention_time', 'mobility', 'mz', 'intensity']
        return pd.DataFrame({c: v for c, v in zip(cols, self.__slice_ptr.to_arrays())})

    def __iter__(self):
        return self

    def __next__(self):
        if self.__current_index < self.__slice_ptr.frame_count:
            frame_ptr = self.__slice_ptr.get_frame_at_index(self.__current_index)
            self.__current_index += 1
            if frame_ptr is not None:
                return TimsFrame.from_py_tims_frame(frame_ptr)
            else:
                raise ValueError("Frame pointer is None for valid index.")
        else:
            self.__current_index = 0  # Reset for next iteration
            raise StopIteration
