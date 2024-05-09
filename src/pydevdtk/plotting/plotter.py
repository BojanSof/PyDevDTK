import enum
import time
import threading
import queue

import matplotlib.artist
import matplotlib.collections
import matplotlib.container
import numpy as np
from numpy.typing import ArrayLike
import matplotlib

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt  # noqa


class PlotType(enum.Enum):
    """
    Suported types of plots.
    """

    Line = (enum.auto(),)
    Scatter = (enum.auto(),)
    Bar = (enum.auto(),)
    Text = (enum.auto(),)
    Image = enum.auto()


class Plotter:
    """
    Class for plotting data in real-time.
    """

    def __call__(
        self,
        cmd_queue: queue.Queue,
        data_queue: queue.Queue,
        stop_event: threading.Event,
        plot_closed_event: threading.Event,
        fps: float | None = None,
    ):
        """
        Main function for plotting.

        Parameters
        ----------
        cmd_queue : queue.Queue
            Queue for receiving plotting commands.
        data_queue : queue.Queue
            Queue for receiving data to be plotted.
        stop_event : threading.Event
            Event to stop plotting.
        plot_closed_event : threading.Event
            Event indicating plot window is closed.
        fps : float | None, optional
            Frames per second for plotting, by default None.
        """
        self.cmd_queue = cmd_queue
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.plot_closed_event = plot_closed_event
        self.figs = {}
        self.axs = {}
        self.artists = {}
        self.bgs = {}
        self.event_processing = False
        t_start = time.time()
        while not self.stop_event.is_set():
            self.process_cmd_queue()
            self.process_data_queue()
            self.process_events()
            if fps is not None and time.time() - t_start < 1 / fps:
                continue
            self.update_figures()
            t_start = time.time()

        while self.cmd_queue.get() is not None:
            self.cmd_queue.get()
        while self.data_queue.get() is not None:
            self.data_queue.get()

    def process_cmd_queue(self):
        """
        Process commands in the command queue.
        """
        while not self.cmd_queue.empty():
            cmd = self.cmd_queue.get()
            if cmd is None:
                # stop
                pass
            if cmd[0] == "show":
                self.show()
            elif cmd[0] == "close":
                self.close()
            elif cmd[0] == "create_fig":
                fig_id = cmd[1]
                kwargs = cmd[2]
                nrows, ncols = cmd[3]
                self.create_figure(fig_id, nrows, ncols, **kwargs)
            elif cmd[0] == "create_axis":
                ax_id = cmd[1]
                fig_id = cmd[2]
                irow, icol = cmd[3]
                nrows, ncols = cmd[4]
                self.create_axis(ax_id, fig_id, irow, icol, nrows, ncols)
            elif cmd[0] == "modify_axis":
                ax_id = cmd[1]
                xlim = cmd[2]
                ylim = cmd[3]
                title = cmd[4]
                xlabel = cmd[5]
                ylabel = cmd[6]
                xticks = cmd[7]
                xticklabels = cmd[8]
                yticks = cmd[9]
                yticklabels = cmd[10]
                legend = cmd[11]
                self.modify_axis(
                    ax_id,
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
            elif cmd[0] == "create_line_plot":
                artist_id = cmd[1]
                ax_id = cmd[2]
                size = cmd[3]
                kwargs = cmd[4]
                self.create_line_plot(artist_id, ax_id, size, **kwargs)
            elif cmd[0] == "create_scatter_plot":
                artist_id = cmd[1]
                ax_id = cmd[2]
                num_points = cmd[3]
                kwargs = cmd[4]
                self.create_scatter_plot(
                    artist_id, ax_id, num_points, **kwargs
                )
            elif cmd[0] == "create_bar_plot":
                artist_id = cmd[1]
                ax_id = cmd[2]
                num_bars = cmd[3]
                kwargs = cmd[4]
                self.create_bar_plot(artist_id, ax_id, num_bars, **kwargs)
            elif cmd[0] == "create_image_plot":
                artist_id = cmd[1]
                ax_id = cmd[2]
                img_shape = cmd[3]
                cbar = cmd[4]
                kwargs = cmd[5]
                self.create_image_plot(
                    artist_id, ax_id, img_shape, cbar, **kwargs
                )

    def process_data_queue(self):
        """
        Process data in the data queue.
        """
        while not self.data_queue.empty():
            data = self.data_queue.get()
            for artist_id, val in data.items():
                artist, type = self.artists[artist_id]
                if type == PlotType.Line:
                    self.update_line_plot(artist, val)
                elif type == PlotType.Scatter:
                    self.update_scatter_plot(artist, val)
                elif type == PlotType.Bar:
                    self.update_bar_plot(artist, val)
                elif type == PlotType.Image:
                    self.update_image_plot(artist, val)

    def process_events(self):
        """
        Process GUI events.
        """
        if self.event_processing:
            is_any_plot_present = False
            for fig, _, _ in self.figs.values():
                if plt.fignum_exists(fig.number):
                    is_any_plot_present = True
                    fig.canvas.flush_events()
            if not is_any_plot_present:
                self.plot_closed_event.set()

    def update_figures(self):
        """
        Update figures with new data.
        """
        for fig_id, (fig, _, artists) in self.figs.items():
            bg = self.bgs[fig_id]
            fig.canvas.restore_region(bg)
            for artist in artists:
                fig.draw_artist(artist)
            fig.canvas.blit(fig.bbox)

    def _on_draw(self, event: matplotlib.backend_bases.Event):
        """
        Event handler for draw events.

        Parameters
        ----------
        event : matplotlib.backend_bases.Event
            Event object.
        """
        if event is not None:
            bg = event.canvas.copy_from_bbox(event.canvas.figure.bbox)
            fig_id = [
                id
                for id, (fig, _, _) in self.figs.items()
                if fig == event.canvas.figure
            ][0]
            self.bgs[fig_id] = bg

    def show(self):
        """
        Show the plot.
        """
        plt.show(block=False)
        for fig_id, (fig, _, _) in self.figs.items():
            bg = fig.canvas.copy_from_bbox(fig.bbox)
            self.bgs[fig_id] = bg
            fig.canvas.mpl_connect("draw_event", self._on_draw)
        self.plot_closed_event.clear()
        self.event_processing = True

    def close(self):
        """
        Close the plot.
        """
        self.event_processing = False
        plt.close("all")

    def create_figure(self, fig_id: str, nrows: int, ncols: int, **kwargs):
        """
        Create a new figure.

        Parameters
        ----------
        fig_id : str
            Unique identifier for the figure.
        nrows : int
            Number of rows in the figure grid.
        ncols : int
            Number of columns in the figure grid.
        kwargs
            Additional keyword arguments for creating the figure.
        """
        fig = plt.figure(constrained_layout=True, **kwargs)
        gs = fig.add_gridspec(nrows, ncols)
        artists = []
        self.figs[fig_id] = (fig, gs, artists)

    def create_axis(
        self,
        ax_id: str,
        fig_id: str,
        irow: int,
        icol: int,
        nrows: int,
        ncols: int,
    ):
        """
        Create a new axis.

        Parameters
        ----------
        ax_id : str
            Unique identifier for the axis.
        fig_id : str
            Unique identifier for the figure containing the axis.
        irow : int
            Row index of the axis in the figure grid.
        icol : int
            Column index of the axis in the figure grid.
        nrows : int
            Total number of rows in the figure grid.
        ncols : int
            Total number of columns in the figure grid.
        """
        fig, gs, _ = self.figs[fig_id]
        ax = fig.add_subplot(gs[irow : irow + nrows, icol : icol + ncols])
        self.axs[ax_id] = ax

    def modify_axis(
        self,
        ax_id: str,
        xlim: tuple[float, float],
        ylim: tuple[float, float],
        title: str,
        xlabel: str,
        ylabel: str,
        xticks: ArrayLike,
        xticklabels: ArrayLike,
        yticks: ArrayLike,
        yticklabels: ArrayLike,
        legend: bool,
    ):
        """
        Modify an existing axis.

        Parameters
        ----------
        ax_id : str
            Unique identifier for the axis.
        xlim : tuple[float, float]
            Tuple containing the x-axis limits.
        ylim : tuple[float, float]
            Tuple containing the y-axis limits.
        title : str
            Title of the axis.
        xlabel : str
            Label for the x-axis.
        ylabel : str
            Label for the y-axis.
        xticks : array-like
            Positions of the x-axis ticks.
        xticklabels : array-like
            Labels for the x-axis ticks.
        yticks : array-like
            Positions of the y-axis ticks.
        yticklabels : array-like
            Labels for the y-axis ticks.
        legend : bool
            Whether to display a legend on the axis.
        """
        ax = self.axs[ax_id]
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if xticks is not None:
            ax.set_xticks(xticks, xticklabels)
        if yticks is not None:
            ax.set_yticks(yticks, yticklabels)
        if legend:
            ax.legend(loc="upper left")

    def create_line_plot(
        self, artist_id: str, ax_id: str, size: int, **kwargs
    ):
        """
        Create a line plot.

        Parameters
        ----------
        artist_id : str
            Unique identifier for the plot.
        ax_id : str
            Unique identifier for the axis containing the plot.
        size : int
            Size of the data array for the plot.
        kwargs
            Additional keyword arguments for creating the plot.
        """
        ax = self.axs[ax_id]
        line = ax.plot(np.full(size, np.nan), **kwargs)[0]
        self.add_artist(artist_id, ax_id, line, PlotType.Line)

    def create_scatter_plot(
        self, artist_id: str, ax_id: str, num_points: int, **kwargs
    ):
        """
        Create a scatter plot.

        Parameters
        ----------
        artist_id : str
            Unique identifier for the plot.
        ax_id : int
            Unique identifier for the axis containing the plot.
        num_points : int
            Number of points in the scatter plot.
        kwargs
            Additional keyword arguments for creating the plot.
        """
        ax = self.axs[ax_id]
        points = ax.scatter(
            np.full(num_points, np.nan), np.full(num_points, np.nan), **kwargs
        )
        self.add_artist(artist_id, ax_id, points, PlotType.Scatter)

    def create_bar_plot(
        self, artist_id: str, ax_id: str, num_bars: int, **kwargs
    ):
        """
        Create a bar plot.

        Parameters
        ----------
        artist_id : str
            Unique identifier for the plot.
        ax_id : str
            Unique identifier for the axis containing the plot.
        num_bars : int
            Number of bars in the bar plot.
        kwargs
            Additional keyword arguments for creating the plot.
        """
        ax = self.axs[ax_id]
        bars = ax.bar(
            [i for i in range(num_bars)],
            [0 for _ in range(num_bars)],
            **kwargs,
        )
        self.add_artist(artist_id, ax_id, bars, PlotType.Bar)

    def create_image_plot(
        self,
        artist_id: str,
        ax_id: str,
        img_shape: tuple[int, int],
        cbar: bool,
        **kwargs,
    ):
        """
        Create an image plot.

        Parameters
        ----------
        artist_id : str
            Unique identifier for the plot.
        ax_id : str
            Unique identifier for the axis containing the plot.
        img_shape : tuple[int, int]
            Shape of the image data.
        cbar : bool
            Whether to display a colorbar.
        kwargs
            Additional keyword arguments for creating the plot.
        """
        ax = self.axs[ax_id]
        img = ax.imshow(np.full(img_shape, np.nan), **kwargs)
        if cbar:
            plt.colorbar(img, ax=ax)
        self.add_artist(artist_id, ax_id, img, PlotType.Image)

    def add_artist(
        self,
        artist_id: str,
        ax_id: str,
        artist: matplotlib.artist.Artist,
        type: PlotType,
    ):
        """
        Add an artist to the plot.

        Parameters
        ----------
        artist_id : str
            Unique identifier for the artist.
        ax_id : str
            Unique identifier for the axis containing the artist.
        artist : matplotlib.artist.Artist
            Artist object to be added to the plot.
        type : PlotType
            Type of the plot.
        """
        if type == PlotType.Bar:
            for real_artist in artist:
                real_artist.set_animated(True)
        else:
            artist.set_animated(True)
        fig_id = [
            id
            for id, (fig, _, _) in self.figs.items()
            if self.axs[ax_id] in fig.get_children()
        ][0]
        _, _, fig_artists = self.figs[fig_id]
        if type == PlotType.Bar:
            for real_artist in artist:
                fig_artists.append(real_artist)
        else:
            fig_artists.append(artist)
        self.artists[artist_id] = artist, type

    def update_line_plot(self, artist: matplotlib.lines.Line2D, val: float):
        """
        Update a line plot with new data.

        Parameters
        ----------
        artist : matplotlib.lines.Line2D
            Line plot artist.
        val : float
            New value for the plot.
        """
        values = artist.get_ydata()
        values = np.roll(values, -1)
        values[-1] = val
        artist.set_ydata(values)

    def update_scatter_plot(
        self,
        artist: matplotlib.collections.PathCollection,
        val: tuple[float, float],
    ):
        """
        Update a scatter plot with new data.

        Parameters
        ----------
        artist : matplotlib.collections.PathCollection
            Scatter plot artist.
        val : tuple[float, float]
            New x, y values for the plot.
        """
        values = artist.get_offsets()
        x_values = values[:, 0]
        y_values = values[:, 1]
        x_values = np.roll(x_values, -1)
        x_values[-1] = val[0]
        y_values = np.roll(y_values, -1)
        y_values[-1] = val[1]
        values = np.c_[x_values, y_values]
        artist.set_offsets(values)

    def update_bar_plot(
        self, artist: matplotlib.container.BarContainer, val: ArrayLike
    ):
        """
        Update a bar plot with new data.

        Parameters
        ----------
        artist : matplotlib.container.BarContainer
            Bar plot artist.
        val : array-like
            New heights for the bars.
        """
        bars = artist
        for bar, h in zip(bars, val):
            bar.set_height(h)

    def update_image_plot(
        self, artist: matplotlib.image.AxesImage, val: ArrayLike
    ):
        """
        Update an image plot with new data.

        Parameters
        ----------
        artist : matplotlib.image.AxesImage
            Image plot artist.
        val : array-like
            New image data.
        """
        artist.set_data(val)
