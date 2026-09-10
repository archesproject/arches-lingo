"""Progress reporting for the long streaming passes of the AAT load.

Reading the Getty export means streaming well over a gigabyte of NTriples, and
without a total to measure against a line counter cannot say how much is left.
The archive records each member's uncompressed size, so progress is tracked by
bytes consumed, which yields an estimated time the way the core reindex command
does.
"""

import sys

import pyprind

PROGRESS_UPDATE_BYTES = 4 * 1024 * 1024


def progress_reporting_is_useful(output_stream=None):
    """Progress bars redraw with carriage returns, which is noise in a log."""
    output_stream = output_stream or sys.stdout
    return hasattr(output_stream, "isatty") and output_stream.isatty()


def iterate_with_progress(
    items, total, title, show_progress=True, output_stream=None, step=1
):
    """Yield items from a sized sequence, reporting progress and an estimate.

    `step` is how much of the total each item represents, so a loop over
    batches can report progress in rows rather than in batches.
    """
    output_stream = output_stream or sys.stdout
    progress_bar = None
    if show_progress and total:
        progress_bar = pyprind.ProgBar(
            total,
            bar_char="█",
            title=title,
            stream=output_stream,
            track_time=True,
        )

    reported = 0
    for item in items:
        yield item
        if progress_bar is not None:
            advance = min(step, total - reported)
            if advance > 0:
                progress_bar.update(advance)
                reported += advance

    if progress_bar is not None and reported < total:
        progress_bar.update(total - reported)


def stream_lines_with_progress(
    line_streams, total_bytes, title, show_progress=True, output_stream=None
):
    """Yield lines from several streams, reporting progress by bytes consumed.

    The bar advances in blocks rather than per line: the streams carry millions
    of lines, and redrawing for each one costs more than the parsing does.
    """
    output_stream = output_stream or sys.stdout
    progress_bar = None
    if show_progress and total_bytes:
        progress_bar = pyprind.ProgBar(
            total_bytes,
            bar_char="█",
            title=title,
            stream=output_stream,
            track_time=True,
        )

    bytes_since_update = 0
    bytes_reported = 0
    for line_stream in line_streams:
        for raw_line in line_stream:
            if progress_bar is not None:
                bytes_since_update += len(raw_line)
                if bytes_since_update >= PROGRESS_UPDATE_BYTES:
                    progress_bar.update(bytes_since_update)
                    bytes_reported += bytes_since_update
                    bytes_since_update = 0
            yield raw_line

    if progress_bar is not None:
        # Settle the bar on 100%: block updates leave a remainder, and a short
        # final read would otherwise leave it visibly unfinished.
        remaining_bytes = max(total_bytes - bytes_reported, 0)
        if remaining_bytes:
            progress_bar.update(remaining_bytes)
