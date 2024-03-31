import multiprocessing as mp
import warnings

from .plotter import Plotter
from .plotter_base import Plotter as PlotterBase


class PlotterManager:
    def __init__(self, plotter: Plotter | PlotterBase, fps: int | None = None):
        self.cmd_queue = mp.Queue()
        self.data_queue = mp.Queue()
        self.stop_event = mp.Event()
        self.is_plot_closed = mp.Event()
        self.plotter_worker = plotter
        self.process = mp.Process(
            target=self.plotter_worker,
            args=(
                self.cmd_queue,
                self.data_queue,
                self.stop_event,
                self.is_plot_closed,
                fps,
            ),
        )
        self.process.start()

    def show(self):
        self.cmd_queue.put(("show",))

    def close(self):
        self.cmd_queue.put(("close",))

    def stop(self):
        self.stop_event.set()
        if self.process is not None and self.process.is_alive():
            self.cmd_queue.put(None)
            self.data_queue.put(None)
            self.process.join(timeout=5)
            if self.process.exitcode is None:
                warnings.warn("Couldn't stop plotter window process")

    def is_alive(self) -> bool:
        return self.process.is_alive()

    def is_shown(self) -> bool:
        return not self.is_plot_closed.is_set()

    def add_data(self, data):
        self.data_queue.put(data)

    def create_figure(
        self, fig_id: str, grid_rows: int = 1, grid_cols: int = 1, **kwargs
    ):
        grid_size = (grid_rows, grid_cols)
        self.cmd_queue.put(("create_fig", fig_id, kwargs, grid_size))

    def create_axis(
        self,
        axis_id: str,
        fig_id: str,
        i_row: int,
        i_col: int,
        num_rows: int = 1,
        num_cols: int = 1,
    ):
        self.cmd_queue.put(
            (
                "create_axis",
                axis_id,
                fig_id,
                (i_row, i_col),
                (num_rows, num_cols),
            )
        )

    def modify_axis(
        self,
        axis_id: str,
        xlim: list[float, float] | None = None,
        ylim: list[float, float] | None = None,
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
        xticks: list[float] | None = None,
        xticklabels: list[str] | None = None,
        yticks: list[float] | None = None,
        yticklabels: list[str] | None = None,
        legend: bool = False,
    ):
        self.cmd_queue.put(
            (
                "modify_axis",
                axis_id,
                xlim,
                ylim,
                title,
                xlabel,
                ylabel,
                xticks,
                xticklabels,
                yticks,
                yticklabels,
                legend,
            )
        )

    def create_line_plot(self, artist_id, axis_id, size, **kwargs):
        self.cmd_queue.put(
            ("create_line_plot", artist_id, axis_id, size, kwargs)
        )

    def create_scatter_plot(self, artist_id, axis_id, num_points, **kwargs):
        self.cmd_queue.put(
            ("create_scatter_plot", artist_id, axis_id, num_points, kwargs)
        )

    def create_bar_plot(self, artist_id, axis_id, num_bars, **kwargs):
        self.cmd_queue.put(
            ("create_bar_plot", artist_id, axis_id, num_bars, kwargs)
        )

    def create_image_plot(
        self, artist_id, axis_id, img_shape, cbar=False, **kwargs
    ):
        self.cmd_queue.put(
            ("create_image_plot", artist_id, axis_id, img_shape, cbar, kwargs)
        )
