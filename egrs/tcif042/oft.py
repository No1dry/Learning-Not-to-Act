"""Task042 uses the original single observation preparation and encode/decode."""
from egrs.task_control.oft import Prediction, decode
from egrs.task_control.oft import prediction as shared_prediction


def prediction(policy, item, *, modules=None):
    controller = getattr(policy, '_tcif042', None)
    if controller is None or not callable(getattr(controller, 'forward', None)):
        raise ValueError('Task042 prediction requires the installed TCIF attention controller')
    return shared_prediction(policy, item, modules=modules, forward=controller.forward)
