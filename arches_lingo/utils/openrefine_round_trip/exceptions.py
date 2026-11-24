class RoundTripRequestError(Exception):
    """A worksheet or match-link request the caller got wrong; its message is
    safe to send back.

    Kept apart from ValueError so a bug while reading or validating a file is
    never reported to the editor as a problem with their request.
    """
