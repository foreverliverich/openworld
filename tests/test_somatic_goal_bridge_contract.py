"""Static contracts for the browser-side cognitive-goal/GPU steering seam."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SomaticGoalBridgeContractTests(unittest.TestCase):
    def test_gpu_attractor_is_bounded_and_zero_distance_safe(self):
        source = (ROOT / "web" / "somatic-gpu.js").read_text()
        self.assertIn("setAttractor(x,y,z", source)
        self.assertIn("goalDistance>1e-5", source)
        self.assertIn("maxAttractionAcceleration", source)
        self.assertIn("size:64,usage:GPUBufferUsage.UNIFORM", source)
        self.assertIn("this.attractionCenter[2]", source)

    def test_receiver_requires_accepted_versioned_monotonic_goal(self):
        source = (ROOT / "web" / "chimera-bridge.js").read_text()
        self.assertIn('message.schema_version!==1', source)
        self.assertIn('message.accepted!==true', source)
        self.assertIn('message.goal_sequence<=this.lastGoalSequence', source)
        self.assertIn('Number.isFinite(t.x)', source)
        self.assertIn('this.kernel.setAttractor', source)

    def test_gpu_and_host_state_are_not_misrepresented_as_zero_copy(self):
        source = (ROOT / "web" / "somatic-gpu.js").read_text()
        self.assertIn("This is not zero-copy", source)
        self.assertIn("queue.writeBuffer", source)


if __name__ == "__main__":
    unittest.main()
