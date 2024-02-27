import imspy_connector as ims

from imspy import MzSpectrum


class AminoAcidSequence:
    def __init__(self, sequence: str):
        self.__ptr = ims.PyAminoAcidSequence(sequence)

    @property
    def sequence(self) -> str:
        return self.__ptr.sequence

    @property
    def monoisotopic_mass(self) -> float:
        return self.__ptr.monoisotopic_mass

    def get_mz(self, charge: int) -> float:
        return self.__ptr.get_mz(charge)

    def get_ptr(self):
        return self.__ptr

    @classmethod
    def fom_py_ptr(cls, seq: ims.PyAminoAcidSequence):
        instance = cls.__new__(cls)
        instance.__ptr = seq
        return instance

    # min_intensity: i32, k: i32, resolution: i32, centroid: bool
    def precursor_spectrum_averagine(self, min_intensity: int = 1, k: int = 10, resolution: int = 3, centroid: bool = True) -> MzSpectrum:
        return MzSpectrum.from_py_mz_spectrum(self.__ptr.precursor_spectrum_averagine(
            min_intensity, k, resolution, centroid
        ))

    def __repr__(self):
        return f"AminoAcidSequence(sequence={self.sequence}, mass={self.mass})"
