import multiprocessing as mp
import time

import numpy as np
from scipy import fft

from pydevdtk.plotting import Plotter, PlotterManager


def get_spectrum(fs, x, n_fft=None, log=False):
    n = x.size
    if n_fft is None:
        n_fft = int(2 ** np.ceil(np.log2(n)))
    x_spec = fft.fft(x, n_fft)
    x_spec = np.abs(x_spec)
    x_spec = x_spec / n
    n_keep = n_fft // 2 + 1
    x_spec = x_spec[0:n_keep]
    x_spec[1:-1] = 2 * x_spec[1:-1]
    f = np.linspace(0, fs / 2, n_keep)
    if log:
        eps = 1e-10
        x_spec[x_spec < eps] = eps
        x_spec = 20 * np.log10(x_spec)

    return f, x_spec


def generate_sine_signal(
    num_samples, amplitude, frequency, sample_rate, offset=0, phase=0
):
    if sample_rate <= 0:
        raise ValueError("Sample rate can't be negative or zero")
    if frequency <= 0:
        raise ValueError("Frequency can't be negative or zero")
    if frequency > sample_rate / 2:
        raise ValueError("Frequency is greater than sample_rate/2")
    time = np.arange(num_samples) / sample_rate
    signal = amplitude * np.sin(2 * np.pi * frequency * time + phase) + offset
    return signal


def generate_sinesweep(f_start, f_stop, amplitude, t_duration, fs):
    phi = 0
    f = f_start
    delta = 2 * np.pi * f / fs
    f_delta = (f_stop - f_start) / (fs * t_duration)
    samples = []
    for _ in range(int(fs * t_duration)):
        sample = amplitude * np.sin(phi)
        phi += delta
        f += f_delta
        delta = 2 * np.pi * f / fs
        samples.append(sample)
    return samples


def main():
    fs = 50
    num_samples = 50
    sin_wave = generate_sine_signal(num_samples, 1, 5, fs)
    cos_wave = generate_sine_signal(num_samples, 1, 2, fs, 0, np.pi / 2)
    sinesweep_wave = generate_sinesweep(0.1, 10, 1, 5, num_samples)
    i_sin = 0
    i_cos = 0
    i_sinswp = 0
    n_fft = 64
    n_spec_update = 1
    spec_buf = np.zeros(n_fft)
    spectrogram = np.full(
        (n_fft // 2 + 1, num_samples // n_spec_update), np.nan
    )
    i_spec_buf = 0
    i_spectrogram = 0
    plotter_manager = PlotterManager(Plotter())
    plotter_manager.create_figure("fig_demo", 3, 6, figsize=(12, 7))
    plotter_manager.create_axis("ax_line1", "fig_demo", 0, 0, 1, 2)
    plotter_manager.create_axis("ax_line2", "fig_demo", 1, 0, 1, 2)
    plotter_manager.create_axis("ax_bar", "fig_demo", 2, 0, 1, 2)
    plotter_manager.create_axis("ax_scat", "fig_demo", 0, 2, 2, 2)
    plotter_manager.create_axis("ax_line3", "fig_demo", 2, 2, 1, 2)
    plotter_manager.create_axis("ax_line4", "fig_demo", 2, 4, 1, 2)
    plotter_manager.create_axis("ax_img", "fig_demo", 0, 4, 2, 2)

    plotter_manager.create_line_plot("line1", "ax_line1", num_samples)
    plotter_manager.create_line_plot("line2", "ax_line2", num_samples)
    plotter_manager.create_bar_plot("bar", "ax_bar", 2)
    plotter_manager.create_line_plot(
        "line3_1", "ax_line3", num_samples, label="sin"
    )
    plotter_manager.create_line_plot(
        "line3_2", "ax_line3", num_samples, label="cos"
    )
    plotter_manager.create_scatter_plot("scat", "ax_scat", num_samples // 5)
    plotter_manager.create_line_plot("line4", "ax_line4", num_samples)
    plotter_manager.create_image_plot(
        "img",
        "ax_img",
        (n_fft // 2 + 1, num_samples // n_spec_update),
        cbar=True,
        vmin=0,
        vmax=1,
        aspect="auto",
        origin="lower",
    )

    plotter_manager.modify_axis(
        "ax_line1",
        [0, num_samples - 1],
        [-1.1, 1.1],
        ylabel="Sine",
        yticks=[-1, 0, 1],
    )
    plotter_manager.modify_axis(
        "ax_line2",
        [0, num_samples - 1],
        [-1.1, 1.1],
        ylabel="Cosine",
        yticks=[-1, 0, 1],
    )
    plotter_manager.modify_axis(
        "ax_bar",
        [-0.5, 1.5],
        [-1.1, 1.1],
        ylabel="Amplitudes",
        xticks=[0, 1],
        xticklabels=["Sine", "Cosine"],
    )
    plotter_manager.modify_axis(
        "ax_scat",
        [-1.1, 1.1],
        [-1.1, 1.1],
        xticks=[-1, 0, 1],
        yticks=[-1, 0, 1],
    )
    plotter_manager.modify_axis(
        "ax_line3",
        [0, num_samples - 1],
        [-1.1, 1.1],
        xlabel="SinCos",
        yticks=[-1, 0, 1],
        legend=True,
    )
    plotter_manager.modify_axis(
        "ax_line4",
        [0, num_samples - 1],
        [-1.1, 1.1],
        xlabel="Chirp",
        yticks=[-1, 0, 1],
    )
    plotter_manager.modify_axis("ax_img", [0, num_samples - 1], [0, 25])

    plotter_manager.show()
    while plotter_manager.is_shown():
        data = {
            "line1": sin_wave[i_sin],
            "line2": cos_wave[i_cos],
            "bar": [sin_wave[i_sin], cos_wave[i_cos]],
            "line3_1": sin_wave[i_sin],
            "line3_2": cos_wave[i_cos],
            "scat": [sin_wave[i_sin], cos_wave[i_cos]],
            "line4": sinesweep_wave[i_sinswp],
        }
        spec_buf[i_spec_buf] = sinesweep_wave[i_sinswp]
        if i_spec_buf % n_spec_update == 0:
            _, spec = get_spectrum(fs, spec_buf, n_fft)
            if i_spectrogram == spectrogram.shape[1] - 1:
                spectrogram[:, : spectrogram.shape[1] - 1] = spectrogram[:, 1:]
                spectrogram[:, i_spectrogram] = spec
            else:
                spectrogram[:, i_spectrogram] = spec
                i_spectrogram += 1
            data["img"] = spectrogram.copy()
        plotter_manager.add_data(data)
        i_sin += 1
        i_cos += 1
        i_sinswp += 1
        i_spec_buf += 1
        if i_sin >= len(sin_wave):
            i_sin = 0
        if i_cos >= len(cos_wave):
            i_cos = 0
        if i_sinswp >= len(sinesweep_wave):
            i_sinswp = 0
        if i_spec_buf >= num_samples:
            i_spec_buf -= n_spec_update
            spec_buf[: len(spec_buf) - n_spec_update] = spec_buf[
                n_spec_update:
            ]
        time.sleep(1 / 50)
    plotter_manager.stop()


if __name__ == "__main__":
    mp.freeze_support()
    main()
