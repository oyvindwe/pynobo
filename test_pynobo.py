import pathlib
import unittest

from pynobo import (
    PynoboConnectionError,
    PynoboError,
    PynoboHandshakeError,
    PynoboValidationError,
    nobo,
)

class TestValidation(unittest.TestCase):

    def test_is_valid_datetime(self):
        self.assertTrue(nobo.API.is_valid_datetime("202404041800"))
        self.assertFalse(nobo.API.is_valid_datetime("2024040418001"))
        self.assertFalse(nobo.API.is_valid_datetime("20240404180"))
        self.assertFalse(nobo.API.is_valid_datetime("invalid"))

    def test_time_is_quarter(self):
        self.assertTrue(nobo.API.time_is_quarter("00"))
        self.assertTrue(nobo.API.time_is_quarter("15"))
        self.assertTrue(nobo.API.time_is_quarter("30"))
        self.assertTrue(nobo.API.time_is_quarter("45"))
        self.assertFalse(nobo.API.time_is_quarter("01"))
        self.assertFalse(nobo.API.time_is_quarter("59"))

    def test_validate_temperature(self):
        nobo.API.validate_temperature("20")
        nobo.API.validate_temperature(20)
        nobo.API.validate_temperature(7)
        nobo.API.validate_temperature(30)
        with self.assertRaises(TypeError):
            nobo.API.validate_temperature(0.0)
        with self.assertRaisesRegex(ValueError, "must be digits"):
            nobo.API.validate_temperature("foo")
        with self.assertRaisesRegex(ValueError, "Min temperature is 7"):
            nobo.API.validate_temperature(6)
        with self.assertRaisesRegex(ValueError, "Max temperature is 30"):
            nobo.API.validate_temperature(31)

    def test_validate_week_profile(self):
        nobo.API.validate_week_profile(['00000','12001','16000','00000','12001','16000','00000','12001','16000','00000','12001','16000','00000','12001','16000','00000','12001','16000','00000','12001','16000'])
        nobo.API.validate_week_profile(['00000','00000','00000','00000','00000','00000','00000'])
        nobo.API.validate_week_profile(['00000','00001','00002','00004','00000','00000','00000'])
        with self.assertRaisesRegex(ValueError, "must contain exactly 7 entries for midnight"):
            nobo.API.validate_week_profile(['00000','00000','00000','00000','00000','00000'])
        with self.assertRaisesRegex(ValueError, "must contain exactly 7 entries for midnight"):
            nobo.API.validate_week_profile(['00000','00000','00000','00000','00000','00000','00000','00000'])
        with self.assertRaisesRegex(ValueError, "invalid state"):
            nobo.API.validate_week_profile(['00003','00000','00000','00000','00000','00000','00000'])
        with self.assertRaisesRegex(ValueError, "not in whole quarters"):
            nobo.API.validate_week_profile(['00000','01231','00000','00000','00000','00000','00000','00000'])


class TestExceptionHierarchy(unittest.TestCase):

    def test_validation_error_raised_and_inherits_value_error(self):
        with self.assertRaises(PynoboValidationError):
            nobo.API.validate_temperature(6)
        # back-compat: callers catching ValueError still work
        with self.assertRaises(ValueError):
            nobo.API.validate_temperature(6)

    def test_all_errors_inherit_base(self):
        self.assertTrue(issubclass(PynoboConnectionError, PynoboError))
        self.assertTrue(issubclass(PynoboHandshakeError, PynoboError))
        self.assertTrue(issubclass(PynoboValidationError, PynoboError))
        self.assertTrue(issubclass(PynoboValidationError, ValueError))


class TestPyTypedMarker(unittest.TestCase):

    def test_py_typed_file_is_present_in_source(self):
        marker = pathlib.Path(__file__).parent / "pynobo" / "py.typed"
        self.assertTrue(marker.is_file(), f"{marker} is missing")


class TestConnectionStateAPI(unittest.TestCase):

    def _make_hub(self):
        return nobo('123', discover=False, synchronous=False)

    def test_initial_state_is_disconnected(self):
        hub = self._make_hub()
        events = []
        hub.register_connection_callback(lambda h, s: events.append(s))
        self.assertFalse(hub.connected)
        self.assertEqual(events, [])

    def test_transition_fires_callback_once(self):
        hub = self._make_hub()
        events = []
        hub.register_connection_callback(lambda h, s: events.append((h is hub, s)))
        hub._set_connected(True)
        self.assertTrue(hub.connected)
        self.assertEqual(events, [(True, True)])

    def test_transitions_are_idempotent(self):
        hub = self._make_hub()
        events = []
        hub.register_connection_callback(lambda h, s: events.append(s))
        hub._set_connected(True)
        hub._set_connected(True)
        hub._set_connected(False)
        hub._set_connected(False)
        self.assertEqual(events, [True, False])

    def test_deregister_stops_callback(self):
        hub = self._make_hub()
        events = []
        cb = lambda h, s: events.append(s)
        hub.register_connection_callback(cb)
        hub._set_connected(True)
        hub.deregister_connection_callback(cb)
        hub._set_connected(False)
        self.assertEqual(events, [True])

    def test_callback_exception_does_not_break_dispatch(self):
        hub = self._make_hub()
        events = []
        def boom(h, s):
            raise RuntimeError("boom")
        hub.register_connection_callback(boom)
        hub.register_connection_callback(lambda h, s: events.append(s))
        hub._set_connected(True)
        self.assertEqual(events, [True])
        self.assertTrue(hub.connected)


if __name__ == '__main__':
    unittest.main()
