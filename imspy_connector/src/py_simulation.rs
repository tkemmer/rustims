use mscore::algorithm::fragmentation::TimsTofCollisionEnergy;
use pyo3::prelude::*;
use rustdf::sim::simulation::{TimsTofSynthetics, TimsTofSyntheticsDIA};
use crate::py_tims_frame::PyTimsFrame;

#[pyclass]
pub struct PyTimsTofSynthetics {
    pub inner: TimsTofSynthetics,
}

#[pymethods]
impl PyTimsTofSynthetics {
    #[new]
    pub fn new(db_path: &str) -> Self {
        let path = std::path::Path::new(db_path);
        PyTimsTofSynthetics { inner: TimsTofSynthetics::new(path).unwrap() }
    }

    pub fn build_frame(&self, frame_id: u32) -> PyTimsFrame {
        PyTimsFrame { inner: self.inner.build_precursor_frame(frame_id) }
    }

    pub fn build_frames(&self, frame_ids: Vec<u32>, num_threads: usize) -> Vec<PyTimsFrame> {
        let frames = self.inner.build_precursor_frames(frame_ids, num_threads);
        frames.iter().map(|x| PyTimsFrame { inner: x.clone() }).collect::<Vec<_>>()
    }
}

#[pyclass(unsendable)]
pub struct PyTimsTofSyntheticsDIA {
    pub inner: TimsTofSyntheticsDIA,
}

#[pymethods]
impl PyTimsTofSyntheticsDIA {
    #[new]
    pub fn new(db_path: &str) -> Self {
        let path = std::path::Path::new(db_path);
        PyTimsTofSyntheticsDIA { inner: TimsTofSyntheticsDIA::new(path).unwrap() }
    }

    pub fn build_frame(&self, frame_id: u32, fragment: bool) -> PyTimsFrame {
        PyTimsFrame { inner: self.inner.build_frame(frame_id, fragment) }
    }

    pub fn build_frames(&self, frame_ids: Vec<u32>, fragment: bool, num_threads: usize) -> Vec<PyTimsFrame> {
        let frames = self.inner.build_frames(frame_ids, fragment, num_threads);
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