"""
Suíte de Testes Automatizados para a Etapa S16:
Resolução da Biblioteca Padrão Java e Classpath (.class, .jar, .jmod e diretórios).
Inclui construtor sintético de bytecode JVMS §4 em memória/tempdir (sem depender de javac).
"""

import os
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.classpath_resolver import (
    ACC_ABSTRACT,
    ACC_FINAL,
    ACC_INTERFACE,
    ACC_PRIVATE,
    ACC_PROTECTED,
    ACC_PUBLIC,
    ACC_STATIC,
    ACC_SUPER,
    ACC_VARARGS,
    ClassFileParser,
    ClasspathDiagnostic,
    DEFAULT_MAX_CLASS_MAJOR,
    ExternalSymbolResolver,
    SignatureDecoder,
)
from src.main import analyze_source, analyze_sources


class _ConstantPoolBuilder:
    """Construtor mínimo de Constant Pool JVMS §4 para gerar .class sintéticos válidos em testes."""

    def __init__(self):
        # Índice 0 reservado (1-based indexing no classfile)
        self._entries: List[bytes] = []
        self._utf8_cache: Dict[str, int] = {}
        self._class_cache: Dict[str, int] = {}

    def _add(self, raw: bytes, slots: int = 1) -> int:
        idx = len(self._entries) + 1
        self._entries.append(raw)
        for _ in range(slots - 1):
            self._entries.append(b"")
        return idx

    def utf8(self, text: str) -> int:
        if text in self._utf8_cache:
            return self._utf8_cache[text]
        data = text.encode("utf-8")
        idx = self._add(struct.pack(">BH", 1, len(data)) + data)
        self._utf8_cache[text] = idx
        return idx

    def class_ref(self, internal_name: str) -> int:
        if internal_name in self._class_cache:
            return self._class_cache[internal_name]
        name_idx = self.utf8(internal_name)
        idx = self._add(struct.pack(">BH", 7, name_idx))
        self._class_cache[internal_name] = idx
        return idx

    def const_int(self, val: int) -> int:
        return self._add(struct.pack(">Bi", 3, val))

    def const_float(self, val: float) -> int:
        return self._add(struct.pack(">Bf", 4, val))

    def const_long(self, val: int) -> int:
        return self._add(struct.pack(">Bq", 5, val), slots=2)

    def const_double(self, val: float) -> int:
        return self._add(struct.pack(">Bd", 6, val), slots=2)

    def const_string(self, text: str) -> int:
        return self._add(struct.pack(">BH", 8, self.utf8(text)))

    def to_bytes(self) -> bytes:
        count = len(self._entries) + 1
        return struct.pack(">H", count) + b"".join(self._entries)


def build_class_bytes(
    internal_name: str,
    *,
    major: int = 52,
    minor: int = 0,
    access_flags: int = ACC_PUBLIC | ACC_SUPER,
    super_internal: Optional[str] = "java/lang/Object",
    interfaces: Sequence[str] = (),
    signature: Optional[str] = None,
    fields: Sequence[Dict[str, Any]] = (),
    methods: Sequence[Dict[str, Any]] = (),
    inner_classes: Sequence[Tuple[str, Optional[str], Optional[str], int]] = (),
) -> bytes:
    """
    Constrói um arquivo .class JVMS §4 válido para testes estáticos de classpath.

    fields: [{"name", "descriptor", "flags", "signature"?, "const_type"?, "const_value"?}]
    methods: [{"name", "descriptor", "flags", "signature"?, "exceptions"?, "code"?}]
    """
    cp = _ConstantPoolBuilder()
    this_idx = cp.class_ref(internal_name)
    super_idx = cp.class_ref(super_internal) if super_internal else 0
    iface_idxs = [cp.class_ref(ifc) for ifc in interfaces]

    def _attr_signature(sig: str) -> bytes:
        aname = cp.utf8("Signature")
        sidx = cp.utf8(sig)
        return struct.pack(">HIH", aname, 2, sidx)

    # Fields
    field_blobs: List[bytes] = []
    for f in fields:
        fflags = int(f.get("flags", ACC_PUBLIC))
        fname = cp.utf8(f["name"])
        fdesc = cp.utf8(f["descriptor"])
        fattrs: List[bytes] = []
        if f.get("signature"):
            fattrs.append(_attr_signature(f["signature"]))
        if "const_value" in f and f["const_value"] is not None:
            ct = f.get("const_type", "int")
            cv = f["const_value"]
            if ct == "int":
                cidx = cp.const_int(int(cv))
            elif ct == "long":
                cidx = cp.const_long(int(cv))
            elif ct == "float":
                cidx = cp.const_float(float(cv))
            elif ct == "double":
                cidx = cp.const_double(float(cv))
            elif ct == "String":
                cidx = cp.const_string(str(cv))
            else:
                raise ValueError(ct)
            fattrs.append(struct.pack(">HIH", cp.utf8("ConstantValue"), 2, cidx))
        field_blobs.append(
            struct.pack(">HHHH", fflags, fname, fdesc, len(fattrs)) + b"".join(fattrs)
        )

    # Methods
    method_blobs: List[bytes] = []
    for m in methods:
        mflags = int(m.get("flags", ACC_PUBLIC))
        mname = cp.utf8(m["name"])
        mdesc = cp.utf8(m["descriptor"])
        mattrs: List[bytes] = []
        if m.get("signature"):
            mattrs.append(_attr_signature(m["signature"]))
        excs = list(m.get("exceptions") or ())
        if excs:
            e_idxs = [cp.class_ref(e) for e in excs]
            payload = struct.pack(">H" + "H" * len(e_idxs), len(e_idxs), *e_idxs)
            mattrs.append(struct.pack(">HI", cp.utf8("Exceptions"), len(payload)) + payload)
        if m.get("code") is not None:
            # Adiciona atributo Code bruto (usado para testar segurança sem execução)
            raw_code = bytes(m["code"])
            code_payload = (
                struct.pack(">HHI", 1, 1, len(raw_code))
                + raw_code
                + struct.pack(">HH", 0, 0)
            )
            mattrs.append(struct.pack(">HI", cp.utf8("Code"), len(code_payload)) + code_payload)
        method_blobs.append(
            struct.pack(">HHHH", mflags, mname, mdesc, len(mattrs)) + b"".join(mattrs)
        )

    # Class attributes
    cls_attrs: List[bytes] = []
    if signature:
        cls_attrs.append(_attr_signature(signature))
    if inner_classes:
        entries_raw: List[bytes] = []
        for inner_int, outer_int, inner_simple, iflags in inner_classes:
            entries_raw.append(
                struct.pack(
                    ">HHHH",
                    cp.class_ref(inner_int),
                    cp.class_ref(outer_int) if outer_int else 0,
                    cp.utf8(inner_simple) if inner_simple else 0,
                    iflags,
                )
            )
        payload = struct.pack(">H", len(entries_raw)) + b"".join(entries_raw)
        cls_attrs.append(struct.pack(">HI", cp.utf8("InnerClasses"), len(payload)) + payload)

    header = struct.pack(">IHH", 0xCAFEBABE, minor, major)
    body = (
        struct.pack(">HHH", access_flags, this_idx, super_idx)
        + struct.pack(">H" + "H" * len(iface_idxs), len(iface_idxs), *iface_idxs)
        + struct.pack(">H", len(field_blobs))
        + b"".join(field_blobs)
        + struct.pack(">H", len(method_blobs))
        + b"".join(method_blobs)
        + struct.pack(">H", len(cls_attrs))
        + b"".join(cls_attrs)
    )
    return header + cp.to_bytes() + body


def write_jar(jar_path: Path, classes: Dict[str, bytes]) -> Path:
    with zipfile.ZipFile(jar_path, "w") as zf:
        for internal_name, data in classes.items():
            zf.writestr(f"{internal_name}.class", data)
    return jar_path


def write_jmod(jmod_path: Path, classes: Dict[str, bytes]) -> Path:
    with zipfile.ZipFile(jmod_path, "w") as zf:
        for internal_name, data in classes.items():
            zf.writestr(f"classes/{internal_name}.class", data)
    return jmod_path


class TestClasspathAndStdlibS16(unittest.TestCase):
    """Testes abrangentes da Etapa S16."""

    # --- 1. Parser de bytecode, decodificador de assinaturas e entradas ---

    def test_01_signature_decoder_and_classfile_parser(self):
        tparams, sc, ifcs = SignatureDecoder.parse_class_signature(
            "<T:Ljava/lang/Number;:Ljava/lang/Comparable<TT;>;>Ljava/util/AbstractList<TT;>;Ljava/util/RandomAccess;"
        )
        self.assertEqual(tparams[0][0], "T")
        self.assertEqual(tparams[0][1], ["java.lang.Number", "java.lang.Comparable<T>"])
        self.assertEqual(sc, "java.util.AbstractList<T>")
        self.assertEqual(ifcs, ["java.util.RandomAccess"])

        mtparams, mparams, mret, mthrows = SignatureDecoder.parse_method_signature(
            "<U:Ljava/lang/Object;>(Ljava/util/List<+TU;>;Ljava/util/Map<Ljava/lang/String;-TU;>;[I)TU;^Ljava/io/IOException;"
        )
        self.assertEqual(mtparams, [("U", ["java.lang.Object"])])
        self.assertEqual(mparams, ["java.util.List<? extends U>", "java.util.Map<java.lang.String, ? super U>", "int[]"])
        self.assertEqual(mret, "U")
        self.assertEqual(mthrows, ["java.io.IOException"])

        raw = build_class_bytes(
            "com/acme/Repo",
            access_flags=ACC_PUBLIC | ACC_SUPER,
            signature="<T:Ljava/lang/Number;>Ljava/lang/Object;Ljava/io/Serializable;",
            fields=[
                {
                    "name": "MAX_ITEMS",
                    "descriptor": "I",
                    "flags": ACC_PUBLIC | ACC_STATIC | ACC_FINAL,
                    "const_type": "int",
                    "const_value": 100,
                }
            ],
            methods=[
                {
                    "name": "<init>",
                    "descriptor": "()V",
                    "flags": ACC_PUBLIC,
                },
                {
                    "name": "fetch",
                    "descriptor": "(I)Ljava/lang/Number;",
                    "signature": "(I)TT;",
                    "flags": ACC_PUBLIC,
                    "exceptions": ["java/io/IOException"],
                    # Opcodes arbitrários nunca são executados pelo parser estático
                    "code": b"\xfe\xff\x00\xb1",
                },
            ],
        )
        info = ClassFileParser.parse_bytes(raw, source_origin="memory.jar")
        self.assertEqual(info.fqn, "com.acme.Repo")
        self.assertEqual(info.package, "com.acme")
        self.assertEqual(info.type_parameters, [("T", ["java.lang.Number"])])
        self.assertEqual(info.interfaces, ["java.io.Serializable"])
        self.assertEqual(info.fields["MAX_ITEMS"].constant_value, ("int", 100))
        self.assertEqual(len(info.constructors), 1)
        m = info.methods["fetch"][0]
        self.assertEqual(m.ret, "T")
        self.assertEqual(m.throws, ["java.io.IOException"])

    def test_02_jmod_and_directory_classpath_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cls_bytes = build_class_bytes(
                "org/lib/Helper",
                fields=[{"name": "TAG", "descriptor": "Ljava/lang/String;", "flags": ACC_PUBLIC | ACC_STATIC | ACC_FINAL, "const_type": "String", "const_value": "ok"}],
                methods=[{"name": "compute", "descriptor": "(I)I", "flags": ACC_PUBLIC | ACC_STATIC}],
            )
            mod_bytes = build_class_bytes(
                "jdk/ext/ModUtil",
                methods=[{"name": "version", "descriptor": "()I", "flags": ACC_PUBLIC | ACC_STATIC}],
            )
            dir_cp = root / "classes_dir"
            out_cls = dir_cp / "org" / "lib" / "Helper.class"
            out_cls.parent.mkdir(parents=True, exist_ok=True)
            out_cls.write_bytes(cls_bytes)

            jmod_path = write_jmod(root / "extra.jmod", {"jdk/ext/ModUtil": mod_bytes})

            code = """
            package app;
            import org.lib.Helper;
            import jdk.ext.ModUtil;
            class Main {
                int run() {
                    String s = Helper.TAG;
                    return Helper.compute(2) + ModUtil.version();
                }
            }
            """
            res = analyze_source(code, classpath=[str(dir_cp), str(jmod_path)])
            self.assertTrue(res.success, msg=res.semantic_errors)
            self.assertEqual(res.unresolved_checks, [])

    # --- 2. Biblioteca padrão Java real (quando disponível no ambiente) ---

    def test_03_stdlib_java_lang_util_io_and_nio(self):
        probe = ExternalSymbolResolver()
        cov = probe.coverage_report()
        if not cov["stdlib_available"]:
            self.skipTest("Nenhuma JDK/JRE local disponível neste ambiente.")

        code = """
        package demo;
        import java.nio.file.Path;
        import java.nio.file.Files;
        import java.nio.ByteBuffer;
        import java.util.List;
        import java.util.ArrayList;
        import java.util.Map;
        import java.util.HashMap;
        import java.io.IOException;
        import java.io.FileInputStream;

        class App {
            byte maxTiny() {
                byte b = Byte.MAX_VALUE;
                return b;
            }

            boolean testarCollectionsNio(Path p) {
                List<String> lista = new ArrayList<>();
                lista.add("java");
                String item = lista.get(0);
                Map<String, Integer> mapa = new HashMap<>();
                mapa.put(item, Integer.valueOf(1));
                ByteBuffer buf = ByteBuffer.allocate(item.length());
                buf.clear();
                return Files.exists(p);
            }

            void ler(String nome) throws IOException {
                FileInputStream fis = new FileInputStream(nome);
                fis.close();
            }
        }
        """
        res = analyze_source(code)
        self.assertTrue(res.success, msg=res.semantic_errors)
        self.assertIsNotNone(res.classpath_coverage)
        self.assertTrue(res.classpath_coverage["stdlib_available"])
        self.assertGreater(res.classpath_coverage["indexed_class_count"], 5000)

    def test_04_stdlib_checked_exceptions_generics_and_functional_interface(self):
        probe = ExternalSymbolResolver()
        if not probe.coverage_report()["stdlib_available"]:
            self.skipTest("Nenhuma JDK/JRE local disponível neste ambiente.")

        # Exceção verificada real vinda de java.io.FileInputStream (não tratada -> erro S14)
        bad_io = """
        import java.io.FileInputStream;
        class BadIO {
            void abrir() {
                FileInputStream f = new FileInputStream("x.txt");
            }
        }
        """
        res_io = analyze_source(bad_io)
        self.assertFalse(res_io.success)
        self.assertTrue(any("exceç" in str(e).lower() or "filenotfound" in str(e).lower() for e in res_io.semantic_errors))

        # FileFilter de java.io não está em BUILTIN_FUNCTIONAL_INTERFACES; deve ser resolvido via bytecode
        good_sam = """
        import java.io.File;
        import java.io.FileFilter;
        class FilterUse {
            FileFilter criar() {
                return f -> f.isFile();
            }
        }
        """
        res_sam = analyze_source(good_sam)
        self.assertTrue(res_sam.success, msg=res_sam.semantic_errors)

        # Path sem import não deve vazar silenciosamente
        no_import = """
        class NoImp {
            void f() {
                Files.exists(null);
            }
        }
        """
        res_ni = analyze_source(no_import)
        self.assertTrue(len(res_ni.unresolved_checks) > 0)

    def test_05_honest_coverage_report_for_partial_jre(self):
        res = analyze_source("class Empty {}")
        cov = res.classpath_coverage
        self.assertIsNotNone(cov)
        self.assertIn("is_partial_jdk", cov)
        # Se estamos sobre rt.jar (JRE 8), is_partial_jdk deve ser True honestamente
        if cov.get("stdlib_kind") == "rt.jar":
            self.assertTrue(cov["is_partial_jdk"])
            self.assertEqual(cov["stdlib_java_version"], "8")

    # --- 3. JARs externos, modificadores, visibilidade, herança, generics, exceções e constantes ---

    def _build_acme_jar(self, jar_path: Path) -> Path:
        classes = {
            "com/acme/PluginException": build_class_bytes(
                "com/acme/PluginException",
                super_internal="java/lang/Exception",
                methods=[{"name": "<init>", "descriptor": "(Ljava/lang/String;)V", "flags": ACC_PUBLIC}],
            ),
            "com/acme/Plugin": build_class_bytes(
                "com/acme/Plugin",
                access_flags=ACC_PUBLIC | ACC_INTERFACE | ACC_ABSTRACT,
                methods=[
                    {
                        "name": "execute",
                        "descriptor": "(Ljava/lang/String;)I",
                        "flags": ACC_PUBLIC | ACC_ABSTRACT,
                        "exceptions": ["com/acme/PluginException"],
                    },
                    {
                        "name": "tag",
                        "descriptor": "()Ljava/lang/String;",
                        "flags": ACC_PUBLIC,
                        "code": b"\x01\xb0",  # método default em interface (não abstract, não static)
                    },
                ],
            ),
            "com/acme/BaseWidget": build_class_bytes(
                "com/acme/BaseWidget",
                access_flags=ACC_PUBLIC | ACC_ABSTRACT | ACC_SUPER,
                methods=[
                    {"name": "<init>", "descriptor": "()V", "flags": ACC_PUBLIC},
                    {"name": "secret", "descriptor": "()V", "flags": ACC_PRIVATE},
                    {"name": "protMethod", "descriptor": "()I", "flags": ACC_PROTECTED},
                    {"name": "pkgMethod", "descriptor": "()V", "flags": 0},
                    {"name": "step", "descriptor": "()V", "flags": ACC_PUBLIC | ACC_ABSTRACT},
                    {"name": "locked", "descriptor": "()V", "flags": ACC_PUBLIC | ACC_FINAL},
                ],
            ),
            "com/acme/PackageInternal": build_class_bytes(
                "com/acme/PackageInternal",
                access_flags=ACC_SUPER,  # package-private
                methods=[{"name": "<init>", "descriptor": "()V", "flags": ACC_PUBLIC}],
            ),
            "com/acme/SealedLeaf": build_class_bytes(
                "com/acme/SealedLeaf",
                access_flags=ACC_PUBLIC | ACC_FINAL | ACC_SUPER,
                methods=[{"name": "<init>", "descriptor": "()V", "flags": ACC_PUBLIC}],
            ),
            "com/acme/Box": build_class_bytes(
                "com/acme/Box",
                signature="<T:Ljava/lang/Object;>Ljava/lang/Object;",
                methods=[
                    {"name": "<init>", "descriptor": "(Ljava/lang/Object;)V", "signature": "(TT;)V", "flags": ACC_PUBLIC},
                    {"name": "get", "descriptor": "()Ljava/lang/Object;", "signature": "()TT;", "flags": ACC_PUBLIC},
                    {"name": "join", "descriptor": "([Ljava/lang/String;)Ljava/lang/String;", "flags": ACC_PUBLIC | ACC_STATIC | ACC_VARARGS},
                ],
            ),
            "com/acme/Consts": build_class_bytes(
                "com/acme/Consts",
                fields=[
                    {"name": "OK_BYTE", "descriptor": "I", "flags": ACC_PUBLIC | ACC_STATIC | ACC_FINAL, "const_type": "int", "const_value": 120},
                    {"name": "BIG_INT", "descriptor": "I", "flags": ACC_PUBLIC | ACC_STATIC | ACC_FINAL, "const_type": "int", "const_value": 200},
                ],
                methods=[{"name": "<init>", "descriptor": "()V", "flags": ACC_PUBLIC}],
            ),
        }
        return write_jar(jar_path, classes)

    def test_06_external_jar_generics_varargs_constants_and_exceptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._build_acme_jar(Path(tmp) / "acme.jar")

            valid_code = """
            package client;
            import com.acme.Box;
            import com.acme.Consts;
            import com.acme.Plugin;
            import com.acme.PluginException;

            class MyPlugin implements Plugin {
                public int execute(String arg) throws PluginException {
                    if (arg.isEmpty()) {
                        throw new PluginException("vazio");
                    }
                    byte b = Consts.OK_BYTE;
                    Box<String> bx = new Box<>("hello");
                    String s = bx.get();
                    String joined = Box.join(s, "world");
                    return b + joined.length();
                }
            }
            """
            res = analyze_source(valid_code, classpath=[str(jar)])
            self.assertTrue(res.success, msg=res.semantic_errors)

            # Narrowing com constante externa acima do limite de byte deve falhar
            overflow_code = """
            package client;
            import com.acme.Consts;
            class BadConst {
                byte x = Consts.BIG_INT;
            }
            """
            res_ov = analyze_source(overflow_code, classpath=[str(jar)])
            self.assertFalse(res_ov.success)

            # Exceção verificada vinda de método do JAR sem tratamento deve falhar (S14)
            unhandled_exc = """
            package client;
            import com.acme.Plugin;
            class Caller {
                int run(Plugin p) {
                    return p.execute("x");
                }
            }
            """
            res_ex = analyze_source(unhandled_exc, classpath=[str(jar)])
            self.assertFalse(res_ex.success)
            self.assertTrue(any("pluginexception" in str(e).lower() for e in res_ex.semantic_errors))

    def test_07_external_jar_modifiers_visibility_and_hierarchy(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._build_acme_jar(Path(tmp) / "acme.jar")

            # 1. Subclasse em outro pacote pode chamar protected via herança, mas não private/package-private nem sobrescrever final
            bad_sub = """
            package client;
            import com.acme.BaseWidget;
            class Sub extends BaseWidget {
                public void step() {}
                public void locked() {}
                void f(BaseWidget other) {
                    int ok = protMethod();
                    other.secret();
                    other.pkgMethod();
                }
            }
            """
            res = analyze_source(bad_sub, classpath=[str(jar)])
            self.assertFalse(res.success)
            joined = "\n".join(str(e).lower() for e in res.semantic_errors)
            self.assertIn("final", joined)
            self.assertIn("private", joined)

            # 2. Não pode instanciar abstract, estender final nem deixar de implementar método abstrato de interface externa
            bad_inst = """
            package client;
            import com.acme.BaseWidget;
            import com.acme.SealedLeaf;
            import com.acme.Plugin;
            class ExtendFinal extends SealedLeaf {}
            class MissingImpl implements Plugin {}
            class Maker {
                void m() {
                    BaseWidget w = new BaseWidget();
                }
            }
            """
            res2 = analyze_source(bad_inst, classpath=[str(jar)])
            self.assertFalse(res2.success)
            j2 = "\n".join(str(e).lower() for e in res2.semantic_errors)
            self.assertIn("final", j2)
            self.assertIn("abstrata", j2)
            self.assertIn("execute", j2)

            # 3. Classe package-private em outro pacote não é acessível
            pkg_priv = """
            package other;
            class U {
                com.acme.PackageInternal ref;
            }
            """
            res3 = analyze_source(pkg_priv, classpath=[str(jar)])
            self.assertFalse(res3.success)

    def test_08_missing_method_missing_class_version_mismatch_and_corrupt_jar(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._build_acme_jar(Path(tmp) / "acme.jar")

            # Método inexistente em classe resolvida do JAR -> erro semântico claro
            bad_method = """
            package client;
            import com.acme.Box;
            class Use {
                void f() {
                    Box<String> b = new Box<>("a");
                    b.naoExiste();
                }
            }
            """
            res_m = analyze_source(bad_method, classpath=[str(jar)])
            self.assertFalse(res_m.success)
            self.assertTrue(any("naoexiste" in str(e).lower() and "não encontrado" in str(e).lower() for e in res_m.semantic_errors))

            # Classe inexistente em import explícito -> diagnóstico claro em unresolved_checks
            missing_cls = """
            package client;
            import com.acme.Inexistente;
            class Use {
                Inexistente obj;
            }
            """
            res_c = analyze_source(missing_cls, classpath=[str(jar)])
            self.assertTrue(any("Inexistente" in u for u in res_c.unresolved_checks), msg=res_c.unresolved_checks)

            # Versão de bytecode incompatível (major=71 > DEFAULT_MAX_CLASS_MAJOR=70)
            future_jar = write_jar(
                Path(tmp) / "future.jar",
                {
                    "com/future/TooNew": build_class_bytes(
                        "com/future/TooNew",
                        major=71,
                        methods=[{"name": "<init>", "descriptor": "()V", "flags": ACC_PUBLIC}],
                    )
                },
            )
            future_src = """
            import com.future.TooNew;
            class UseFuture {
                TooNew x;
            }
            """
            res_v = analyze_source(future_src, classpath=[str(future_jar)])
            self.assertFalse(res_v.success)
            self.assertTrue(any("versão" in str(e).lower() or "incompatível" in str(e).lower() for e in res_v.semantic_errors))

            # JAR corrompido + caminho inexistente -> diagnósticos claros
            bad_jar = Path(tmp) / "corrupt.jar"
            bad_jar.write_bytes(b"NOT_A_ZIP_FILE")
            res_bad = analyze_source("class Ok {}", classpath=[str(bad_jar), str(Path(tmp) / "missing.jar")])
            self.assertFalse(res_bad.success)
            cov = res_bad.classpath_coverage
            kinds = {d.kind for d in cov["diagnostics"]}
            self.assertIn("corrupt_classfile", kinds)
            self.assertIn("missing_entry", kinds)

    def test_09_compilation_unit_precedence_shadows_stdlib_and_jar(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._build_acme_jar(Path(tmp) / "acme.jar")

            # Declaração local de ArrayList e com.acme.Consts deve prevalecer sobre stdlib e JAR
            src_shadow_local = """
            class ArrayList {
                int apenasDaUnidade() {
                    return 77;
                }
            }
            class Teste {
                int run() {
                    ArrayList al = new ArrayList();
                    return al.apenasDaUnidade();
                }
            }
            """
            res1 = analyze_source(src_shadow_local, classpath=[str(jar)])
            self.assertTrue(res1.success, msg=res1.semantic_errors)

            # Multi-unidade com pacote idêntico ao JAR: classe da unidade tem precedência absoluta
            unit_consts = """
            package com.acme;
            public class Consts {
                public static final int LOCAL_ONLY = 9;
            }
            """
            unit_user = """
            package app;
            import com.acme.Consts;
            class App {
                int x = Consts.LOCAL_ONLY;
            }
            """
            res2 = analyze_sources([unit_consts, unit_user], classpath=[str(jar)])
            self.assertTrue(res2.success, msg=res2.semantic_errors)


if __name__ == "__main__":
    unittest.main()
