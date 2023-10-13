use pyo3::prelude::*;
use numpy::{PyArray1, IntoPyArray};
use mscore::{TimsFrame, ImsFrame, MsType};
use pyo3::types::PyList;

use crate::py_mz_spectrum::{PyMzSpectrum, PyTimsSpectrum};

#[pyclass]
#[derive(Clone)]
pub struct PyTimsFrame {
    pub inner: TimsFrame,
}

#[pymethods]
impl PyTimsFrame {

    #[new]
    pub unsafe fn new(frame_id: i32,
                      ms_type: i32,
                      retention_time: f64,
                      scan: &PyArray1<i32>,
                      mobility: &PyArray1<f64>,
                      tof: &PyArray1<i32>,
                      mz: &PyArray1<f64>,
                      intensity: &PyArray1<f64>) -> PyResult<Self> {
        Ok(PyTimsFrame {
            inner: TimsFrame {
                frame_id,
                ms_type: MsType::new(ms_type),
                scan: scan.as_slice()?.to_vec(),
                tof: tof.as_slice()?.to_vec(),
                ims_frame: ImsFrame {
                    retention_time,
                    mobility: mobility.as_slice()?.to_vec(),
                    mz: mz.as_slice()?.to_vec(),
                    intensity: intensity.as_slice()?.to_vec(),
                },
            },
        })
    }
    #[getter]
    pub fn mz(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.ims_frame.mz.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn intensity(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.ims_frame.intensity.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn scan(&self, py: Python) -> Py<PyArray1<i32>> {
        self.inner.scan.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn mobility(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.ims_frame.mobility.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn tof(&self, py: Python) -> Py<PyArray1<i32>> {
        self.inner.tof.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn frame_id(&self) -> i32 {
        self.inner.frame_id
    }
    #[getter]
    pub fn ms_type_numeric(&self) -> i32 {
        self.inner.ms_type.ms_type_numeric()
    }
    #[getter]
    pub fn ms_type(&self) -> String {
        self.inner.ms_type.to_string()
    }
    #[getter]
    pub fn retention_time(&self) -> f64 {
        self.inner.ims_frame.retention_time
    }

    pub fn to_resolution(&self, resolution: i32) -> PyTimsFrame {
        PyTimsFrame { inner: self.inner.to_resolution(resolution) }
    }

    pub fn to_tims_spectra(&self, py: Python) -> PyResult<Py<PyList>> {
        let spectra = self.inner.to_tims_spectra();
        let list: Py<PyList> = PyList::empty(py).into();

        for spec in spectra {
            let py_tims_spectrum = Py::new(py, PyTimsSpectrum { inner: spec })?;
            list.as_ref(py).append(py_tims_spectrum)?;
        }

        Ok(list.into())
    }

    pub fn to_windows(&self, py: Python, window_length: f64, overlapping: bool, min_peaks: usize, min_intensity: f64) -> PyResult<Py<PyList>> {

        let windows = self.inner.to_windows(window_length, overlapping, min_peaks, min_intensity);
        let list: Py<PyList> = PyList::empty(py).into();

        for window in windows {
            let py_mz_spectrum = Py::new(py, PyMzSpectrum { inner: window })?;
            list.as_ref(py).append(py_mz_spectrum)?;
        }

        Ok(list.into())
    }

    pub fn filter_ranged(&self, mz_min: f64, mz_max: f64, scan_min: i32, scan_max: i32, intensity_min: f64, intensity_max: f64) -> PyTimsFrame {
        return PyTimsFrame { inner: self.inner.filter_ranged(mz_min, mz_max, scan_min, scan_max, intensity_min, intensity_max) }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct PyTimsFrameVectorized {
    pub inner: TimsFrame,
}