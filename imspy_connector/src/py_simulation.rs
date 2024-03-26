use mscore::timstof::collision::TimsTofCollisionEnergy;
use pyo3::prelude::*;
use rustdf::sim::dia::{TimsTofSyntheticsFrameBuilderDIA};
use rustdf::sim::precursor::{TimsTofSyntheticsPrecursorFrameBuilder};
use rustdf::sim::handle::TimsTofSyntheticsDataHandle;
use crate::py_tims_frame::PyTimsFrame;

#[pyclass]
pub struct PyTimsTofSyntheticsDataHandle {
    pub inner: TimsTofSyntheticsDataHandle,
}

#[pymethods]
impl PyTimsTofSyntheticsDataHandle {
    #[new]
    pub fn new(db_path: &str) -> Self {
        let path = std::path::Path::new(db_path);
        PyTimsTofSyntheticsDataHandle { inner: TimsTofSyntheticsDataHandle::new(path).unwrap() }
    }

    pub fn get_transmitted_ions(&self, num_threads: Option<usize>) -> (Vec<i32>, Vec<i32>, Vec<String>, Vec<i8>, Vec<f32>) {
        let threads = num_threads.unwrap_or(4);
        self.inner.get_transmitted_ions(threads)
    }
}

#[pyclass]
pub struct PyTimsTofSyntheticsPrecursorFrameBuilder {
    pub inner: TimsTofSyntheticsPrecursorFrameBuilder,
}

#[pymethods]
impl PyTimsTofSyntheticsPrecursorFrameBuilder {
    #[new]
    pub fn new(db_path: &str) -> Self {
        let path = std::path::Path::new(db_path);
        PyTimsTofSyntheticsPrecursorFrameBuilder { inner: TimsTofSyntheticsPrecursorFrameBuilder::new(path).unwrap() }
    }

    pub fn build_precursor_frame(&self, frame_id: u32, mz_noise_precursor: bool, precursor_noise_ppm: f64) -> PyTimsFrame {
        PyTimsFrame { inner: self.inner.build_precursor_frame(frame_id, mz_noise_precursor, precursor_noise_ppm) }
    }

    pub fn build_precursor_frames(&self, frame_ids: Vec<u32>, mz_noise_precursor: bool, precursor_noise_ppm: f64, num_threads: usize) -> Vec<PyTimsFrame> {
        let frames = self.inner.build_precursor_frames(frame_ids, mz_noise_precursor, precursor_noise_ppm, num_threads);
        frames.iter().map(|x| PyTimsFrame { inner: x.clone() }).collect::<Vec<_>>()
    }
}

#[pyclass(unsendable)]
pub struct PyTimsTofSyntheticsFrameBuilderDIA {
    pub inner: TimsTofSyntheticsFrameBuilderDIA,
}

#[pymethods]
impl PyTimsTofSyntheticsFrameBuilderDIA {
    #[new]
    pub fn new(db_path: &str, num_threads: usize) -> Self {
        let path = std::path::Path::new(db_path);
        PyTimsTofSyntheticsFrameBuilderDIA { inner: TimsTofSyntheticsFrameBuilderDIA::new(path, num_threads).unwrap() }
    }

    pub fn build_frame(&self, frame_id: u32, mz_noise_precursor: bool, precursor_noise_ppm: f64, mz_noise_fragment: bool, fragment_noise_ppm: f64, fragment: bool) -> PyTimsFrame {
        let frames = self.inner.build_frames(vec![frame_id], fragment, mz_noise_precursor, precursor_noise_ppm, mz_noise_fragment, fragment_noise_ppm, 1);
        PyTimsFrame { inner: frames[0].clone() }
    }

    pub fn build_frames(&self, frame_ids: Vec<u32>, fragment: bool, mz_noise_precursor: bool, precursor_noise_ppm: f64, mz_noise_fragment: bool, fragment_noise_ppm: f64, num_threads: usize) -> Vec<PyTimsFrame> {
        let frames = self.inner.build_frames(frame_ids, fragment, mz_noise_precursor, precursor_noise_ppm, mz_noise_fragment, fragment_noise_ppm, num_threads);
        frames.iter().map(|x| PyTimsFrame { inner: x.clone() }).collect::<Vec<_>>()
    }

    pub fn get_collision_energy(&self, frame_id: i32, scan_id: i32) -> f64 {
        self.inner.get_collision_energy(frame_id, scan_id)
    }

    pub fn get_collision_energies(&self, frame_ids: Vec<i32>, scan_ids: Vec<i32>) -> Vec<f64> {
        let mut result = Vec::with_capacity(frame_ids.len());
        for (frame_id, scan_id) in frame_ids.iter().zip(scan_ids.iter()) {
            result.push(self.inner.get_collision_energy(*frame_id, *scan_id));
        }
        result
    }
}

#[pymodule]
pub fn simulation(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyTimsTofSyntheticsDataHandle>()?;
    m.add_class::<PyTimsTofSyntheticsPrecursorFrameBuilder>()?;
    m.add_class::<PyTimsTofSyntheticsFrameBuilderDIA>()?;
    Ok(())
}