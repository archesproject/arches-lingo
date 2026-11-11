class ReconciliationRequestError(Exception):
    """A request the caller got wrong; its message is safe to send back.

    Kept apart from ValueError so a bug inside the service is never reported
    to an anonymous caller as their own bad request.
    """
