import logging

LOG = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
LOG.addHandler(handler)
LOG.setLevel(logging.DEBUG)

