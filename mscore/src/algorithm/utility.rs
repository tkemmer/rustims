// extern crate rgsl;

use std::collections::HashMap;
// use rgsl::{IntegrationWorkspace, error::erfc, error::erf};
use std::f64::consts::SQRT_2;
use rayon::prelude::*;
use rayon::ThreadPoolBuilder;

// Numerical integration using the trapezoidal rule
fn integrate<F>(f: F, a: f64, b: f64, n: usize) -> f64
    where
        F: Fn(f64) -> f64,
{
    let dx = (b - a) / n as f64;
    let mut sum = 0.0;
    for i in 0..n {
        let x = a + i as f64 * dx;
        sum += f(x);
    }
    sum * dx
}

// Complementary error function (erfc)
fn erfc(x: f64) -> f64 {
    1.0 - erf(x)
}

// Error function (erf)
fn erf(x: f64) -> f64 {
    let t = 1.0 / (1.0 + 0.5 * x.abs());
    let tau = t * (-x * x - 1.26551223 + t * (1.00002368 +
        t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 +
            t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 +
                t * (-0.82215223 + t * 0.17087277)))))))))
        .exp();
    if x >= 0.0 {
        1.0 - tau
    } else {
        tau - 1.0
    }
}

// Exponentially modified Gaussian function
fn emg(x: f64, mu: f64, sigma: f64, lambda: f64) -> f64 {
    let part1 = lambda / 2.0 * (-lambda * (x - mu) + lambda * lambda * sigma * sigma / 2.0).exp();
    let part2 = erfc((mu + lambda * sigma * sigma - x) / (sigma * 2.0_f64.sqrt()));
    part1 * part2
}

pub fn custom_cdf_normal(x: f64, mean: f64, std_dev: f64) -> f64 {
    let z = (x - mean) / std_dev;
    0.5 * (1.0 + erf(z / SQRT_2))
}

pub fn accumulated_intensity_cdf_normal(sample_start: f64, sample_end: f64, mean: f64, std_dev: f64) -> f64 {
    let cdf_start = custom_cdf_normal(sample_start, mean, std_dev);
    let cdf_end = custom_cdf_normal(sample_end, mean, std_dev);
    cdf_end - cdf_start
}

pub fn calculate_bounds_normal(mean: f64, std: f64, z_score: f64) -> (f64, f64) {
    (mean - z_score * std, mean + z_score * std)
}

pub fn emg_function(x: f64, mu: f64, sigma: f64, lambda: f64) -> f64 {
    let prefactor = lambda / 2.0 * ((lambda / 2.0) * (2.0 * mu + lambda * sigma.powi(2) - 2.0 * x)).exp();
    let erfc_part = erfc((mu + lambda * sigma.powi(2) - x) / (SQRT_2 * sigma));
    prefactor * erfc_part
}

/*
pub fn emg_cdf_range(lower_limit: f64, upper_limit: f64, mu: f64, sigma: f64, lambda: f64) -> f64 {
    let mut workspace = IntegrationWorkspace::new(1000).expect("IntegrationWorkspace::new failed");

    let (result, _) = workspace.qags(
        |x| emg_function(x, mu, sigma, lambda),
        lower_limit,
        upper_limit,
        0.0,
        1e-7,
        1000,
    )
        .unwrap();

    result
}
*/

pub fn emg_cdf_range(lower_limit: f64, upper_limit: f64, mu: f64, sigma: f64, lambda: f64, n_steps: Option<usize>) -> f64 {
    let n_steps = n_steps.unwrap_or(1000);
    integrate(|x| emg(x, mu, sigma, lambda), lower_limit, upper_limit, n_steps)
}

pub fn calculate_bounds_emg(mu: f64, sigma: f64, lambda: f64, step_size: f64, target: f64, lower_start: f64, upper_start: f64, n_steps: Option<usize>) -> (f64, f64) {
    assert!(0.0 <= target && target <= 1.0, "target must be in [0, 1]");

    let lower_initial = mu - lower_start * sigma;
    let upper_initial = mu + upper_start * sigma;

    let steps = ((upper_initial - lower_initial) / step_size).round() as usize;
    let search_space: Vec<f64> = (0..=steps).map(|i| lower_initial + i as f64 * step_size).collect();

    let calc_cdf = |low: usize, high: usize| -> f64 {
        emg_cdf_range(search_space[low], search_space[high], mu, sigma, lambda, n_steps)
    };

    // Binary search for cutoff values
    let (mut low, mut high) = (0, steps);
    while low < high {
        let mid = low + (high - low) / 2;
        if calc_cdf(0, mid) < target {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    let upper_cutoff_index = low;

    low = 0;
    high = upper_cutoff_index;
    while low < high {
        let mid = high - (high - low) / 2;
        let prob_mid_to_upper = calc_cdf(mid, upper_cutoff_index);

        if prob_mid_to_upper < target {
            high = mid - 1;
        } else {
            low = mid;
        }
    }
    let lower_cutoff_index = high;

    (search_space[lower_cutoff_index], search_space[upper_cutoff_index])
}

pub fn calculate_frame_occurrence_emg(retention_times: &[f64], rt: f64, sigma: f64, lambda_: f64, target_p: f64, step_size: f64, n_steps: Option<usize>) -> Vec<i32> {
    let (rt_min, rt_max) = calculate_bounds_emg(rt, sigma, lambda_, step_size, target_p, 20.0, 60.0, n_steps);

    // Finding the frame closest to rt_min
    let first_frame = retention_times.iter()
        .enumerate()
        .min_by(|(_, &a), (_, &b)| (a - rt_min).abs().partial_cmp(&(b - rt_min).abs()).unwrap())
        .map(|(idx, _)| idx + 1) // Rust is zero-indexed, so +1 to match Python's 1-indexing
        .unwrap_or(0); // Fallback in case of an empty slice

    // Finding the frame closest to rt_max
    let last_frame = retention_times.iter()
        .enumerate()
        .min_by(|(_, &a), (_, &b)| (a - rt_max).abs().partial_cmp(&(b - rt_max).abs()).unwrap())
        .map(|(idx, _)| idx + 1) // Same adjustment for 1-indexing
        .unwrap_or(0); // Fallback

    // Generating the range of frames
    (first_frame..=last_frame).map(|x| x as i32).collect()
}

pub fn calculate_frame_abundance_emg(time_map: &HashMap<i32, f64>, occurrences: &[i32], rt: f64, sigma: f64, lambda_: f64, rt_cycle_length: f64, n_steps: Option<usize>) -> Vec<f64> {
    let mut frame_abundance = Vec::new();

    for &occurrence in occurrences {
        if let Some(&time) = time_map.get(&occurrence) {
            let start = time - rt_cycle_length;
            let i = emg_cdf_range(start, time, rt, sigma, lambda_, n_steps);
            frame_abundance.push(i);
        }
    }

    frame_abundance
}

// retention_times: &[f64], rt: f64, sigma: f64, lambda_: f64
pub fn calculate_frame_occurrences_emg_par(retention_times: &[f64], rts: Vec<f64>, sigmas: Vec<f64>, lambdas: Vec<f64>, target_p: f64, step_size: f64, num_threads: usize, n_steps: Option<usize>) -> Vec<Vec<i32>> {
    let thread_pool = ThreadPoolBuilder::new().num_threads(num_threads).build().unwrap();
    let result = thread_pool.install(|| {
        rts.into_par_iter().zip(sigmas.into_par_iter()).zip(lambdas.into_par_iter())
            .map(|((rt, sigma), lambda)| {
                calculate_frame_occurrence_emg(retention_times, rt, sigma, lambda, target_p, step_size, n_steps)
            })
            .collect()
    });
    result
}

pub fn calculate_frame_abundances_emg_par(time_map: &HashMap<i32, f64>, occurrences: Vec<Vec<i32>>, rts: Vec<f64>, sigmas: Vec<f64>, lambdas: Vec<f64>, rt_cycle_length: f64, num_threads: usize, n_steps: Option<usize>) -> Vec<Vec<f64>> {
    let thread_pool = ThreadPoolBuilder::new().num_threads(num_threads).build().unwrap();
    let result = thread_pool.install(|| {
        occurrences.into_par_iter().zip(rts.into_par_iter()).zip(sigmas.into_par_iter()).zip(lambdas.into_par_iter())
            .map(|(((occurrences, rt), sigma), lambda)| {
                calculate_frame_abundance_emg(time_map, &occurrences, rt, sigma, lambda, rt_cycle_length, n_steps)
            })
            .collect()
    });
    result
}
