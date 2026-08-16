import logging

logger = logging.getLogger('nearcash')



def log_message(
    msg: str, level: str = "info", exc_info: bool = False, extra: dict = None
) -> None:
    _log_levels = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
        "exception": logger.exception,
    }
    if level not in _log_levels:
        # default to info level if the provided level is not valid
        _log_levels["info"](msg, exc_info=exc_info, extra=extra)
        return
    if level.lower() == "exception":
        # exception level should always log the stack trace
        exc_info = True
        msg.format(exc_info)
    _log_levels[level](msg, exc_info=exc_info, extra=extra)
    return
