from typing import List
from numpy.typing import NDArray

import numpy as np
import pyims_connector as pims


class TimsFrame:
    def __init__(self, frame_id: int, ms_type: int, retention_time: float, scan: NDArray[np.int32],
                 inv_mobility: NDArray[np.float64], tof: NDArray[np.int32],
                 mz: NDArray[np.float64], intensity: NDArray[np.float64]):
        """TimsFrame class.

        Args:
            frame_id (int): Frame ID.
            ms_type (int): MS type.
            retention_time (float): Retention time.
            scan (NDArray[np.int32]): Scan.
            inv_mobility (NDArray[np.float64]): Inverse mobility.
            tof (NDArray[np.int32]): Time of flight.
            mz (NDArray[np.float64]): m/z.
            intensity (NDArray[np.float64]): Intensity.

        Raises:
            AssertionError: If the length of the scan, inv_mobility, tof, mz and intensity arrays are not equal.
        """

        assert len(scan) == len(inv_mobility) == len(tof) == len(mz) == len(intensity), \
            "The length of the scan, inv_mobility, tof, mz and intensity arrays must be equal."

        self.__frame_ptr = pims.PyTimsFrame(frame_id, ms_type, retention_time, scan, inv_mobility, tof, mz, intensity)

    @classmethod
    def from_py_tims_frame(cls, frame: pims.PyTimsFrame):
        """Create a TimsFrame from a PyTimsFrame.

        Args:
            frame (pims.PyTimsFrame): PyTimsFrame to create the TimsFrame from.

        Returns:
            TimsFrame: TimsFrame created from the PyTimsFrame.
        """
        instance = cls.__new__(cls)
        instance.__frame_ptr = frame
        return instance

    @property
    def frame_id(self) -> int:
        """Frame ID.

        Returns:
            int: Frame ID.
        """
        return self.__frame_ptr.frame_id

    @property
    def ms_type(self) -> str:
        """MS type.

        Returns:
            int: MS type.
        """
        return self.__frame_ptr.ms_type_as_string

    @property
    def retention_time(self) -> float:
        """Retention time.

        Returns:
            float: Retention time.
        """
        return self.__frame_ptr.retention_time

    @property
    def scan(self) -> NDArray[np.int32]:
        """Scan.

        Returns:
            NDArray[np.int32]: Scan.
        """
        return self.__frame_ptr.scan

    @property
    def inv_mobility(self) -> NDArray[np.float64]:
        """Inverse mobility.

        Returns:
            NDArray[np.float64]: Inverse mobility.
        """
        return self.__frame_ptr.inv_mobility

    @property
    def tof(self) -> NDArray[np.int32]:
        """Time of flight.

        Returns:
            NDArray[np.int32]: Time of flight.
        """
        return self.__frame_ptr.tof

    @property
    def mz(self) -> NDArray[np.float64]:
        """m/z.

        Returns:
            NDArray[np.float64]: m/z.
        """
        return self.__frame_ptr.mz

    @property
    def intensity(self) -> NDArray[np.float64]:
        """Intensity.

        Returns:
            NDArray[np.float64]: Intensity.
        """
        return self.__frame_ptr.intensity

    def filter_ranged(self, mz_min: float, mz_max: float,
                      scan_min: int = 0,
                      scan_max: int = 1000,
                      intensity_min: float = 0.0,
                      ) -> 'TimsFrame':
        """Filter the frame for a given m/z range, scan range and intensity range.

        Args:
            mz_min (float): Minimum m/z value.
            mz_max (float): Maximum m/z value.
            scan_min (int, optional): Minimum scan value. Defaults to 0.
            scan_max (int, optional): Maximum scan value. Defaults to 1000.
            intensity_min (float, optional): Minimum intensity value. Defaults to 0.0.

        Returns:
            TimsFrame: Filtered frame.
        """

        return TimsFrame.from_py_tims_frame(self.__frame_ptr.filter_ranged(mz_min, mz_max, scan_min, scan_max, intensity_min))

    def __repr__(self):
        return (f"TimsFrame(frame_id={self.__frame_ptr.frame_id}, ms_type={self.__frame_ptr.ms_type_as_string}, "
                f"num_peaks={len(self.__frame_ptr.mz)})")
