import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(tries=4, delay=3, backoff=2):
  """
  Retry decorator with exponential backoff.
  """
  def deco_retry(f):
    @wraps(f)
    def f_retry(*args, **kwargs):
      mtries, mdelay = tries, delay
      while mtries > 1:
        try:
          return f(*args, **kwargs)
        except Exception as e:
          logger.warning(f"{e}, Retrying in {mdelay} seconds...")
          time.sleep(mdelay)
          mtries -= 1
          mdelay *= backoff
      return f(*args, **kwargs)
    return f_retry
  return deco_retry
