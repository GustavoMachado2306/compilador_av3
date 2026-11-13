"""Infraestrutura reutilizável e matriz de validação diferencial D1–D8 (compilador_base_av3 vs javac JDK 26).

Executa os casos de teste isoladamente em diretórios temporários:
1. Analisa todos os casos no `compilador_base_av3` (`src.main.analyze_sources`).
2. Se houver um `javac` oficial do JDK 26 disponível (major == 26), compila os mesmos casos
   com `--release 26` (e `--enable-preview` nos casos de preview) e compara os vereditos.
3. Caso o JDK 26 não esteja instalado no ambiente, NÃO substitui por JDK anterior (8/17/21):
   marca a comparação com o oráculo como `INCONCLUSIVO` e sinaliza qualquer divergência
   entre o resultado obtido no compilador próprio e o veredito normativo esperado da JLS 26.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.main import analyze_sources


@dataclass(frozen=True)
class DifferentialCase:
    case_id: str
    category: str
    title: str
    jls_ref: str
    expected_jls: str  # "ACCEPT" ou "REJECT"
    files: Dict[str, str]
    preview: bool = False
    module_source_path: bool = False
    note: str = ""


@dataclass
class CaseExecutionResult:
    case: DifferentialCase
    own_verdict: str  # "ACCEPT" | "REJECT"
    own_errors: List[str] = field(default_factory=list)
    own_unresolved: List[str] = field(default_factory=list)
    javac_verdict: Optional[str] = None  # "ACCEPT" | "REJECT" | None
    javac_exit_code: Optional[int] = None
    javac_output: str = ""
    classification: str = "INCONCLUSIVO"
    jls_alignment: str = "OK"


@dataclass
class JavacInfo:
    available: bool
    path: Optional[str] = None
    version_text: str = ""
    major_version: Optional[int] = None
    is_jdk26: bool = False
    reason: str = ""


def _parse_javac_major(version_text: str) -> Optional[int]:
    match = re.search(r"javac\s+(\d+)(?:\.(\d+))?", version_text)
    if not match:
        return None
    first = int(match.group(1))
    second = int(match.group(2)) if match.group(2) else None
    if first == 1 and second is not None:
        return second
    return first


def discover_jdk26_javac(explicit_path: Optional[str] = None) -> JavacInfo:
    """Procura exclusivamente um compilador `javac` oficial do JDK 26."""
    candidates: List[str] = []
    if explicit_path:
        candidates.append(explicit_path)
    env_javac = os.environ.get("JDK26_JAVAC")
    if env_javac:
        candidates.append(env_javac)
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        ext = ".exe" if os.name == "nt" else ""
        candidates.append(str(Path(java_home) / "bin" / f"javac{ext}"))
    which_javac = shutil.which("javac")
    if which_javac:
        candidates.append(which_javac)

    seen = set()
    tried_details: List[str] = []
    for cand in candidates:
        norm = str(Path(cand))
        if norm in seen:
            continue
        seen.add(norm)
        if not Path(cand).exists() and shutil.which(cand) is None:
            tried_details.append(f"{cand} (não encontrado)")
            continue
        try:
            proc = subprocess.run(
                [cand, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            ver = (proc.stdout or proc.stderr or "").strip()
            major = _parse_javac_major(ver)
            if major == 26:
                return JavacInfo(
                    available=True,
                    path=cand,
                    version_text=ver,
                    major_version=major,
                    is_jdk26=True,
                    reason="JDK 26 javac detectado.",
                )
            tried_details.append(f"{cand} -> '{ver}' (major={major}, esperado 26)")
        except Exception as exc:
            tried_details.append(f"{cand} -> erro ao consultar versão: {exc}")

    if not tried_details:
        reason = "Nenhum binário 'javac' encontrado no PATH, JAVA_HOME ou JDK26_JAVAC."
    else:
        reason = "Nenhum JDK 26 encontrado: " + "; ".join(tried_details)
    return JavacInfo(available=False, reason=reason)


def run_own_compiler(case: DifferentialCase) -> Tuple[str, List[str], List[str]]:
    sources = [case.files[k] for k in sorted(case.files.keys())]
    res = analyze_sources(
        sources,
        enable_preview_primitive_patterns=case.preview,
        include_stdlib=True,
    )
    errors: List[str] = []
    if res.lexical_errors:
        errors.extend(str(e) for e in res.lexical_errors)
    elif res.lexical_error is not None:
        errors.append(str(res.lexical_error))
    if res.syntactic_error is not None:
        errors.append(str(res.syntactic_error))
    errors.extend(str(e) for e in (res.semantic_errors or []))
    verdict = "ACCEPT" if res.success else "REJECT"
    return verdict, errors, list(res.unresolved_checks or [])


def run_javac_oracle(case: DifferentialCase, javac_path: str) -> Tuple[str, int, str]:
    with tempfile.TemporaryDirectory(prefix=f"diff_{case.case_id}_") as tmp_dir:
        tmp_root = Path(tmp_dir)
        out_dir = tmp_root / "out"
        src_root = tmp_root / "src"
        out_dir.mkdir(parents=True, exist_ok=True)
        src_root.mkdir(parents=True, exist_ok=True)

        written_files: List[Path] = []
        for rel_path, content in case.files.items():
            dest = src_root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written_files.append(dest)

        cmd: List[str] = [javac_path, "-encoding", "UTF-8", "--release", "26", "-d", str(out_dir)]
        if case.preview:
            cmd.append("--enable-preview")
        if case.module_source_path:
            cmd.extend(["--module-source-path", str(src_root)])
        cmd.extend(str(p) for p in written_files)

        proc = subprocess.run(
            cmd,
            cwd=str(src_root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        verdict = "ACCEPT" if proc.returncode == 0 else "REJECT"
        return verdict, proc.returncode, output


def classify_differential(own_verdict: str, javac_verdict: Optional[str]) -> str:
    if javac_verdict is None:
        return "INCONCLUSIVO"
    if own_verdict == javac_verdict:
        return "CONCORDÂNCIA"
    if own_verdict == "ACCEPT" and javac_verdict == "REJECT":
        return "FALSO ACEITE"
    return "FALSA REJEIÇÃO"


def build_differential_matrix() -> List[DifferentialCase]:
    """Matriz completa D1–D8, interações cross-feature e casos adversariais."""
    return [
        # ================= D1 — Generic Arity =================
        DifferentialCase(
            case_id="D1-01",
            category="D1",
            title="Aridade exata, tipo raw e diamond válido",
            jls_ref="JLS §4.5 / §15.9",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Box<T> {
                    T v;
                    Box(T v) { this.v = v; }
                }
                interface Pair<K, V> {}
                class Demo {
                    void ok() {
                        Box<String> a = new Box<String>("ok");
                        Box<String> b = new Box<>("ok");
                        Box raw = new Box("raw");
                        Pair<String, Integer> p = null;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-02",
            category="D1",
            title="Aridade menor ou maior que a declarada",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Pair<K, V> {}
                class Demo {
                    Pair<String> missingArg;
                    Pair<String, Integer, Boolean> extraArg;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-03",
            category="D1",
            title="Argumentos genéricos em tipo não genérico",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Plain {}
                class Demo {
                    Plain<String> p;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-04",
            category="D1",
            title="Diamond explícito fora de new (campo/extends/cast)",
            jls_ref="JLS §4.5.1 / §15.9",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Box<T> {}
                class Demo {
                    Box<> badField;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-05",
            category="D1",
            title="Tipos aninhados qualificados com argumentos por segmento",
            jls_ref="JLS §4.5 / §6.5.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Outer<T> {
                    class Inner<U> {}
                    static class Nested<V> {}
                }
                class Demo {
                    Outer<String>.Inner<Integer> okInner;
                    Outer.Nested<Boolean> okStaticNested;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-06",
            category="D1",
            title="Aridade errada em segmento interno de tipo qualificado",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer<T> {
                    class Inner<U> {}
                }
                class Demo {
                    Outer<String, Integer>.Inner<Boolean> badOuterSeg;
                    Outer<String>.Inner<Boolean, Integer> badInnerSeg;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-07",
            category="D1",
            title="Argumentos genéricos em tipo qualificador de static nested class",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer<T> {
                    static class Nested<V> {}
                }
                class Demo {
                    Outer<String>.Nested<Integer> illegal;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-07b",
            category="D1",
            title="Argumentos genéricos no qualificador de static nested class não genérica",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer<T> {
                    static class Nested {}
                }
                class Demo {
                    Outer<String>.Nested illegal;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-08",
            category="D1",
            title="Method reference de array com aridade errada",
            jls_ref="JLS §4.5 / §15.13.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import java.util.List;
                import java.util.function.IntFunction;
                class Demo {
                    void test() {
                        IntFunction<Object> fn = List<String, Integer>[]::new;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-09",
            category="D1",
            title="Tipos externos java.util.List/Map com aridade válida e inválida",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import java.util.Map;
                class Demo {
                    Map<String> badMap;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D1-10",
            category="D1",
            title="Method reference de criação de array reificável List<?>[]::new",
            jls_ref="JLS §4.5 / §15.13.1",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import java.util.List;
                import java.util.function.IntFunction;
                class Demo {
                    void test() {
                        IntFunction<List<?>[]> fn = List<?>[]::new;
                    }
                }
                """
            },
        ),

        # ================= D2 — Generic Bounds =================
        DifferentialCase(
            case_id="D2-01",
            category="D2",
            title="Bound simples satisfeito (Number <- Integer/Double)",
            jls_ref="JLS §4.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class NumBox<T extends Number> {}
                class Demo {
                    NumBox<Integer> a;
                    NumBox<Double> b;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-02",
            category="D2",
            title="Bound simples violado (Number <- String)",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class NumBox<T extends Number> {}
                class Demo {
                    NumBox<String> bad;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-03",
            category="D2",
            title="Intersection bound múltiplo válido vs incompleto",
            jls_ref="JLS §4.4 / §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                interface A {}
                interface B {}
                class OnlyA implements A {}
                class Hold<T extends A & B> {}
                class Demo {
                    Hold<OnlyA> bad;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-04",
            category="D2",
            title="F-bound recursivo com Enum implícito Comparable<E>",
            jls_ref="JLS §8.9 / §4.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                enum Color { RED, BLUE }
                class CompBox<T extends Comparable<T>> {}
                class Demo {
                    CompBox<Color> okEnum;
                    CompBox<Integer> okInt;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-05",
            category="D2",
            title="Substituição de parâmetros entre parâmetros de classe",
            jls_ref="JLS §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Pair<A, B extends A> {}
                class Demo {
                    Pair<Number, Integer> ok;
                    Pair<Integer, Number> bad;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-06",
            category="D2",
            title="Method reference com type arguments explícitos violando bound",
            jls_ref="JLS §15.13.1 / §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import java.util.function.UnaryOperator;
                class Util {
                    static <T extends Number> T id(T v) { return v; }
                }
                class Demo {
                    void test() {
                        UnaryOperator<String> op = Util::<String>id;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-07",
            category="D2",
            title="Method reference com type arguments explícitos satisfazendo bound",
            jls_ref="JLS §15.13.1 / §4.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import java.util.function.UnaryOperator;
                class Util {
                    static <T extends Number> T id(T v) { return v; }
                }
                class Demo {
                    void test() {
                        UnaryOperator<Integer> op = Util::<Integer>id;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-08",
            category="D2",
            title="Wildcard ? extends String violando bound T extends Number",
            jls_ref="JLS §4.5.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class NumBox<T extends Number> {}
                class Demo {
                    NumBox<? extends String> badWild;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D2-09",
            category="D2",
            title="Bound cíclico direto class Cyc<T extends T>",
            jls_ref="JLS §4.4",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Cyc<T extends T> {}
                class Demo {
                    Cyc<String> x;
                }
                """
            },
        ),

        # ================= D3 — Inner Classes & Static Context =================
        DifferentialCase(
            case_id="D3-01",
            category="D3",
            title="Instanciação qualificada de inner class e static nested em método estático",
            jls_ref="JLS §15.9.2 / §8.1.3",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Outer {
                    class Inner {}
                    static class Nested {}
                    static void ok() {
                        Outer o = new Outer();
                        Inner a = o.new Inner();
                        Nested b = new Outer.Nested();
                    }
                    void inst() {
                        Inner c = new Inner();
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D3-02",
            category="D3",
            title="Instanciação direta de inner class não-static em método estático",
            jls_ref="JLS §15.9.2 / §8.1.3",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer {
                    class Inner {}
                    static void bad() {
                        Inner a = new Inner();
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D3-03",
            category="D3",
            title="Instanciação de inner class por herança dentro de subclasse em método estático",
            jls_ref="JLS §15.9.2",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Base {
                    class Inner {}
                }
                class Sub extends Base {
                    static void bad() {
                        new Inner();
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D3-04",
            category="D3",
            title="Instanciação qualificada o.new StaticNested() proibida pela JLS",
            jls_ref="JLS §15.9",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer {
                    static class Nested {}
                    static void bad() {
                        Outer o = new Outer();
                        o.new Nested();
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D3-05",
            category="D3",
            title="Subclasse anônima de inner class não-static em contexto estático",
            jls_ref="JLS §15.9.2",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer {
                    class Inner {}
                    static void bad() {
                        new Inner() {};
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D3-06",
            category="D3",
            title="Inner class dentro de interface é implicitamente static",
            jls_ref="JLS §9.5 / §8.1.3",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                interface Api {
                    class Impl {}
                }
                class Demo {
                    static void ok() {
                        Api.Impl impl = new Api.Impl();
                    }
                }
                """
            },
        ),

        # ================= D4 — Generic Array Creation =================
        DifferentialCase(
            case_id="D4-01",
            category="D4",
            title="Criação de arrays reificáveis (wildcards ilimitados, raw, primitivos)",
            jls_ref="JLS §4.7 / §15.10.1",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Box<T> {}
                class Demo {
                    void ok() {
                        Box<?>[] a = new Box<?>[2];
                        Box[] b = new Box[2];
                        String[][] c = new String[2][3];
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D4-02",
            category="D4",
            title="Criação de array com tipo parametrizado concreto new Box<String>[2]",
            jls_ref="JLS §15.10.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Box<T> {}
                class Demo {
                    void bad() {
                        Box<String>[] a = new Box<String>[2];
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D4-03",
            category="D4",
            title="Criação de array com wildcard limitado new Box<? extends Number>[2]",
            jls_ref="JLS §4.7 / §15.10.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Box<T> {}
                class Demo {
                    void bad() {
                        Box<? extends Number>[] a = new Box<? extends Number>[2];
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D4-04",
            category="D4",
            title="Criação de array de variável de tipo new T[2]",
            jls_ref="JLS §15.10.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Box<T> {
                    T[] make() {
                        return new T[2];
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D4-05",
            category="D4",
            title="Declaração e cast de array genérico permanecem válidos",
            jls_ref="JLS §4.7 / §5.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Box<T> {}
                class Demo {
                    Box<String>[] ok(Object o) {
                        Box<String>[] arr = (Box<String>[]) o;
                        return arr;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D4-06",
            category="D4",
            title="Array de inner generic aninhado reificável vs não reificável",
            jls_ref="JLS §4.7 / §15.10.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer<T> {
                    class Inner<U> {}
                }
                class Demo {
                    void bad() {
                        Object x = new Outer<String>.Inner<?>[2];
                    }
                }
                """
            },
        ),

        # ================= D5 — Try-With-Resources =================
        DifferentialCase(
            case_id="D5-01",
            category="D5",
            title="TWR válido com AutoCloseable, herança, var e recurso efetivamente final",
            jls_ref="JLS §14.20.3",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import java.io.Closeable;
                class MyRes implements Closeable {
                    public void close() {}
                }
                class Demo {
                    void ok() {
                        MyRes existing = new MyRes();
                        try (MyRes a = new MyRes(); var b = new MyRes(); existing) {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D5-02",
            category="D5",
            title="TWR rejeita tipo não AutoCloseable (String / Object)",
            jls_ref="JLS §14.20.3",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    void bad() {
                        try (String s = "nope") {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D5-03",
            category="D5",
            title="TWR rejeita recurso var com tipo inferido não AutoCloseable",
            jls_ref="JLS §14.20.3",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    void bad() {
                        try (var x = Integer.valueOf(1)) {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D5-04",
            category="D5",
            title="TWR rejeita variável não efetivamente final usada diretamente",
            jls_ref="JLS §14.20.3",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class MyRes implements AutoCloseable {
                    public void close() {}
                }
                class Demo {
                    void bad() {
                        MyRes r = new MyRes();
                        r = new MyRes();
                        try (r) {
                        }
                    }
                }
                """
            },
        ),

        # ================= D6 — Unreachable Code & Enhanced Switch =================
        DifferentialCase(
            case_id="D6-01",
            category="D6",
            title="Instrução inalcançável após return e throw",
            jls_ref="JLS §14.22",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    int bad(boolean b) {
                        if (b) {
                            return 1;
                            int x = 2;
                        }
                        throw new RuntimeException();
                        int y = 3;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-02",
            category="D6",
            title="Exceção de compilação condicional if (false) é permitida pela JLS",
            jls_ref="JLS §14.22",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Demo {
                    int ok() {
                        if (false) {
                            return 0;
                        }
                        return 1;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-03",
            category="D6",
            title="while (false) possui corpo inalcançável",
            jls_ref="JLS §14.22",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    void bad() {
                        while (false) {
                            int x = 1;
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-04",
            category="D6",
            title="while (true) sem break torna código posterior inalcançável",
            jls_ref="JLS §14.22",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    void bad() {
                        while (true) {
                            int x = 1;
                        }
                        int unreachable = 2;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-05",
            category="D6",
            title="Enhanced switch exaustivo com pattern incondicional torna código posterior inalcançável",
            jls_ref="JLS §14.11.2 / §14.22",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    int bad(Object o) {
                        switch (o) {
                            case String s -> { return 1; }
                            case Object x -> { return 2; }
                        }
                        return 3;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-06",
            category="D6",
            title="Enhanced switch exaustivo com pattern incondicional + guard (when flag) + ramo complementar PODE completar normalmente",
            jls_ref="JLS §14.11.2 / §14.22",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Demo {
                    int ok(Object o, boolean flag) {
                        switch (o) {
                            case Object x when flag -> { return 1; }
                            case Object _ -> {}
                        }
                        return 2;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-06b",
            category="D6",
            title="Guard when com lambda dentro de chamada Predicate seguida de '->'",
            jls_ref="JLS §14.11.1 / §14.22",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import java.util.function.Predicate;
                class Demo {
                    boolean eval(Predicate<String> p, String v) { return p.test(v); }
                    int ok(Object o) {
                        switch (o) {
                            case String s when eval(x -> x.length() > 1, s) -> { return 1; }
                            case Object _ -> {}
                        }
                        return 2;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-06c",
            category="D6",
            title="Enhanced switch com pattern guardado e case null sem default/incondicional é NÃO-exaustivo",
            jls_ref="JLS §14.11.2",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    int bad(Object o, boolean flag) {
                        switch (o) {
                            case Object x when flag -> { return 1; }
                            case null -> { return 0; }
                        }
                        return 2;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-07",
            category="D6",
            title="Switch tradicional SEM default pode completar normalmente segundo JLS §14.22",
            jls_ref="JLS §14.22",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Demo {
                    int ok(int x) {
                        switch (x) {
                            case 1: return 10;
                            case 2: return 20;
                        }
                        return 30;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-07b",
            category="D6",
            title="Switch tradicional COM default e sem break NÃO completa normalmente (código posterior inalcançável)",
            jls_ref="JLS §14.22",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    int bad(int x) {
                        switch (x) {
                            case 1: return 10;
                            default: return 20;
                        }
                        return 30;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-08",
            category="D6",
            title="Dominância de pattern em switch (Object antes de String)",
            jls_ref="JLS §14.11.1.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    int bad(Object o) {
                        return switch (o) {
                            case Object x -> 1;
                            case String s -> 2;
                        };
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D6-09",
            category="D6",
            title="try retorna mas finally completa normalmente -> código após try é inalcançável",
            jls_ref="JLS §14.22",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Demo {
                    int bad() {
                        try {
                            return 1;
                        } finally {
                            int x = 2;
                        }
                        return 3;
                    }
                }
                """
            },
        ),

        # ================= D7 — Record Patterns & Primitive Patterns =================
        DifferentialCase(
            case_id="D7-01",
            category="D7",
            title="Record pattern convencional (componentes referência e var) sem Preview",
            jls_ref="JLS §14.30 / JEP 440",
            expected_jls="ACCEPT",
            preview=False,
            files={
                "Demo.java": """
                record Pair(String a, int b) {}
                class Demo {
                    int ok(Object o) {
                        if (o instanceof Pair(String s, var n)) {
                            return s.length() + n;
                        }
                        return 0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-02",
            category="D7",
            title="Record pattern com componente primitivo exato sem Preview (regra Java 26 / JEP 530 do projeto)",
            jls_ref="JEP 530 (Preview Java 26) — atenção à diferença potencial entre JEP 440 e JEP 530 no javac 26",
            expected_jls="REJECT",
            preview=False,
            note="Verificar explicitamente com javac 26: JEP 440 (Java 21) já permitia P(int x) exato sem preview, enquanto JEP 530 estende padrões primitivos.",
            files={
                "Demo.java": """
                record Point(int x, int y) {}
                class Demo {
                    int test(Object o) {
                        if (o instanceof Point(int x, int y)) {
                            return x + y;
                        }
                        return 0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-03",
            category="D7",
            title="Record pattern com componente primitivo exato COM Preview",
            jls_ref="JEP 530 (--enable-preview --release 26)",
            expected_jls="ACCEPT",
            preview=True,
            files={
                "Demo.java": """
                record Point(int x, int y) {}
                class Demo {
                    int test(Object o) {
                        if (o instanceof Point(int x, int y)) {
                            return x + y;
                        }
                        return 0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-04",
            category="D7",
            title="Record pattern com conversão primitiva (double x para int) SEM Preview",
            jls_ref="JEP 530 (Preview)",
            expected_jls="REJECT",
            preview=False,
            files={
                "Demo.java": """
                record Point(int x, int y) {}
                class Demo {
                    double bad(Object o) {
                        if (o instanceof Point(double x, double y)) {
                            return x + y;
                        }
                        return 0.0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-05",
            category="D7",
            title="Record pattern com conversão primitiva (double x para int) COM Preview",
            jls_ref="JEP 530 (--enable-preview --release 26)",
            expected_jls="ACCEPT",
            preview=True,
            files={
                "Demo.java": """
                record Point(int x, int y) {}
                class Demo {
                    double ok(Object o) {
                        if (o instanceof Point(double x, double y)) {
                            return x + y;
                        }
                        return 0.0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-06",
            category="D7",
            title="Pattern primitivo top-level sem Preview vs com Preview",
            jls_ref="JEP 530 (Preview)",
            expected_jls="REJECT",
            preview=False,
            files={
                "Demo.java": """
                class Demo {
                    boolean bad(int v) {
                        return v instanceof double d;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-07",
            category="D7",
            title="Pattern primitivo top-level COM Preview",
            jls_ref="JEP 530 (--enable-preview --release 26)",
            expected_jls="ACCEPT",
            preview=True,
            files={
                "Demo.java": """
                class Demo {
                    double ok(int v) {
                        if (v instanceof double d) {
                            return d;
                        }
                        return 0.0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-08",
            category="D7",
            title="Aridade errada em record pattern",
            jls_ref="JLS §14.30.1",
            expected_jls="REJECT",
            preview=True,
            files={
                "Demo.java": """
                record Point(int x, int y) {}
                class Demo {
                    int bad(Object o) {
                        if (o instanceof Point(int x)) {
                            return x;
                        }
                        return 0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D7-09",
            category="D7",
            title="Tipo incompatível em componente de record pattern",
            jls_ref="JLS §14.30.1",
            expected_jls="REJECT",
            preview=True,
            files={
                "Demo.java": """
                record Box(String s) {}
                class Demo {
                    int bad(Object o) {
                        if (o instanceof Box(Integer i)) {
                            return i;
                        }
                        return 0;
                    }
                }
                """
            },
        ),

        # ================= D8 — import module & Module System =================
        DifferentialCase(
            case_id="D8-01",
            category="D8",
            title="import module java.base resolve pacotes exportados (util, io, math, nio.file)",
            jls_ref="JLS §7.5.5 / JEP 511",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import module java.base;
                class Demo {
                    List<String> list;
                    Optional<BigDecimal> opt;
                    Path path;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-02",
            category="D8",
            title="module continua sendo palavra-chave contextual fora de declarações modulares",
            jls_ref="JLS §3.9",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Demo {
                    int module = 7;
                    int getModule(int module) {
                        return module + 1;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-03",
            category="D8",
            title="import module java.sql inclui requires transitive (java.xml, java.logging)",
            jls_ref="JLS §7.5.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import module java.sql;
                class Demo {
                    Connection conn;
                    Logger logger;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-04",
            category="D8",
            title="Ambiguidade entre import module java.base e import module java.desktop (List)",
            jls_ref="JLS §7.5.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import module java.base;
                import module java.desktop;
                class Demo {
                    List x;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-05",
            category="D8",
            title="Ambiguidade em único import module (Element em java.desktop) resolvida por import explícito",
            jls_ref="JLS §7.5.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import module java.desktop;
                class Demo {
                    Element el;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-06",
            category="D8",
            title="Resolução de ambiguidade via single-type import explícito",
            jls_ref="JLS §7.5.1 / §7.5.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import module java.base;
                import module java.desktop;
                import java.util.List;
                class Demo {
                    List<String> x;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-07",
            category="D8",
            title="Ambiguidade entre import module java.base e import java.sql.* (Date)",
            jls_ref="JLS §7.5.2 / §7.5.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import module java.base;
                import java.sql.*;
                class Demo {
                    Date d;
                }
                """
            },
        ),
        DifferentialCase(
            case_id="D8-08",
            category="D8",
            title="Multi-módulo interno com exports e requires",
            jls_ref="JLS §7.7 / §7.5.5",
            expected_jls="ACCEPT",
            module_source_path=True,
            files={
                "app.core/module-info.java": "module app.core { exports app.core.api; }",
                "app.core/app/core/api/Service.java": """
                package app.core.api;
                public class Service {
                    public int ping() { return 42; }
                }
                """,
                "app.cli/module-info.java": "module app.cli { requires app.core; }",
                "app.cli/app/cli/Client.java": """
                package app.cli;
                import module app.core;
                public class Client {
                    public int run(Service s) { return s.ping(); }
                }
                """,
            },
        ),
        DifferentialCase(
            case_id="D8-09",
            category="D8",
            title="Módulo sintético exportando dois pacotes com mesmo nome público gera ambiguidade",
            jls_ref="JLS §7.5.5",
            expected_jls="REJECT",
            module_source_path=True,
            files={
                "app.multi/module-info.java": "module app.multi { exports p1; exports p2; }",
                "app.multi/p1/Element.java": "package p1; public class Element {}",
                "app.multi/p2/Element.java": "package p2; public class Element {}",
                "app.cli/module-info.java": "module app.cli { requires app.multi; }",
                "app.cli/cli/Consumer.java": """
                package cli;
                import module app.multi;
                public class Consumer {
                    Element el;
                }
                """,
            },
        ),

        # ================= Cross-Feature Interactions =================
        DifferentialCase(
            case_id="INT-01",
            category="INTERACTION",
            title="D1+D2+D7: Record pattern genérico com violação de bound",
            jls_ref="JLS §4.5 / §14.30",
            expected_jls="REJECT",
            preview=True,
            files={
                "Demo.java": """
                record NumBox<T extends Number>(T val) {}
                class Demo {
                    void bad(Object o) {
                        if (o instanceof NumBox<String>(String s)) {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-02",
            category="INTERACTION",
            title="D1+D2+D7: Record pattern genérico com bound válido",
            jls_ref="JLS §4.5 / §14.30",
            expected_jls="ACCEPT",
            preview=True,
            files={
                "Demo.java": """
                record NumBox<T extends Number>(T val) {}
                class Demo {
                    int ok(Object o) {
                        if (o instanceof NumBox<Integer>(Integer n)) {
                            return n;
                        }
                        return 0;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-03",
            category="INTERACTION",
            title="D1+D4: Array genérico com aridade inválida new Box<String, Integer>[2]",
            jls_ref="JLS §4.5 / §15.10.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Box<T> {}
                class Demo {
                    void bad() {
                        Object a = new Box<String, Integer>[2];
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-04",
            category="INTERACTION",
            title="D2+D5: Try-with-resources com recurso genérico violando bound",
            jls_ref="JLS §4.5 / §14.20.3",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class NumRes<T extends Number> implements AutoCloseable {
                    public void close() {}
                }
                class Demo {
                    void bad() {
                        try (NumRes<String> r = new NumRes<>()) {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-05",
            category="INTERACTION",
            title="D2+D5: Try-with-resources com recurso genérico respeitando bound",
            jls_ref="JLS §4.5 / §14.20.3",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class NumRes<T extends Number> implements AutoCloseable {
                    public void close() {}
                }
                class Demo {
                    void ok() {
                        try (NumRes<Integer> r = new NumRes<>()) {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-06",
            category="INTERACTION",
            title="D3+D1+D2: Inner class genérica instanciada em contexto estático via enclosing válido vs inválido",
            jls_ref="JLS §15.9.2 / §4.5",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                class Outer<T extends Number> {
                    class Inner<U extends T> {}
                    static void bad() {
                        Outer<Integer> o = new Outer<>();
                        Inner<Integer> i = new Inner<>();
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-07",
            category="INTERACTION",
            title="D6+D7: Switch com record pattern primitivo exaustivo + código inalcançável após switch",
            jls_ref="JLS §14.11.2 / §14.22 / JEP 530",
            expected_jls="REJECT",
            preview=True,
            files={
                "Demo.java": """
                record Point(int x, int y) {}
                class Demo {
                    int bad(Object o) {
                        switch (o) {
                            case Point(int x, int y) -> { return x + y; }
                            case Object other -> { return -1; }
                        }
                        return 99;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-08",
            category="INTERACTION",
            title="D8+D1+D5: import module java.base com List<String> e BufferedReader em TWR",
            jls_ref="JLS §7.5.5 / §4.5 / §14.20.3",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import module java.base;
                class Demo {
                    void ok() throws Exception {
                        List<String> items = null;
                        BufferedReader br = null;
                        try (br) {
                        }
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="INT-09",
            category="INTERACTION",
            title="D8+D5: import module java.base + Path em TWR deve ser rejeitado (Path não é AutoCloseable)",
            jls_ref="JLS §7.5.5 / §14.20.3",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import module java.base;
                class Demo {
                    void bad() {
                        Path p = null;
                        try (p) {
                        }
                    }
                }
                """
            },
        ),

        # ================= Adversarial =================
        DifferentialCase(
            case_id="ADV-01",
            category="ADVERSARIAL",
            title="Diamond anônimo e captura de instância em retorno de lambda",
            jls_ref="JLS §15.9.5 / §4.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Box<T> {
                    T val;
                    Box(T val) { this.val = val; }
                }
                class Demo {
                    Box<String> make() {
                        return new Box<>("ok") {};
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="ADV-02",
            category="ADVERSARIAL",
            title="Switch expression com break/yield e switch aninhado exaustivo",
            jls_ref="JLS §14.11.2 / §14.22",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                class Demo {
                    int nested(Object o) {
                        int r = switch (o) {
                            case String s -> {
                                yield s.length();
                            }
                            default -> 0;
                        };
                        return r;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="ADV-03",
            category="ADVERSARIAL",
            title="Method reference Outer.Inner::new com Supplier<Outer.Inner> sem instância enclosing",
            jls_ref="JLS §15.13.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import java.util.function.Supplier;
                class Outer {
                    class Inner {}
                    static void bad() {
                        Supplier<Inner> s = Inner::new;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="ADV-04",
            category="ADVERSARIAL",
            title="Constructor reference de inner class com Function<Outer, Inner> em contexto estático é rejeitado (JLS §15.13.1)",
            jls_ref="JLS §15.13.1",
            expected_jls="REJECT",
            files={
                "Demo.java": """
                import java.util.function.Function;
                class Outer {
                    class Inner {}
                    static void bad() {
                        Function<Outer, Inner> fn = Inner::new;
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="ADV-04b",
            category="ADVERSARIAL",
            title="Lambda com instanciação qualificada o -> o.new Inner() para Function<Outer, Inner> é válida",
            jls_ref="JLS §15.9 / §15.27",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import java.util.function.Function;
                class Outer {
                    class Inner {}
                    static void ok() {
                        Function<Outer, Inner> fn = o -> o.new Inner();
                    }
                }
                """
            },
        ),
        DifferentialCase(
            case_id="ADV-05",
            category="ADVERSARIAL",
            title="import module redundante no mesmo arquivo é aceito sem ambiguidade",
            jls_ref="JLS §7.5.5",
            expected_jls="ACCEPT",
            files={
                "Demo.java": """
                import module java.base;
                import module java.base;
                class Demo {
                    List<String> xs;
                }
                """
            },
        ),
    ]


def execute_matrix(
    cases: Sequence[DifferentialCase],
    javac_info: JavacInfo,
) -> List[CaseExecutionResult]:
    results: List[CaseExecutionResult] = []
    for case in cases:
        own_verdict, own_errors, own_unresolved = run_own_compiler(case)
        javac_verdict: Optional[str] = None
        javac_exit: Optional[int] = None
        javac_output = ""
        if javac_info.available and javac_info.is_jdk26 and javac_info.path:
            javac_verdict, javac_exit, javac_output = run_javac_oracle(case, javac_info.path)
        classification = classify_differential(own_verdict, javac_verdict)
        jls_alignment = "OK" if own_verdict == case.expected_jls else f"DIVERGE_ESPERADO_JLS({case.expected_jls})"
        results.append(
            CaseExecutionResult(
                case=case,
                own_verdict=own_verdict,
                own_errors=own_errors,
                own_unresolved=own_unresolved,
                javac_verdict=javac_verdict,
                javac_exit_code=javac_exit,
                javac_output=javac_output,
                classification=classification,
                jls_alignment=jls_alignment,
            )
        )
    return results


def summarize_results(results: Sequence[CaseExecutionResult], javac_info: JavacInfo) -> Dict[str, object]:
    counts: Dict[str, int] = {
        "CONCORDÂNCIA": 0,
        "FALSO ACEITE": 0,
        "FALSA REJEIÇÃO": 0,
        "INCONCLUSIVO": 0,
    }
    jls_mismatches: List[str] = []
    for r in results:
        counts[r.classification] = counts.get(r.classification, 0) + 1
        if r.jls_alignment != "OK":
            jls_mismatches.append(r.case.case_id)

    return {
        "total_cases": len(results),
        "jdk26_oracle_available": bool(javac_info.available and javac_info.is_jdk26),
        "javac_version": javac_info.version_text or None,
        "javac_path": javac_info.path,
        "javac_reason": javac_info.reason,
        "classifications": counts,
        "jls_mismatches": jls_mismatches,
    }


def format_markdown_report(results: Sequence[CaseExecutionResult], javac_info: JavacInfo) -> str:
    summary = summarize_results(results, javac_info)
    lines: List[str] = []
    lines.append("# Relatório de Execução — Validação Diferencial D1–D8")
    lines.append("")
    if javac_info.is_jdk26:
        lines.append(f"- Oráculo JDK 26: **{javac_info.version_text}** (`{javac_info.path}`)")
    else:
        lines.append(f"- Oráculo JDK 26: **INDISPONÍVEL** ({javac_info.reason})")
        lines.append("- Modo de execução: **Validação parcial** (compilador próprio vs expectativa normativa JLS 26; comparação com `javac` marcada como `INCONCLUSIVO`).")
    lines.append(f"- Total de casos executados: **{summary['total_cases']}**")
    lines.append(f"- Classificação diferencial: `{summary['classifications']}`")
    lines.append(f"- Divergências vs expectativa JLS 26 no compilador próprio: `{summary['jls_mismatches']}`")
    lines.append("")
    lines.append("| ID | Categoria | Preview | Esperado JLS | Compilador Próprio | `javac` 26 | Classificação | Alinhamento JLS |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        jv = r.javac_verdict if r.javac_verdict is not None else "AUSENTE"
        lines.append(
            f"| {r.case.case_id} | {r.case.category} | {'Sim' if r.case.preview else 'Não'} "
            f"| {r.case.expected_jls} | {r.own_verdict} | {jv} | {r.classification} | {r.jls_alignment} |"
        )
    mismatches = [r for r in results if r.jls_alignment != "OK" or r.classification in ("FALSO ACEITE", "FALSA REJEIÇÃO")]
    if mismatches:
        lines.append("")
        lines.append("## Detalhes de Divergências / Falhas Observadas")
        for r in mismatches:
            lines.append(f"### {r.case.case_id} — {r.case.title}")
            lines.append(f"- JLS: {r.case.jls_ref} | Esperado: `{r.case.expected_jls}` | Compilador próprio: `{r.own_verdict}` | `javac`: `{r.javac_verdict}`")
            if r.own_errors:
                lines.append("- Erros próprios:")
                for err in r.own_errors:
                    lines.append(f"  - `{err}`")
            if r.own_unresolved:
                lines.append("- Unresolved checks:")
                for u in r.own_unresolved:
                    lines.append(f"  - `{u}`")
            if r.javac_output:
                lines.append(f"- Saída javac:\n```text\n{r.javac_output}\n```")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validação diferencial D1–D8 (compilador_base_av3 vs JDK 26 javac).")
    parser.add_argument("--javac", help="Caminho explícito para o binário javac do JDK 26.")
    parser.add_argument("--filter", help="Filtra case_id ou category por substring (case-insensitive).")
    parser.add_argument("--json", help="Salva resultado detalhado em JSON no caminho informado.")
    parser.add_argument("--require-oracle", action="store_true", help="Falha com exit code 2 se JDK 26 javac não estiver disponível.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    javac_info = discover_jdk26_javac(args.javac)
    cases = build_differential_matrix()
    if args.filter:
        needle = args.filter.lower()
        cases = [c for c in cases if needle in c.case_id.lower() or needle in c.category.lower() or needle in c.title.lower()]

    results = execute_matrix(cases, javac_info)
    print(format_markdown_report(results, javac_info))

    if args.json:
        payload = {
            "summary": summarize_results(results, javac_info),
            "results": [
                {
                    "case_id": r.case.case_id,
                    "category": r.case.category,
                    "title": r.case.title,
                    "jls_ref": r.case.jls_ref,
                    "preview": r.case.preview,
                    "expected_jls": r.case.expected_jls,
                    "own_verdict": r.own_verdict,
                    "own_errors": r.own_errors,
                    "own_unresolved": r.own_unresolved,
                    "javac_verdict": r.javac_verdict,
                    "javac_exit_code": r.javac_exit_code,
                    "javac_output": r.javac_output,
                    "classification": r.classification,
                    "jls_alignment": r.jls_alignment,
                }
                for r in results
            ],
        }
        Path(args.json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.require_oracle and not javac_info.is_jdk26:
        return 2
    summary = summarize_results(results, javac_info)
    if summary["jls_mismatches"] or summary["classifications"]["FALSO ACEITE"] or summary["classifications"]["FALSA REJEIÇÃO"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
