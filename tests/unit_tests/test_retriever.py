from tests.filepath import ABSOLUTE_PATH
import sys, os

sys.path.append(ABSOLUTE_PATH)
from mooseagent.retrieval import get_local_retriever


get_local_retriever(os.path.join(ABSOLUTE_PATH, "database"))
