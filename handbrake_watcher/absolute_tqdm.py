from tqdm import tqdm


class AbosluteTqdm(tqdm):
    def update_to(self, n):
        """
        Update the progress bar in-place, useful for setting
        the state of the progress bar manually.
        E.g.:
        >>> t = tqdm(total=100) # Initialise
        >>> t.update_to(50)     # progressbar is now half-way complete
        >>> t.close()
        The last line is highly recommended, but possibly not necessary if
        `t.update_to()` will be called in such a way that `total` will be
        exactly reached and printed.

        Parameters
        ----------
        n  : int or float
            Set the internal counter of iterations.
            f using float, consider specifying `{n:.3f}`
            or similar in `bar_format`, or specifying `unit_scale`.

        """
        self.n = n
        self.refresh()
