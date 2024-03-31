import multiprocessing as mp
import time

import numpy as np
import matplotlib.pyplot as plt

from pydevdtk.plotting import PlotterManager, PlotterBase


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


# create custom PlotterBase
class Plotter(PlotterBase):
    def __init__(self, num_points=50):
        self.num_points = num_points

    def init(self):
        fig, axs = plt.subplots(3, 1, figsize=(8, 5), constrained_layout=True)

        self.y_sin = self.num_points * [np.nan]
        self.y_cos = self.num_points * [np.nan]
        self.y_rand = self.num_points * [np.nan]

        # create artists
        self.sin_artist = axs[0].plot(self.y_sin, color="C0")[0]
        self.cos_artist = axs[1].plot(self.y_cos, color="C1")[0]
        self.rand_artist = axs[2].plot(self.y_rand, color="C2")[0]

        # modify axes properties
        for ax in axs:
            ax.set_xlim([0, self.num_points - 1])
        for ax in axs:
            ax.set_xticks([0, self.num_points / 2, self.num_points])
        axs[0].set_title("sin")
        axs[1].set_title("cos")
        axs[2].set_title("rand")
        axs[0].set_ylim([-1.1, 1.1])
        axs[1].set_ylim([-1.1, 1.1])
        axs[2].set_ylim([999, 5001])

        # ensure this is called!
        self.add_figure_and_artists(
            fig, [self.sin_artist, self.cos_artist, self.rand_artist]
        )

    def process_data_queue(self):
        while not self.data_queue.empty():
            sin, cos, rand = self.data_queue.get()
            self.y_sin.append(sin)
            self.y_cos.append(cos)
            self.y_rand.append(rand)
            self.y_sin = self.y_sin[-self.num_points :]
            self.y_cos = self.y_cos[-self.num_points :]
            self.y_rand = self.y_rand[-self.num_points :]
            self.sin_artist.set_ydata(self.y_sin)
            self.cos_artist.set_ydata(self.y_cos)
            self.rand_artist.set_ydata(self.y_rand)


def main():
    fs = 50
    num_samples = 100
    sin_wave = generate_sine_signal(num_samples, 1, 5, fs)
    cos_wave = generate_sine_signal(num_samples, 1, 2, fs, 0, np.pi / 2)
    i_sin = 0
    i_cos = 0
    plotter_manager = PlotterManager(Plotter(num_samples))
    plotter_manager.show()
    while plotter_manager.is_shown():
        data = [
            sin_wave[i_sin],
            cos_wave[i_cos],
            np.random.randint(1000, 5000 + 1),
        ]
        plotter_manager.add_data(data)
        i_sin += 1
        i_cos += 1
        if i_sin >= len(sin_wave):
            i_sin = 0
        if i_cos >= len(cos_wave):
            i_cos = 0
        time.sleep(1 / 50)
    plotter_manager.stop()


if __name__ == "__main__":
    mp.freeze_support()
    main()
