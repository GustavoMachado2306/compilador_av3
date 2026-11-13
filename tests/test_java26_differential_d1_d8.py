import unittest
from unittest.mock import patch

from tests.differential_d1_d8 import (
    build_differential_matrix,
    discover_jdk26_javac,
    execute_matrix,
    summarize_results,
)


class TestJava26DifferentialD1D8(unittest.TestCase):
    """Integra a matriz diferencial D1–D8 à suíte de testes e valida o gate estrito de JDK 26."""

    def test_matrix_alignment_and_optional_jdk26_oracle(self):
        cases = build_differential_matrix()
        self.assertGreaterEqual(len(cases), 75)

        javac_info = discover_jdk26_javac()
        results = execute_matrix(cases, javac_info)
        summary = summarize_results(results, javac_info)

        self.assertEqual(
            summary["jls_mismatches"],
            [],
            msg=f"Divergências no compilador próprio vs JLS 26 esperado: {summary['jls_mismatches']}",
        )

        if javac_info.is_jdk26:
            mismatches = [
                (r.case.case_id, r.classification, r.own_verdict, r.javac_verdict, r.javac_output)
                for r in results
                if r.classification != "CONCORDÂNCIA"
            ]
            self.assertEqual(mismatches, [], msg=f"Divergências vs javac JDK 26: {mismatches}")
        else:
            self.assertEqual(summary["classifications"]["INCONCLUSIVO"], len(cases))

    def test_discover_jdk26_javac_rejects_older_jdks(self):
        class _FakeProc:
            def __init__(self, stdout: str):
                self.stdout = stdout
                self.stderr = ""

        with (
            patch("tests.differential_d1_d8.Path.exists", return_value=True),
            patch("tests.differential_d1_d8.subprocess.run", return_value=_FakeProc("javac 21.0.4")),
        ):
            info = discover_jdk26_javac("C:/fake/jdk21/bin/javac.exe")
            self.assertFalse(info.available)
            self.assertFalse(info.is_jdk26)
            self.assertIn("esperado 26", info.reason)


if __name__ == "__main__":
    unittest.main()

