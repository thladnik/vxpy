from vxpy.core import logger


def run_process(target, **kwargs):

    logger.setup_log_queue(kwargs.get('_log_queue'))
    log = logger.getLogger(target.name)
    logger.write = lambda lvl, msg: log.info(msg)
    logger.debug = log.debug
    logger.info = log.info
    logger.warning = log.warning
    logger.error = log.error

    logger.setup_log_history(kwargs.get('_log_history'))

    local_module = target(**kwargs)