from vxpy.core import logging


def run_process(target, **kwargs):

    logging.setup_log_queue(kwargs.get('_log_queue'))
    log = logging.getLogger(target.name)
    logging.write = lambda lvl, msg: log.info(msg)
    logging.debug = log.debug
    logging.info = log.info
    logging.warning = log.warning
    logging.error = log.error

    logging.setup_log_history(kwargs.get('_log_history'))

    local_module = target(**kwargs)