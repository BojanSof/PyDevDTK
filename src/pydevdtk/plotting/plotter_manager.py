import multiprocessing as mp
import warnings

from .plotter import Plotter
from .plotter_base import Plotter as PlotterBase


class PlotterManager:
    """
    Manager for the plotter.

    Parameters
    ----------
    plotter : Plotter or PlotterBase
        The plotter object that will be used to create figures and artists.
    fps : int or None, optional
        The frames per second at which the plotter updates the figures.
    """

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
        """Show the plotter window."""
        self.cmd_queue.put(("show",))

    def close(self):
        """Close the plotter window."""
        self.cmd_queue.put(("close",))

    def stop(self):
        """Stop the plotter process."""
        self.stop_event.set()
        if self.process is not None and self.process.is_alive():
            self.cmd_queue.put(None)
            self.data_queue.put(None)
            self.process.join(timeout=5)
            if self.process.exitcode is None:
                warnings.warn("Couldn't stop plotter window process")

    def is_alive(self) -> bool:
        """Check if the plotter process is alive."""
        return self.process.is_alive()

    def is_shown(self) -> bool:
        """Check if the plotter window is shown."""
        return not self.is_plot_closed.is_set()

    def add_data(self, data: dict[str]) -> None:
        """
        Add data to the plotter's data queue.

        Parameters
        ----------
        data : dict[str]
            Dictionary of data, where the keys are the artist ids.
        """
        self.data_queue.put(data)

    def create_figure(
        self,
        fig_id: str,
        grid_rows: int = 1,
        grid_cols: int = 1,
        **kwargs,
    ) -> None:
        """
        Create a figure with the given ID, number of rows and columns, and
        keyword arguments.

        Parameters
        ----------
        fig_id : str
            The ID of the figure.
        grid_rows : int, optional
            The number of rows in the grid. Default is 1.
        grid_cols : int, optional
            The number of columns in the grid. Default is 1.
        kwargs
            Keyword arguments to pass to the figure constructor.
            Look-up the docstring for `matplotlib.figure.Figure`.
        """
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
    ) -> None:
        """
        Create an axis with the given ID, figure ID, and position in the grid.

        Parameters
        ----------
        axis_id : str
            The ID of the axis.
        fig_id : str
            The ID of the figure.
        i_row : int
            The row index of the axis in the grid.
        i_col : int
            The column index of the axis in the grid.
        num_rows : int, optional
            The number of rows in the grid. Default is 1.
        num_cols : int, optional
            The number of columns in the grid. Default is 1.
        """
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
        """
        Modify the axis with the given ID.

        Parameters
        ----------
        axis_id : str
            The ID of the axis.
        xlim : Tuple[float, float], optional
            The x-axis limits. Default is None.
        ylim : Tuple[float, float], optional
            The y-axis limits. Default is None.
        title : str, optional
            The title of the axis. Default is None.
        xlabel : str, optional
            The label for the x-axis. Default is None.
        ylabel : str, optional
            The label for the y-axis. Default is None.
        xticks : List[float], optional
            The locations of the tick marks on the x-axis. Default is None.
        xticklabels : List[str], optional
            The labels for the tick marks on the x-axis. Default is None.
        yticks : List[float], optional
            The locations of the tick marks on the y-axis. Default is None.
        yticklabels : List[str], optional
            The labels for the tick marks on the y-axis. Default is None.
        legend : bool, optional
            Whether to show the legend. Default is False.
        """
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

    def create_line_plot(
        self,
        artist_id: str,
        axis_id: str,
        size: int,
        **kwargs,
    ) -> None:
        """
        Create a line plot.

        Parameters
        ----------
        artist_id : str
            The ID of the artist.
        axis_id : str
            The ID of the axis.
        size : int
            The number of points on the line plot.
        kwargs : Any
            Additional keyword arguments to pass to the plot method.
            Look-up the docstring for `matplotlib.Axes.plot` method.
        """
        self.cmd_queue.put(
            ("create_line_plot", artist_id, axis_id, size, kwargs)
        )

    def create_scatter_plot(
        self,
        artist_id: str,
        axis_id: str,
        num_points: int,
        **kwargs,
    ) -> None:
        """
        Create a scatter plot with the given ID, axis ID, number of points, and
        keyword arguments.

        Parameters
        ----------
        artist_id : str
            The ID of the artist.
        axis_id : str
            The ID of the axis.
        num_points : int
            The number of points in the scatter plot.
        kwargs
            Additional keyword arguments to pass to the scatter method.
            Look-up the docstring for `matplotlib.Axes.scatter` method.
        """
        self.cmd_queue.put(
            ("create_scatter_plot", artist_id, axis_id, num_points, kwargs)
        )

    def create_bar_plot(
        self,
        artist_id: str,
        axis_id: str,
        num_bars: int,
        **kwargs,
    ) -> None:
        """
        Create a bar plot.

        Parameters
        ----------
        artist_id : str
            The ID of the artist.
        axis_id : str
            The ID of the axis.
        num_bars : int
            The number of bars in the bar plot.
        kwargs
            Additional keyword arguments to pass to the bar method.
            Look-up the docstring for `matplotlib.Axes.bar` method.
        """
        self.cmd_queue.put(
            ("create_bar_plot", artist_id, axis_id, num_bars, kwargs)
        )

    def create_image_plot(
        self,
        artist_id: str,
        axis_id: str,
        img_shape: tuple[int, int],
        cbar: bool = False,
        **kwargs,
    ) -> None:
        """
        Create an image plot with the given ID, axis ID, image shape, and
        keyword arguments.

        Parameters
        ----------
        artist_id : str
            The ID of the artist.
        axis_id : str
            The ID of the axis.
        img_shape : tuple[int, int]
            The shape of the image.
        cbar : bool, optional
            Whether to include colorbar, by default False.
        kwargs
            Additional keyword arguments to pass to the imshow method.
            Look-up the docstring for `matplotlib.Axes.imshow` method.
        """
        self.cmd_queue.put(
            ("create_image_plot", artist_id, axis_id, img_shape, cbar, kwargs)
        )
