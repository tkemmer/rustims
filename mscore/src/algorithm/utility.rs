extern crate rgsl;

use rgsl::{IntegrationWorkspace, error::erfc, error::erf};
use std::f64::consts::SQRT_2;

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

pub fn calculate_bounds_emg(mu: f64, sigma: f64, lambda: f64, step_size: f64, target: f64, lower_start: f64, upper_start: f64) -> (f64, f64) {
    assert!(0.0 <= target && target <= 1.0, "target must be in [0, 1]");

    let lower_initial = mu - lower_start * sigma;
    let upper_initial = mu + upper_start * sigma;

    // Create the search space
    let steps = ((upper_initial - lower_initial) / step_size).round() as usize;
    let search_space: Vec<f64> = (0..=steps).map(|i| lower_initial + i as f64 * step_size).collect();

    // Define a local closure to calculate the CDF over a given range for convenience
    let calc_cdf = |low: usize, high: usize| -> f64 {
        emg_cdf_range(search_space[low], search_space[high], mu, sigma, lambda)
    };

    // Binary search for the upper cutoff value, starting from mu to upper_initial
    let (mut low, mut high) = (0, steps);
    while low < high {
        let mid = low + (high - low) / 2;
        if calc_cdf(0, mid) < target {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    let upper_cutoff = search_space[low.min(steps)];

    // Reset for binary search for the lower cutoff value
    low = 0;
    high = steps;
    while low < high {
        let mid = low + (high - low) / 2;
        // This time, we're interested in the interval from this midpoint to the upper cutoff.
        let prob_mid_to_upper = emg_cdf_range(search_space[mid], upper_cutoff, mu, sigma, lambda);

        // Check if the cumulative probability from mid to the upper cutoff is sufficient.
        if prob_mid_to_upper > target {
            high = mid; // We need to move towards the start of the array, as we've exceeded the target.
        } else {
            if mid == steps { break; } // Prevents going out of bounds
            low = mid + 1; // Not enough cumulative probability, move towards the end.
        }
    }
    let lower_cutoff = if low == 0 { search_space[low] } else { search_space[low-1] };

    (lower_cutoff, upper_cutoff)
}