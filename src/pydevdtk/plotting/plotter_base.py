import time

import matplotlib
import matplotlib.pyplot as plt


class Plotter:
    """
    Base class for plotting. Represents a plotter object that continuously
    updates and redraws figures based on incoming data.
    User should subclass this class and implement the  `init` method to create
    the figure and its artists and `process_data_queue` method to update the
    artists based on the incoming data.

    The `add_figure_and_artists` method is used to add a figure and its artists
    to the plotter and mark them as animated (changing as opposed to the
    background).
    """

    def __call__(
        self, cmd_queue, data_queue, stop_event, plot_closed_event, fps=None
    ):
        """
        Call method that continuously processes the data and commands.
        """
        self.cmd_queue = cmd_queue
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.plot_closed_event = plot_closed_event
        self.figs = []
        self.axs = {}
        self.event_processing = False
        self.init()
        if len(self.figs) == 0:
            raise RuntimeError(
                "No figure added, "
                "ensure `add_figure` is called at least once in `init`"
            )
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

    def init(self):
        """
        Initializes the plotter. Should be overridden in a subclass.
        """
        raise NotImplementedError("init method not implemented")

    def process_data_queue(self):
        """
        Processes the data queue. Should be overridden in a subclass.
        """
        raise NotImplementedError("process_data_queue method not implemented")

    def process_cmd_queue(self):
        """
        Processes the command queue. If a None command is received, the
        plotting is stopped.
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

    def add_figure_and_artists(self, fig, artists):
        """
        Adds a figure and its artists to the plotter. The background of the
        figure is saved for updates.
        """
        fig.canvas.draw()
        bg = fig.canvas.copy_from_bbox(fig.bbox)
        self.figs.append([fig, bg, artists])
        fig.canvas.mpl_connect("draw_event", self._on_draw)
        # exclude artists from regular redraw
        for artist in artists:
            artist.set_animated(True)

    def process_events(self):
        """
        Process the events. If the plot is not being shown, the
        `plot_closed_event` is set.
        """
        if self.event_processing:
            is_any_plot_present = False
            for fig, _, _ in self.figs:
                if plt.fignum_exists(fig.number):
                    is_any_plot_present = True
                    fig.canvas.flush_events()
            if not is_any_plot_present:
                self.plot_closed_event.set()

    def update_figures(self):
        """
        Update the figures based on the incoming data.
        """
        for fig, bg, artists in self.figs:
            fig.canvas.restore_region(bg)
            for artist in artists:
                fig.draw_artist(artist)
            fig.canvas.blit(fig.bbox)

    def _on_draw(self, event: matplotlib.backend_bases.Event):
        """
        Callback method that is called when a figure is redrawn.
        """
        if event is not None:
            bg = event.canvas.copy_from_bbox(event.canvas.figure.bbox)
            i_fig = next(
                i
                for i, (fig, _, _) in enumerate(self.figs)
                if fig == event.canvas.figure
            )
            self.figs[i_fig][1] = bg

    def show(self):
        """
        Display the figures. The background of the figures is saved and the
        `plot_closed_event` is cleared.
        """
        plt.show(block=False)
        for i_fig, (fig, _, _) in enumerate(self.figs):
            bg = fig.canvas.copy_from_bbox(fig.bbox)
            fig.canvas.mpl_connect("draw_event", self._on_draw)
            self.figs[i_fig][1] = bg
        self.plot_closed_event.clear()
        self.event_processing = True

    def close(self):
        """
        Close all the figures.
        """
        self.event_processing = False
        plt.close("all")
