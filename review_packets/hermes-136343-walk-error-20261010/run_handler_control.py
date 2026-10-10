"""Counterfactual control only; preserves exact-owner source file unchanged."""
import unittest
from unittest.mock import patch
import test_walk_error
subject = test_walk_error.subject
original_walk = subject.os.walk

def propagate(error):
    raise error

def checked_walk(top, *args, **kwargs):
    kwargs['onerror'] = propagate
    return original_walk(top, *args, **kwargs)

with patch.object(subject.os, 'walk', side_effect=checked_walk):
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_walk_error))
raise SystemExit(not outcome.wasSuccessful())
