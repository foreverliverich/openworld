import unittest

from chimera.tecq.contract import (
    ContractViolation,
    IdentitySeed,
    StateArtifact,
    FoldDescriptor,
    LOSSLESS_CHECKPOINT_DOMAINS,
    memory_budget,
    validate_somatic_cell_buffer,
    validate_bond_edges,
    normalize_quaternion_xyzw,
    validate_phase_schedule,
    phase_experiment_baselines,
)


class IdentityAndFoldContractTests(unittest.TestCase):
    def test_identity_seed_accepts_up_to_one_kibibyte(self):
        seed = IdentitySeed(version="opaque-v1", payload=bytes(1024))
        self.assertEqual(len(seed.payload), 1024)
        self.assertEqual(len(seed.digest), 64)

    def test_identity_seed_rejects_overflow(self):
        with self.assertRaises(ContractViolation):
            IdentitySeed(version="opaque-v1", payload=bytes(1025))

    def test_portable_fold_requires_recipe(self):
        with self.assertRaises(ContractViolation):
            FoldDescriptor(
                codec="SEED2",
                codec_version="3",
                mode="portable",
                identity_seed=IdentitySeed("opaque-v1", b"seed"),
            )

    def test_lossless_fold_requires_checkpoint_and_all_domains(self):
        artifact = StateArtifact("cas://sha256/example", "a" * 64, 4096)
        with self.assertRaises(ContractViolation):
            FoldDescriptor(
                codec="TECQ-FOLD",
                codec_version="1",
                mode="lossless",
                identity_seed=IdentitySeed("opaque-v1", b"seed"),
                checkpoint=artifact,
                checkpoint_domains=("cell_abi",),
            )
        descriptor = FoldDescriptor(
            codec="TECQ-FOLD",
            codec_version="1",
            mode="lossless",
            identity_seed=IdentitySeed("opaque-v1", b"seed"),
            checkpoint=artifact,
            checkpoint_domains=LOSSLESS_CHECKPOINT_DOMAINS,
        )
        self.assertEqual(descriptor.manifest()["mode"], "lossless")


class TecqContractTests(unittest.TestCase):
    def test_48_byte_cell_abi_is_preserved_as_opaque_records(self):
        self.assertEqual(validate_somatic_cell_buffer(bytes(48 * 15000)), 15000)
        with self.assertRaises(ContractViolation):
            validate_somatic_cell_buffer(bytes(49))

    def test_million_cell_gpu_budget_is_not_misreported_as_128_mib(self):
        report = memory_budget(1_000_000)
        self.assertEqual(report.base_cell_buffer_bytes, 48_000_000)
        self.assertEqual(report.gpu_state_bytes, 144_000_000)
        self.assertFalse(report.gpu_fits)
        self.assertGreater(report.gpu_overage_bytes, 0)

    def test_15000_cell_experiment_fits_declared_gpu_pool(self):
        report = memory_budget(15_000)
        self.assertTrue(report.gpu_fits)

    def test_bonds_are_canonical_and_reject_self_edges(self):
        edges = validate_bond_edges([(3, 1, 0.5), (2, 4, 1.0)], 5)
        self.assertEqual(edges, ((1, 3, 0.5), (2, 4, 1.0)))
        with self.assertRaises(ContractViolation):
            validate_bond_edges([(1, 1, 0.5)], 5)

    def test_quaternion_normalization_is_real_rotational_state(self):
        self.assertEqual(normalize_quaternion_xyzw((0, 0, 0, 2)), (0.0, 0.0, 0.0, 1.0))
        with self.assertRaises(ContractViolation):
            normalize_quaternion_xyzw((0, 0, 0, 0))

    def test_vortex_sequence_is_preserved_as_test_candidate(self):
        self.assertEqual(validate_phase_schedule(), (1, 2, 4, 8, 7, 5))
        self.assertEqual(len(phase_experiment_baselines()), 6)


if __name__ == "__main__":
    unittest.main()
