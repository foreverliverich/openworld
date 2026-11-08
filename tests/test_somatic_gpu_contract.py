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

 def test_gpu_work_is_bounded_and_rotates(self):
  s=SOURCE.read_text()
  self.assertIn("rotationFrames=5",s)
  self.assertIn("maxCellsPerFrame=262144",s)
  self.assertIn("Math.min(targetChunk,this.maxCellsPerFrame,this.cellCount-this.cursor)",s)
  self.assertIn("processedCells:budget",s)
  self.assertIn("baseCell: u32",s)
  self.assertIn("gid.x+params.baseCell",s)
 def test_audio_uniform_is_explicit_and_bounded(self):
  s=SOURCE.read_text()
  self.assertIn("audioBands: vec4<f32>",s)
  self.assertIn("audioStrength: f32",s)
  self.assertIn("new ArrayBuffer(112)",s)
  self.assertIn("setAudioDrive(bass,mid,treble",s)
  self.assertIn("strength>20",s)
  self.assertIn("clearAudioDrive()",s)
 def test_spectral_bridge_uses_fft_bands_without_recording(self):
  s=(ROOT/"web"/"somatic-audio.js").read_text()
  for term in ("createAnalyser()","getFloatFrequencyData","bandLevel(20,250)","bandLevel(250,2000)","bandLevel(2000,12000)","setAudioDrive","dispose("):
   self.assertIn(term,s)
if __name__=="__main__":unittest.main()

 def test_depth_key_shader_uses_camera_space_and_monotonic_positive_float_bits(self):
  s=(ROOT/"web"/"somatic-sort-depth.wgsl").read_text()
  self.assertIn("camera.view * world",s)
  self.assertIn("let depth = -viewPosition.z",s)
  self.assertIn("~bitcast<u32>(depth)",s)
  self.assertIn("keys[index] = key",s)
  self.assertIn("values[index] = index",s)

 def test_radix_sorter_has_histogram_prefix_scatter_and_ping_pong(self):
  s=(ROOT/"web"/"somatic-gpu-sort.js").read_text()
  for term in ("HIST_WGSL","PREFIX_WGSL","SCATTER_WGSL","atomicAdd(&bins[bucket],1u)","bucketBase","keysOut[destination]","valuesOut[destination]","pass%2===0","PASSES=8"):
   self.assertIn(term,s)
  self.assertIn("createRadixSorter()",SOURCE.read_text())
 def test_sorter_does_not_claim_stable_tie_order_or_zero_copy(self):
  s=(ROOT/"web"/"somatic-gpu-sort.js").read_text()
  self.assertIn("Equal-depth ordering is not stable",s)
  self.assertIn("maxStorageBufferBindingSize",s)
  self.assertIn("this.valuesA",s)

 def test_radix_prefix_is_hierarchical_and_bounded(self):
  s=(ROOT/"web"/"somatic-gpu-sort.js").read_text()
  self.assertIn("GROUPS_PER_SCAN=256",s)
  self.assertIn("PREFIX_LOCAL_WGSL",s)
  self.assertIn("PREFIX_BLOCKS_WGSL",s)
  self.assertIn("localOffsets[group*16u+bucket]",s)
  self.assertIn("blockBases[block*16u+bucket]",s)
  self.assertIn("maxComputeWorkgroupsPerDimension",s)
