import unittest

from chimera.embodiment import (
    BODY_FORMS, EmbodimentError, make_body_model, morph_progress,
    validate_body_model,
)


class EmbodimentDescriptorTests(unittest.TestCase):
    def test_supported_forms_and_schema(self):
        for form in BODY_FORMS:
            model = make_body_model(form, (0.6, 1.8, 0.3))
            self.assertEqual(model["schema_version"], 1)
            self.assertEqual(model["representation"], "analytic_sdf")
            self.assertEqual(model["to_form"], form)

    def test_transition_progress_uses_simulation_time(self):
        model = make_body_model(
            "quadruped", (0.8, 1.2, 0.5), start_time=4.0, duration=2.0
        )
        self.assertEqual(morph_progress(model, 3.0), 0.0)
        self.assertEqual(morph_progress(model, 4.0), 0.0)
        self.assertAlmostEqual(morph_progress(model, 5.0), 0.5)
        self.assertEqual(morph_progress(model, 6.0), 1.0)
        self.assertEqual(morph_progress(model, 9.0), 1.0)

    def test_validation_normalizes_without_changing_contract(self):
        raw = make_body_model("insect", [0.4, 0.7, 0.5])
        self.assertEqual(validate_body_model(raw), raw)

    def test_rejects_unknown_form_and_invalid_dimensions(self):
        with self.assertRaises(EmbodimentError):
            make_body_model("dragon", (1, 1, 1))
        with self.assertRaises(EmbodimentError):
            make_body_model("humanoid", (1, 0, 1))
        with self.assertRaises(EmbodimentError):
            make_body_model("humanoid", (1, float("nan"), 1))

    def test_rejects_bad_clock(self):
        model = make_body_model("humanoid", (0.6, 1.8, 0.3))
        with self.assertRaises(EmbodimentError):
            morph_progress(model, float("nan"))


if __name__ == "__main__":
    unittest.main()
