"""Static ABI and safety checks for the browser WebGPU hot path."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"web"/"somatic-gpu.js"
class SomaticGPUContractTests(unittest.TestCase):
 def test_preserves_three_vec4_48_byte_cell_abi(self):
  s=SOURCE.read_text()
  self.assertIn("CELL_BYTES=48",s);self.assertIn("FLOATS_PER_CELL=12",s)
  self.assertIn("position: vec4<f32>",s);self.assertIn("velocity: vec4<f32>",s);self.assertIn("state: vec4<f32>",s)
 def test_pages_to_actual_adapter_limits(self):
  s=SOURCE.read_text();self.assertIn("maxStorageBufferBindingSize",s);self.assertIn("maxBufferSize",s);self.assertIn("cellsPerPage",s)
 def test_hot_path_has_no_per_frame_readback(self):
  s=SOURCE.read_text();self.assertIn("async readback()",s);self.assertNotIn("await this.readback()",s)
 def test_contact_and_friction_are_explicit(self):
  s=SOURCE.read_text()
  for term in ("groundY","restitution","friction","frictionImpulse"): self.assertIn(term,s)
 def test_does_not_claim_zero_copy_or_use_arbitrary_harmonics(self):
  s=SOURCE.read_text();self.assertIn("not zero-copy",s);self.assertNotIn("432.0",s);self.assertNotIn("VORTEX_SEQ",s)
 def test_dt_and_disposal_are_guarded(self):
  s=SOURCE.read_text();self.assertIn("MAX_DT",s);self.assertIn("this.disposed",s);self.assertIn("Number.isFinite(deltaSeconds)",s)
if __name__=="__main__":unittest.main()
