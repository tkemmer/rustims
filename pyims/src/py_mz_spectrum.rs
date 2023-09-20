use pyo3::prelude::*;
use numpy::{PyArray1, IntoPyArray};
use mscore::{MzSpectrum, TimsFrame, MsType};

#[pyclass]
pub struct PyMzSpectrum {
    inner: MzSpectrum,
}

#[pymethods]
impl PyMzSpectrum {
    #[new]
    pub unsafe fn new(mz: &PyArray1<f64>, intensity: &PyArray1<f64>) -> PyResult<Self> {
        Ok(PyMzSpectrum {
            inner: MzSpectrum {
                mz: mz.as_slice()?.to_vec(),
                intensity: intensity.as_slice()?.to_vec(),
            },
        })
    }

    #[getter]
    pub fn mz(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.mz.clone().into_pyarray(py).to_owned()
    }

    #[getter]
    pub fn intensity(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.intensity.clone().into_pyarray(py).to_owned()
    }
}

#[pyclass]
pub struct PyTimsFrame {
    pub inner: TimsFrame,
}

#[pymethods]
impl PyTimsFrame {
    #[new]
    pub unsafe fn new(frame_id: i32, ms_type: i32, retention_time: f64, scan: &PyArray1<i32>, inv_mobility: &PyArray1<f64>, tof: &PyArray1<i32>, mz: &PyArray1<f64>, intensity: &PyArray1<f64>) -> PyResult<Self> {
        Ok(PyTimsFrame {
            inner: TimsFrame {
                frame_id,
                ms_type: MsType::new(ms_type),
                retention_time,
                scan: scan.as_slice()?.to_vec(),
                inv_mobility: inv_mobility.as_slice()?.to_vec(),
                tof: tof.as_slice()?.to_vec(),
                mz: mz.as_slice()?.to_vec(),
                intensity: intensity.as_slice()?.to_vec(),
            },
        })
    }
    #[getter]
    pub fn mz(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.mz.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn intensity(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.intensity.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn scan(&self, py: Python) -> Py<PyArray1<i32>> {
        self.inner.scan.clone().into_pyarray(py).to_owned()
    }
    #[getter]
    pub fn inv_mobility(&self, py: Python) -> Py<PyArray1<f64>> {
        self.inner.inv_mobility.clone().into_pyarray(py).to_owned()
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
    pub fn ms_type(&self) -> i32 {
        self.inner.ms_type.to_i32()
    }
}