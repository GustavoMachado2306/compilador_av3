"""Suíte de Testes para a Correção D5 — Validação de Tipos em try-with-resources (JLS §14.20.3)."""

import struct
import tempfile
import unittest
from pathlib import Path

from src.main import analyze_source


def _build_class_bytes(internal_name: str, super_internal: str = "java/lang/Object", interfaces=None) -> bytes:
    """Constroi .class minimo valido com superclasse e interfaces especificadas."""
    interfaces = interfaces or []
    cp_entries = []

    def add_utf8(s: str) -> int:
        data = s.encode("utf-8")
        cp_entries.append(b"\x01" + struct.pack(">H", len(data)) + data)
        return len(cp_entries)

    def add_class(name: str) -> int:
        ni = add_utf8(name)
        cp_entries.append(b"\x07" + struct.pack(">H", ni))
        return len(cp_entries)

    this_idx = add_class(internal_name)
    super_idx = add_class(super_internal)
    iface_idxs = [add_class(iface) for iface in interfaces]

    cp_bytes = struct.pack(">H", len(cp_entries) + 1) + b"".join(cp_entries)
    header = struct.pack(">IHH", 0xCAFEBABE, 0, 52)
    class_info = struct.pack(">HHHH", 0x0021, this_idx, super_idx, len(iface_idxs))
    ifaces_bytes = b"".join(struct.pack(">H", idx) for idx in iface_idxs)
    tail = struct.pack(">HHHH", 0, 0, 0, 0)
    return header + cp_bytes + class_info + ifaces_bytes + tail


class TestJava26TryWithResourcesD5(unittest.TestCase):
    def test_01_valid_autocloseable_inheritance_generics_and_multi(self):
        code = """
        import java.io.*;
        class RecDireto implements AutoCloseable {
            public void close() {}
        }
        class RecIndireto extends RecDireto {}
        interface MeuCloseable extends Closeable {}
        class BoxCloseable<T> implements AutoCloseable {
            public void close() {}
        }
        class Uso<R extends AutoCloseable> {
            void ok(RecIndireto existente, final BoxCloseable<String> bx, R param) throws Exception {
                try (RecDireto a = new RecDireto();
                     RecIndireto b = new RecIndireto();
                     var c = new RecIndireto();
                     existente;
                     bx;
                     param;
                     BufferedReader br = null;
                     MeuCloseable mc = null) {
                    int x = 1;
                }
            }
        }
        """
        res = analyze_source(code)
        self.assertTrue(res.success, msg=res.semantic_errors)

    def test_02_non_autocloseable_resources_rejected(self):
        defs = """
        class NaoFechavel {}
        class BoxNaoFechavel<T> {}
        class RecOk implements AutoCloseable { public void close() {} }
        """
        bad_cases = [
            ("String local", 'class A { void f() { try (String s = "x") {} } }'),
            ("int local", "class A { void f() { try (int n = 10) {} } }"),
            ("Object var", "class A { Object mk() { return null; } void f() { try (var x = mk()) {} } }"),
            ("custom class", defs + "class A { void f() { try (NaoFechavel nf = new NaoFechavel()) {} } }"),
            ("generic non-closeable", defs + "class A { void f() { try (BoxNaoFechavel<String> bx = new BoxNaoFechavel<>()) {} } }"),
            ("existing variable non-closeable", defs + "class A { void f(final NaoFechavel nf) { try (nf) {} } }"),
            ("array type", defs + "class A { void f() { try (RecOk[] arr = null) {} } }"),
            ("second resource invalid", defs + "class A { void f() { try (RecOk ok = new RecOk(); NaoFechavel nf = new NaoFechavel()) {} } }"),
            ("unbounded type parameter", "class A<T> { void f(final T t) { try (t) {} } }"),
        ]
        for label, src in bad_cases:
            with self.subTest(case=label):
                res = analyze_source(src)
                self.assertFalse(res.success, msg=f"Esperava rejeição em try-with-resources para: {label}")
                self.assertTrue(
                    any("AutoCloseable" in str(e) for e in res.semantic_errors),
                    msg=res.semantic_errors,
                )

    def test_03_external_classpath_and_unresolved_resources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_dir = Path(tmpdir) / "pkg" / "res"
            pkg_dir.mkdir(parents=True)
            (pkg_dir / "ExtOk.class").write_bytes(
                _build_class_bytes("pkg/res/ExtOk", interfaces=["java/lang/AutoCloseable"])
            )
            (pkg_dir / "ExtSubCloseable.class").write_bytes(
                _build_class_bytes("pkg/res/ExtSubCloseable", interfaces=["java/io/Closeable"])
            )
            (pkg_dir / "ExtBad.class").write_bytes(
                _build_class_bytes("pkg/res/ExtBad")
            )

            ok_src = """
            import pkg.res.ExtOk;
            import pkg.res.ExtSubCloseable;
            class Uso {
                void m(ExtOk a, ExtSubCloseable b) throws Exception {
                    try (a; b; ExtDesconhecido desc = null) {}
                }
            }
            """
            res_ok = analyze_source(ok_src, classpath=[tmpdir])
            self.assertTrue(res_ok.success, msg=res_ok.semantic_errors)

            bad_src = """
            import pkg.res.ExtBad;
            class Uso {
                void m(ExtBad b) {
                    try (b) {}
                }
            }
            """
            res_bad = analyze_source(bad_src, classpath=[tmpdir])
            self.assertFalse(res_bad.success)
            self.assertTrue(
                any("AutoCloseable" in str(e) for e in res_bad.semantic_errors),
                msg=res_bad.semantic_errors,
            )


if __name__ == "__main__":
    unittest.main()

