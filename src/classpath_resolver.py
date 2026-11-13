"""
Módulo de Resolução Externa (JDK / Classpath / JARs / JMODs / .class) — Etapa S16.

Implementa leitura estática de metadados de arquivos `.class` conforme a
Java Virtual Machine Specification (JVMS §4), decodificação de descritores e
assinaturas genéricas (JVMS §4.3 e §4.7.9.1) e indexação preguiçosa de JARs,
JMODs, diretórios de classes e bibliotecas padrão Java (rt.jar / jmods) sem
executar bytecode arbitrário do classpath.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import struct
import zipfile
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# Versões principais suportadas por formato .class (JVMS §4.1)
CLASS_MAJOR_TO_JAVA: Dict[int, str] = {
    45: "1.1",
    46: "1.2",
    47: "1.3",
    48: "1.4",
    49: "5",
    50: "6",
    51: "7",
    52: "8",
    53: "9",
    54: "10",
    55: "11",
    56: "12",
    57: "13",
    58: "14",
    59: "15",
    60: "16",
    61: "17",
    62: "18",
    63: "19",
    64: "20",
    65: "21",
    66: "22",
    67: "23",
    68: "24",
    69: "25",
    70: "26",
}

JAVA_TO_CLASS_MAJOR: Dict[int, int] = {
    5: 49, 6: 50, 7: 51, 8: 52, 9: 53, 10: 54, 11: 55, 12: 56, 13: 57,
    14: 58, 15: 59, 16: 60, 17: 61, 18: 62, 19: 63, 20: 64, 21: 65,
    22: 66, 23: 67, 24: 68, 25: 69, 26: 70,
}

DEFAULT_MAX_CLASS_MAJOR = 70  # Java SE 26

# Tags da Constant Pool (JVMS §4.4)
CP_UTF8 = 1
CP_INTEGER = 3
CP_FLOAT = 4
CP_LONG = 5
CP_DOUBLE = 6
CP_CLASS = 7
CP_STRING = 8
CP_FIELDREF = 9
CP_METHODREF = 10
CP_INTERFACE_METHODREF = 11
CP_NAME_AND_TYPE = 12
CP_METHOD_HANDLE = 15
CP_METHOD_TYPE = 16
CP_DYNAMIC = 17
CP_INVOKE_DYNAMIC = 18
CP_MODULE = 19
CP_PACKAGE = 20

# Flags de acesso (JVMS §4.1, §4.5, §4.6, §4.7.6)
ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_SUPER = 0x0020
ACC_SYNCHRONIZED = 0x0020
ACC_BRIDGE = 0x0040
ACC_VOLATILE = 0x0040
ACC_TRANSIENT = 0x0080
ACC_VARARGS = 0x0080
ACC_NATIVE = 0x0100
ACC_INTERFACE = 0x0200
ACC_ABSTRACT = 0x0400
ACC_STRICT = 0x0800
ACC_SYNTHETIC = 0x1000
ACC_ANNOTATION = 0x2000
ACC_ENUM = 0x4000
ACC_MODULE = 0x8000


class ClassFormatError(Exception):
    """Erro estrutural ao decodificar um arquivo .class."""


class ClassVersionError(ClassFormatError):
    """Incompatibilidade de versão do classfile acima do alvo configurado."""

    def __init__(self, message: str, major: int, minor: int, max_major: int):
        super().__init__(message)
        self.major = major
        self.minor = minor
        self.max_major = max_major


@dataclass
class ExternalFieldInfo:
    """Metadados de campo lidos estaticamente do bytecode."""

    name: str
    type: str
    raw_type: str
    is_static: bool = False
    is_final: bool = False
    access: str = "package"
    modifiers: List[str] = field(default_factory=list)
    constant_value: Optional[Tuple[str, Any]] = None


@dataclass
class ExternalMethodInfo:
    """Metadados de método ou construtor lidos estaticamente do bytecode."""

    name: str
    is_constructor: bool = False
    params: List[str] = field(default_factory=list)
    ret: str = "void"
    static: bool = False
    varargs: bool = False
    tparams: List[str] = field(default_factory=list)
    tparam_bounds: Dict[str, List[str]] = field(default_factory=dict)
    throws: List[str] = field(default_factory=list)
    access: str = "package"
    modifiers: List[str] = field(default_factory=list)
    is_abstract: bool = False
    is_final: bool = False
    is_default: bool = False


@dataclass
class ExternalTypeInfo:
    """Metadados completos de classe, interface, enum ou record externo."""

    fqn: str
    internal_name: str
    package: str
    simple_name: str
    kind: str  # 'class' | 'interface' | 'enum' | 'record' | 'annotation_interface'
    modifiers: List[str] = field(default_factory=list)
    access: str = "package"
    is_final: bool = False
    is_abstract: bool = False
    is_nested: bool = False
    enclosing_fqn: Optional[str] = None
    top_level_fqn: Optional[str] = None
    type_parameters: List[Tuple[str, List[str]]] = field(default_factory=list)
    super_class: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    fields: Dict[str, ExternalFieldInfo] = field(default_factory=dict)
    methods: Dict[str, List[ExternalMethodInfo]] = field(default_factory=dict)
    constructors: List[ExternalMethodInfo] = field(default_factory=list)
    major_version: int = 52
    minor_version: int = 0
    java_version: str = "8"
    source_origin: str = ""


@dataclass
class ClasspathDiagnostic:
    """Diagnóstico não-executável produzido durante indexação ou leitura de bytecode."""

    kind: str  # 'missing_entry' | 'unsupported_class_version' | 'corrupt_classfile' | 'jimage_unsupported'
    message: str
    target: Optional[str] = None


def _internal_to_fqn(internal_name: str) -> str:
    """Converte nome interno JVM ('java/util/Map$Entry') para FQN Java ('java.util.Map.Entry')."""
    if not internal_name:
        return ""
    if internal_name.startswith("["):
        return SignatureDecoder.parse_field_descriptor(internal_name)
    return internal_name.replace("/", ".").replace("$", ".")


def _access_from_flags(flags: int) -> str:
    if flags & ACC_PUBLIC:
        return "public"
    if flags & ACC_PROTECTED:
        return "protected"
    if flags & ACC_PRIVATE:
        return "private"
    return "package"


def _modifiers_from_flags(flags: int, is_type: bool = False) -> List[str]:
    mods: List[str] = []
    if flags & ACC_PUBLIC:
        mods.append("public")
    elif flags & ACC_PROTECTED:
        mods.append("protected")
    elif flags & ACC_PRIVATE:
        mods.append("private")
    if flags & ACC_STATIC:
        mods.append("static")
    if flags & ACC_FINAL:
        mods.append("final")
    if flags & ACC_ABSTRACT:
        mods.append("abstract")
    if not is_type:
        if flags & ACC_SYNCHRONIZED:
            mods.append("synchronized")
        if flags & ACC_NATIVE:
            mods.append("native")
        if flags & ACC_STRICT:
            mods.append("strictfp")
    return mods


class SignatureDecoder:
    """Decodificador recursivo para descritores e assinaturas genéricas JVMS §4.3 / §4.7.9.1."""

    PRIMITIVES = {
        "B": "byte",
        "C": "char",
        "D": "double",
        "F": "float",
        "I": "int",
        "J": "long",
        "S": "short",
        "Z": "boolean",
        "V": "void",
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < self.length else ""

    def consume(self, expected: Optional[str] = None) -> str:
        if self.pos >= self.length:
            raise ClassFormatError(f"Assinatura JVM truncada: '{self.text}'")
        ch = self.text[self.pos]
        if expected is not None and ch != expected:
            raise ClassFormatError(f"Esperado '{expected}' em '{self.text}', encontrado '{ch}' na posição {self.pos}")
        self.pos += 1
        return ch

    def read_until(self, stop_chars: Set[str]) -> str:
        start = self.pos
        while self.pos < self.length and self.text[self.pos] not in stop_chars:
            self.pos += 1
        return self.text[start:self.pos]

    @classmethod
    def parse_field_descriptor(cls, desc: str) -> str:
        dec = cls(desc)
        return dec.parse_java_type_signature()

    @classmethod
    def parse_method_descriptor(cls, desc: str) -> Tuple[List[str], str]:
        dec = cls(desc)
        dec.consume("(")
        params: List[str] = []
        while dec.peek() and dec.peek() != ")":
            params.append(dec.parse_java_type_signature())
        dec.consume(")")
        ret = dec.parse_java_type_signature()
        return params, ret

    @classmethod
    def parse_class_signature(cls, sig: str) -> Tuple[List[Tuple[str, List[str]]], str, List[str]]:
        dec = cls(sig)
        tparams = dec.parse_formal_type_parameters() if dec.peek() == "<" else []
        super_type = dec.parse_class_type_signature()
        ifaces: List[str] = []
        while dec.pos < dec.length:
            ifaces.append(dec.parse_class_type_signature())
        return tparams, super_type, ifaces

    @classmethod
    def parse_method_signature(
        cls, sig: str
    ) -> Tuple[List[Tuple[str, List[str]]], List[str], str, List[str]]:
        dec = cls(sig)
        tparams = dec.parse_formal_type_parameters() if dec.peek() == "<" else []
        dec.consume("(")
        params: List[str] = []
        while dec.peek() and dec.peek() != ")":
            params.append(dec.parse_java_type_signature())
        dec.consume(")")
        ret = dec.parse_java_type_signature()
        throws: List[str] = []
        while dec.peek() == "^":
            dec.consume("^")
            if dec.peek() == "L":
                throws.append(dec.parse_class_type_signature())
            elif dec.peek() == "T":
                throws.append(dec.parse_type_variable_signature())
            else:
                break
        return tparams, params, ret, throws

    def parse_formal_type_parameters(self) -> List[Tuple[str, List[str]]]:
        self.consume("<")
        out: List[Tuple[str, List[str]]] = []
        while self.peek() and self.peek() != ">":
            name = self.read_until({":"})
            self.consume(":")
            bounds: List[str] = []
            # ClassBound é opcional antes de ':' (ex: <T::Ljava/io/Serializable;>)
            if self.peek() not in (":", ">"):
                cb = self.parse_field_type_signature()
                if cb:
                    bounds.append(cb)
            while self.peek() == ":":
                self.consume(":")
                ib = self.parse_field_type_signature()
                if ib:
                    bounds.append(ib)
            if not bounds:
                bounds.append("java.lang.Object")
            out.append((name, bounds))
        self.consume(">")
        return out

    def parse_java_type_signature(self) -> str:
        ch = self.peek()
        if ch in self.PRIMITIVES:
            self.pos += 1
            return self.PRIMITIVES[ch]
        return self.parse_field_type_signature()

    def parse_field_type_signature(self) -> str:
        ch = self.peek()
        if ch == "L":
            return self.parse_class_type_signature()
        if ch == "[":
            dims = 0
            while self.peek() == "[":
                self.pos += 1
                dims += 1
            elem = self.parse_java_type_signature()
            return elem + ("[]" * dims)
        if ch == "T":
            return self.parse_type_variable_signature()
        raise ClassFormatError(f"Token inesperado '{ch}' em assinatura '{self.text}' na posição {self.pos}")

    def parse_type_variable_signature(self) -> str:
        self.consume("T")
        name = self.read_until({";"})
        self.consume(";")
        return name

    def parse_class_type_signature(self) -> str:
        self.consume("L")
        raw_base = self.read_until({"<", ";", "."})
        base = _internal_to_fqn(raw_base)
        result = base
        if self.peek() == "<":
            args = self.parse_type_arguments()
            if args:
                result = f"{result}<{', '.join(args)}>"
        while self.peek() == ".":
            self.consume(".")
            seg = self.read_until({"<", ";", "."})
            seg_clean = seg.replace("$", ".")
            result = f"{result}.{seg_clean}"
            if self.peek() == "<":
                args = self.parse_type_arguments()
                if args:
                    result = f"{result}<{', '.join(args)}>"
        self.consume(";")
        return result

    def parse_type_arguments(self) -> List[str]:
        self.consume("<")
        args: List[str] = []
        while self.peek() and self.peek() != ">":
            ch = self.peek()
            if ch == "*":
                self.pos += 1
                args.append("?")
            elif ch == "+":
                self.pos += 1
                args.append(f"? extends {self.parse_field_type_signature()}")
            elif ch == "-":
                self.pos += 1
                args.append(f"? super {self.parse_field_type_signature()}")
            else:
                args.append(self.parse_field_type_signature())
        self.consume(">")
        return args


class _ByteReader:
    """Leitor sequencial big-endian seguro sobre buffer binário de .class."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.length = len(data)

    def read_u1(self) -> int:
        if self.pos + 1 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (u1).")
        val = self.data[self.pos]
        self.pos += 1
        return val

    def read_u2(self) -> int:
        if self.pos + 2 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (u2).")
        val = struct.unpack_from(">H", self.data, self.pos)[0]
        self.pos += 2
        return val

    def read_u4(self) -> int:
        if self.pos + 4 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (u4).")
        val = struct.unpack_from(">I", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_i4(self) -> int:
        if self.pos + 4 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (i4).")
        val = struct.unpack_from(">i", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_i8(self) -> int:
        if self.pos + 8 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (i8).")
        val = struct.unpack_from(">q", self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_f4(self) -> float:
        if self.pos + 4 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (f4).")
        val = struct.unpack_from(">f", self.data, self.pos)[0]
        self.pos += 4
        return val

    def read_f8(self) -> float:
        if self.pos + 8 > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (f8).")
        val = struct.unpack_from(">d", self.data, self.pos)[0]
        self.pos += 8
        return val

    def read_bytes(self, n: int) -> bytes:
        if self.pos + n > self.length:
            raise ClassFormatError("Fim inesperado do arquivo .class (bytes).")
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out


class ClassFileParser:
    """Parser estático completo de arquivos .class segundo JVMS §4."""

    MAGIC = 0xCAFEBABE

    @classmethod
    def parse_bytes(
        cls,
        data: bytes,
        source_origin: str = "",
        max_class_major: int = DEFAULT_MAX_CLASS_MAJOR,
    ) -> ExternalTypeInfo:
        reader = _ByteReader(data)
        magic = reader.read_u4()
        if magic != cls.MAGIC:
            raise ClassFormatError(f"Cabeçalho mágico inválido 0x{magic:08X} (esperado 0xCAFEBABE).")

        minor = reader.read_u2()
        major = reader.read_u2()
        if major < 45:
            raise ClassVersionError(
                f"Versão principal de bytecode inválida: {major}.{minor}.",
                major=major,
                minor=minor,
                max_major=max_class_major,
            )
        if major > max_class_major:
            found_ver = CLASS_MAJOR_TO_JAVA.get(major, f"major {major}")
            target_ver = CLASS_MAJOR_TO_JAVA.get(max_class_major, f"major {max_class_major}")
            raise ClassVersionError(
                f"Incompatibilidade de versão de bytecode: arquivo .class compilado para Java {found_ver} (major {major}.{minor}), acima do máximo configurado Java {target_ver} (major {max_class_major}).",
                major=major,
                minor=minor,
                max_major=max_class_major,
            )

        cp = cls._read_constant_pool(reader)

        access_flags = reader.read_u2()
        this_idx = reader.read_u2()
        super_idx = reader.read_u2()

        this_internal = cls._cp_class_name(cp, this_idx)
        super_internal = cls._cp_class_name(cp, super_idx) if super_idx != 0 else None

        ifaces_count = reader.read_u2()
        iface_internals: List[str] = [cls._cp_class_name(cp, reader.read_u2()) for _ in range(ifaces_count)]

        fqn = _internal_to_fqn(this_internal)
        simple_name = fqn.split(".")[-1] if fqn else ""
        if "." in this_internal.replace("/", "."):
            pkg = this_internal.rsplit("/", 1)[0].replace("/", ".") if "/" in this_internal else ""
        else:
            pkg = this_internal.rsplit("/", 1)[0].replace("/", ".") if "/" in this_internal else ""

        # Leitura preliminar de campos e métodos
        fields_raw = cls._read_members(reader, cp)
        methods_raw = cls._read_members(reader, cp)
        class_attrs = cls._read_attributes(reader, cp)

        # Resolve metadados adicionais de atributos da classe
        class_sig = class_attrs.get("Signature")
        inner_classes = class_attrs.get("InnerClasses", [])
        has_record_attr = "Record" in class_attrs

        # Ajusta modificadores de InnerClasses quando disponíveis
        eff_flags = access_flags
        is_nested = "$" in this_internal
        enclosing_fqn: Optional[str] = None
        top_level_fqn: str = fqn
        for ic in inner_classes:
            if ic["inner_name"] == this_internal:
                eff_flags = ic["access_flags"]
                if ic["outer_name"]:
                    enclosing_fqn = _internal_to_fqn(ic["outer_name"])
                    is_nested = True
                break
        if "$" in this_internal:
            top_internal = this_internal.split("$", 1)[0]
            top_level_fqn = _internal_to_fqn(top_internal)

        if eff_flags & ACC_ANNOTATION:
            kind = "annotation_interface"
        elif eff_flags & ACC_INTERFACE:
            kind = "interface"
        elif eff_flags & ACC_ENUM:
            kind = "enum"
        elif has_record_attr or super_internal == "java/lang/Record":
            kind = "record"
        else:
            kind = "class"

        modifiers = _modifiers_from_flags(eff_flags, is_type=True)
        access = _access_from_flags(eff_flags)
        is_final = bool(eff_flags & ACC_FINAL) or kind in ("enum", "record")
        is_abstract = bool(eff_flags & ACC_ABSTRACT) or kind in ("interface", "annotation_interface")

        type_parameters: List[Tuple[str, List[str]]] = []
        super_fqn = _internal_to_fqn(super_internal) if super_internal else None
        iface_fqns = [_internal_to_fqn(i) for i in iface_internals if i]

        if class_sig:
            try:
                tparams, sig_sup, sig_ifaces = SignatureDecoder.parse_class_signature(class_sig)
                type_parameters = tparams
                if super_internal is not None:
                    super_fqn = sig_sup
                if sig_ifaces:
                    iface_fqns = sig_ifaces
            except ClassFormatError:
                pass

        # Processa campos
        fields: Dict[str, ExternalFieldInfo] = {}
        for f in fields_raw:
            fflags = f["access_flags"]
            if fflags & ACC_SYNTHETIC:
                continue
            fname = f["name"]
            raw_ftype = SignatureDecoder.parse_field_descriptor(f["descriptor"])
            gen_ftype = raw_ftype
            fattrs = f["attributes"]
            if "Signature" in fattrs:
                try:
                    gen_ftype = SignatureDecoder(fattrs["Signature"]).parse_field_type_signature()
                except ClassFormatError:
                    gen_ftype = raw_ftype

            const_val = None
            if "ConstantValue" in fattrs and (fflags & ACC_STATIC) and (fflags & ACC_FINAL):
                const_val = cls._normalize_constant_value(raw_ftype, fattrs["ConstantValue"])

            if kind == "interface":
                f_access = "public"
                f_static = True
                f_final = True
            else:
                f_access = _access_from_flags(fflags)
                f_static = bool(fflags & ACC_STATIC)
                f_final = bool(fflags & ACC_FINAL)

            fields[fname] = ExternalFieldInfo(
                name=fname,
                type=gen_ftype,
                raw_type=raw_ftype,
                is_static=f_static,
                is_final=f_final,
                access=f_access,
                modifiers=_modifiers_from_flags(fflags, is_type=False),
                constant_value=const_val,
            )

        # Processa métodos e construtores
        methods: Dict[str, List[ExternalMethodInfo]] = {}
        constructors: List[ExternalMethodInfo] = []
        for m in methods_raw:
            mflags = m["access_flags"]
            mname = m["name"]
            if mname == "<clinit>":
                continue
            if (mflags & ACC_SYNTHETIC) or (mflags & ACC_BRIDGE):
                continue

            mattrs = m["attributes"]
            params, ret = SignatureDecoder.parse_method_descriptor(m["descriptor"])
            tparams: List[str] = []
            tparam_bounds: Dict[str, List[str]] = {}
            throws_attr = [_internal_to_fqn(t) for t in mattrs.get("Exceptions", [])]
            throws = list(throws_attr)

            if "Signature" in mattrs:
                try:
                    sig_tp, sig_params, sig_ret, sig_throws = SignatureDecoder.parse_method_signature(mattrs["Signature"])
                    for tp_n, tp_b in sig_tp:
                        tparams.append(tp_n)
                        tparam_bounds[tp_n] = tp_b
                    if len(sig_params) == len(params):
                        params = sig_params
                    else:
                        # Construtores de inner/enum podem ter parâmetros sintéticos na frente do descriptor
                        diff = len(params) - len(sig_params)
                        if diff > 0 and mname == "<init>":
                            params = sig_params
                    ret = sig_ret
                    if sig_throws and len(sig_throws) == len(throws_attr):
                        throws = sig_throws
                except ClassFormatError:
                    pass

            is_varargs = bool(mflags & ACC_VARARGS)
            if is_varargs and params and params[-1].endswith("[]"):
                params[-1] = params[-1][:-2]

            is_ctor = (mname == "<init>")
            is_static = bool(mflags & ACC_STATIC)
            is_abs = bool(mflags & ACC_ABSTRACT)
            is_fin = bool(mflags & ACC_FINAL)
            m_access = _access_from_flags(mflags)
            if kind == "interface":
                if m_access == "package":
                    m_access = "public"
                is_def = (not is_static) and (not is_abs) and (m_access != "private")
            else:
                is_def = False

            info = ExternalMethodInfo(
                name=mname,
                is_constructor=is_ctor,
                params=params,
                ret=ret,
                static=is_static,
                varargs=is_varargs,
                tparams=tparams,
                tparam_bounds=tparam_bounds,
                throws=throws,
                access=m_access,
                modifiers=_modifiers_from_flags(mflags, is_type=False),
                is_abstract=is_abs,
                is_final=is_fin,
                is_default=is_def,
            )
            if is_ctor:
                constructors.append(info)
            else:
                methods.setdefault(mname, []).append(info)

        java_ver = CLASS_MAJOR_TO_JAVA.get(major, f"major-{major}")
        return ExternalTypeInfo(
            fqn=fqn,
            internal_name=this_internal,
            package=pkg,
            simple_name=simple_name,
            kind=kind,
            modifiers=modifiers,
            access=access,
            is_final=is_final,
            is_abstract=is_abstract,
            is_nested=is_nested,
            enclosing_fqn=enclosing_fqn,
            top_level_fqn=top_level_fqn,
            type_parameters=type_parameters,
            super_class=super_fqn,
            interfaces=iface_fqns,
            fields=fields,
            methods=methods,
            constructors=constructors,
            major_version=major,
            minor_version=minor,
            java_version=java_ver,
            source_origin=source_origin,
        )

    @staticmethod
    def _decode_mutf8(raw: bytes) -> str:
        if b"\xc0\x80" in raw:
            raw = raw.replace(b"\xc0\x80", b"\x00")
        return raw.decode("utf-8", errors="replace")

    @classmethod
    def _read_constant_pool(cls, reader: _ByteReader) -> List[Any]:
        count = reader.read_u2()
        if count < 1:
            raise ClassFormatError("Constant pool vazia ou inválida.")
        cp: List[Any] = [None] * count
        idx = 1
        while idx < count:
            tag = reader.read_u1()
            if tag == CP_UTF8:
                ln = reader.read_u2()
                cp[idx] = ("Utf8", cls._decode_mutf8(reader.read_bytes(ln)))
            elif tag == CP_INTEGER:
                cp[idx] = ("Integer", reader.read_i4())
            elif tag == CP_FLOAT:
                cp[idx] = ("Float", reader.read_f4())
            elif tag == CP_LONG:
                cp[idx] = ("Long", reader.read_i8())
                idx += 1
            elif tag == CP_DOUBLE:
                cp[idx] = ("Double", reader.read_f8())
                idx += 1
            elif tag == CP_CLASS:
                cp[idx] = ("Class", reader.read_u2())
            elif tag == CP_STRING:
                cp[idx] = ("String", reader.read_u2())
            elif tag in (CP_FIELDREF, CP_METHODREF, CP_INTERFACE_METHODREF, CP_NAME_AND_TYPE, CP_DYNAMIC, CP_INVOKE_DYNAMIC):
                reader.read_u2()
                reader.read_u2()
                cp[idx] = ("Ref", tag)
            elif tag == CP_METHOD_HANDLE:
                reader.read_u1()
                reader.read_u2()
                cp[idx] = ("MethodHandle",)
            elif tag in (CP_METHOD_TYPE, CP_MODULE, CP_PACKAGE):
                reader.read_u2()
                cp[idx] = ("NameRef", tag)
            else:
                raise ClassFormatError(f"Tag de Constant Pool desconhecida: {tag} (índice {idx}).")
            idx += 1
        return cp

    @staticmethod
    def _cp_utf8(cp: List[Any], idx: int) -> str:
        if 0 < idx < len(cp) and cp[idx] and cp[idx][0] == "Utf8":
            return cp[idx][1]
        return ""

    @classmethod
    def _cp_class_name(cls, cp: List[Any], idx: int) -> str:
        if 0 < idx < len(cp) and cp[idx] and cp[idx][0] == "Class":
            return cls._cp_utf8(cp, cp[idx][1])
        return ""

    @classmethod
    def _read_members(cls, reader: _ByteReader, cp: List[Any]) -> List[Dict[str, Any]]:
        count = reader.read_u2()
        members: List[Dict[str, Any]] = []
        for _ in range(count):
            flags = reader.read_u2()
            name = cls._cp_utf8(cp, reader.read_u2())
            desc = cls._cp_utf8(cp, reader.read_u2())
            attrs = cls._read_attributes(reader, cp)
            members.append({
                "access_flags": flags,
                "name": name,
                "descriptor": desc,
                "attributes": attrs,
            })
        return members

    @classmethod
    def _read_attributes(cls, reader: _ByteReader, cp: List[Any]) -> Dict[str, Any]:
        count = reader.read_u2()
        attrs: Dict[str, Any] = {}
        for _ in range(count):
            attr_name = cls._cp_utf8(cp, reader.read_u2())
            attr_len = reader.read_u4()
            raw = reader.read_bytes(attr_len)
            if attr_name == "Signature" and len(raw) == 2:
                sig_idx = struct.unpack_from(">H", raw, 0)[0]
                attrs["Signature"] = cls._cp_utf8(cp, sig_idx)
            elif attr_name == "Exceptions" and len(raw) >= 2:
                ex_reader = _ByteReader(raw)
                n_ex = ex_reader.read_u2()
                attrs["Exceptions"] = [
                    cls._cp_class_name(cp, ex_reader.read_u2()) for _ in range(n_ex)
                ]
            elif attr_name == "ConstantValue" and len(raw) == 2:
                cv_idx = struct.unpack_from(">H", raw, 0)[0]
                if 0 < cv_idx < len(cp) and cp[cv_idx] is not None:
                    entry = cp[cv_idx]
                    if entry[0] == "String":
                        attrs["ConstantValue"] = ("String", cls._cp_utf8(cp, entry[1]))
                    elif entry[0] in ("Integer", "Float", "Long", "Double"):
                        attrs["ConstantValue"] = entry
            elif attr_name == "InnerClasses" and len(raw) >= 2:
                ic_reader = _ByteReader(raw)
                n_ic = ic_reader.read_u2()
                ics = []
                for _ in range(n_ic):
                    inner_i = ic_reader.read_u2()
                    outer_i = ic_reader.read_u2()
                    name_i = ic_reader.read_u2()
                    ic_flags = ic_reader.read_u2()
                    ics.append({
                        "inner_name": cls._cp_class_name(cp, inner_i),
                        "outer_name": cls._cp_class_name(cp, outer_i) if outer_i != 0 else "",
                        "simple_name": cls._cp_utf8(cp, name_i) if name_i != 0 else "",
                        "access_flags": ic_flags,
                    })
                attrs["InnerClasses"] = ics
            elif attr_name == "Record":
                attrs["Record"] = True
        return attrs

    @staticmethod
    def _normalize_constant_value(field_type: str, raw_entry: Tuple[str, Any]) -> Optional[Tuple[str, Any]]:
        tag, val = raw_entry
        if field_type == "boolean" and tag == "Integer":
            return ("boolean", bool(val))
        if field_type == "char" and tag == "Integer":
            return ("char", chr(val & 0xFFFF))
        if field_type in ("byte", "short", "int") and tag == "Integer":
            return (field_type, int(val))
        if field_type == "long" and tag == "Long":
            return ("long", int(val))
        if field_type == "float" and tag == "Float":
            return ("float", float(val))
        if field_type == "double" and tag == "Double":
            return ("double", float(val))
        if field_type in ("java.lang.String", "String") and tag == "String":
            return ("String", str(val))
        return None


class ClasspathEntry:
    """Abstração de fonte de bytecode externa (diretório, JAR ou JMOD)."""

    def __init__(self, path: str):
        self.path = path
        self._fqn_to_member: Dict[str, str] = {}
        self._loaded = False

    def ensure_indexed(self) -> None:
        if not self._loaded:
            self._loaded = True
            self._index()

    def _index(self) -> None:
        raise NotImplementedError

    def read_class_bytes(self, fqn: str) -> Optional[bytes]:
        raise NotImplementedError

    def list_fqns(self) -> Sequence[str]:
        self.ensure_indexed()
        return list(self._fqn_to_member.keys())

    def has_class(self, fqn: str) -> bool:
        self.ensure_indexed()
        return fqn in self._fqn_to_member

    def _register_internal_member(self, internal_name: str, archive_member: str) -> None:
        # Registra tanto o nome com '$' quanto a forma pontuada para tipos aninhados
        dotted_raw = internal_name.replace("/", ".")
        self._fqn_to_member[dotted_raw] = archive_member
        if "$" in internal_name:
            fqn = _internal_to_fqn(internal_name)
            self._fqn_to_member.setdefault(fqn, archive_member)


class DirectoryClasspathEntry(ClasspathEntry):
    """Provedor para diretório de arquivos `.class` compilados."""

    def _index(self) -> None:
        root = Path(self.path)
        if not root.is_dir():
            return
        for class_file in root.rglob("*.class"):
            rel = class_file.relative_to(root).as_posix()
            if rel.endswith("module-info.class") or rel.endswith("package-info.class"):
                continue
            internal_name = rel[:-6]  # remove '.class'
            self._register_internal_member(internal_name, str(class_file))

    def read_class_bytes(self, fqn: str) -> Optional[bytes]:
        self.ensure_indexed()
        target = self._fqn_to_member.get(fqn)
        if not target:
            return None
        return Path(target).read_bytes()


class JarClasspathEntry(ClasspathEntry):
    """Provedor preguiçoso para arquivos `.jar` / `.zip` (incluindo `rt.jar`)."""

    def __init__(self, path: str, entry_prefix: str = "", keep_open: bool = False):
        super().__init__(path)
        self._entry_prefix = entry_prefix
        self._keep_open = keep_open
        self._zip: Optional[zipfile.ZipFile] = None

    def _open_zip(self) -> Optional[zipfile.ZipFile]:
        if self._zip is None and os.path.isfile(self.path):
            self._zip = zipfile.ZipFile(self.path, "r")
        return self._zip

    def _index(self) -> None:
        if not os.path.isfile(self.path):
            return
        if self._keep_open:
            zf = self._open_zip()
            if zf is None:
                return
            self._index_zipfile(zf)
        else:
            with zipfile.ZipFile(self.path, "r") as zf:
                self._index_zipfile(zf)

    def _index_zipfile(self, zf: zipfile.ZipFile) -> None:
        plen = len(self._entry_prefix)
        for name in zf.namelist():
            if not name.endswith(".class"):
                continue
            if self._entry_prefix:
                if not name.startswith(self._entry_prefix):
                    continue
                rel = name[plen:]
            else:
                rel = name
            if rel.endswith("module-info.class") or rel.endswith("package-info.class"):
                continue
            internal_name = rel[:-6]
            self._register_internal_member(internal_name, name)

    def read_class_bytes(self, fqn: str) -> Optional[bytes]:
        self.ensure_indexed()
        member = self._fqn_to_member.get(fqn)
        if not member:
            return None
        if self._keep_open:
            zf = self._open_zip()
            if zf is None:
                return None
            return zf.read(member)
        if not os.path.isfile(self.path):
            return None
        with zipfile.ZipFile(self.path, "r") as zf:
            return zf.read(member)

    def close(self) -> None:
        if self._zip is not None:
            try:
                self._zip.close()
            finally:
                self._zip = None

    def __del__(self):
        self.close()


class JmodClasspathEntry(JarClasspathEntry):
    """Provedor para módulos JDK `.jmod` (lê entradas sob `classes/`)."""

    def __init__(self, path: str, keep_open: bool = False):
        super().__init__(path, entry_prefix="classes/", keep_open=keep_open)


def discover_default_jdk_entries() -> Tuple[List[ClasspathEntry], Dict[str, Any]]:
    """
    Descobre fontes estáticas de biblioteca padrão disponíveis no ambiente local
    (`jmods/*.jmod` ou `lib/rt.jar`) sem invocar ferramentas externas sobre o classpath.
    """
    candidates: List[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home))

    java_bin = shutil.which("java")
    if java_bin:
        try:
            resolved_bin = Path(java_bin).resolve()
            candidates.append(resolved_bin.parent.parent)
        except Exception:
            pass

    for root_str in (
        r"C:\Program Files\Java",
        r"C:\Program Files (x86)\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\Microsoft",
        r"C:\Program Files\Zulu",
        "/usr/lib/jvm",
        "/Library/Java/JavaVirtualMachines",
    ):
        root = Path(root_str)
        if root.is_dir():
            for child in sorted(root.iterdir(), reverse=True):
                if child.is_dir():
                    candidates.append(child)
                    mac_home = child / "Contents" / "Home"
                    if mac_home.is_dir():
                        candidates.append(mac_home)

    seen_dirs: Set[str] = set()
    for base in candidates:
        key = str(base).lower()
        if key in seen_dirs or not base.is_dir():
            continue
        seen_dirs.add(key)

        jmods_dir = base / "jmods"
        if jmods_dir.is_dir():
            jmod_files = sorted(jmods_dir.glob("*.jmod"))
            if jmod_files:
                entries: List[ClasspathEntry] = [JmodClasspathEntry(str(jf), keep_open=True) for jf in jmod_files]
                is_partial = not any(jf.name == "java.base.jmod" for jf in jmod_files)
                return entries, {
                    "stdlib_available": True,
                    "stdlib_kind": "jmods",
                    "stdlib_source": str(jmods_dir),
                    "stdlib_module_count": len(jmod_files),
                    "is_partial_jdk": is_partial,
                }

        for rt_rel in (Path("jre") / "lib" / "rt.jar", Path("lib") / "rt.jar"):
            rt_path = base / rt_rel
            if rt_path.is_file():
                return [JarClasspathEntry(str(rt_path), keep_open=True)], {
                    "stdlib_available": True,
                    "stdlib_kind": "rt.jar",
                    "stdlib_source": str(rt_path),
                    "stdlib_module_count": 1,
                    "is_partial_jdk": True,  # JRE 8 rt.jar não contém APIs JDK 9-26 / módulos separados
                }

    return [], {
        "stdlib_available": False,
        "stdlib_kind": "none",
        "stdlib_source": None,
        "stdlib_module_count": 0,
        "is_partial_jdk": True,
    }


_DEFAULT_STDLIB_CACHE: Dict[
    str,
    Tuple[
        List[ClasspathEntry],
        Dict[str, Any],
        Dict[str, Tuple[ClasspathEntry, str]],
        Dict[Tuple[int, str], Optional[ExternalTypeInfo]],
    ],
] = {}


def _get_cached_default_jdk() -> Tuple[
    List[ClasspathEntry],
    Dict[str, Any],
    Dict[str, Tuple[ClasspathEntry, str]],
    Dict[Tuple[int, str], Optional[ExternalTypeInfo]],
]:
    cache_key = os.environ.get("JAVA_HOME", "")
    cached = _DEFAULT_STDLIB_CACHE.get(cache_key)
    if cached is not None:
        return cached
    entries, meta = discover_default_jdk_entries()
    fqn_index: Dict[str, Tuple[ClasspathEntry, str]] = {}
    for ent in entries:
        try:
            fqns = ent.list_fqns()
        except zipfile.BadZipFile:
            continue
        for fqn in fqns:
            fqn_index.setdefault(fqn, (ent, fqn))
    parsed_cache: Dict[Tuple[int, str], Optional[ExternalTypeInfo]] = {}
    meta_copy = dict(meta)
    if meta_copy.get("stdlib_available") and "java.lang.Object" in fqn_index:
        ent, real_fqn = fqn_index["java.lang.Object"]
        try:
            raw = ent.read_class_bytes(real_fqn)
            if raw is not None:
                obj = ClassFileParser.parse_bytes(raw, source_origin=ent.path, max_class_major=DEFAULT_MAX_CLASS_MAJOR)
                parsed_cache[(DEFAULT_MAX_CLASS_MAJOR, "java.lang.Object")] = obj
                meta_copy["stdlib_java_version"] = obj.java_version
                if obj.major_version >= DEFAULT_MAX_CLASS_MAJOR and meta_copy.get("stdlib_kind") == "jmods":
                    meta_copy["is_partial_jdk"] = False
                else:
                    meta_copy["is_partial_jdk"] = True
        except Exception:
            pass
    bundle = (entries, meta_copy, fqn_index, parsed_cache)
    _DEFAULT_STDLIB_CACHE[cache_key] = bundle
    return bundle


def _unpack_import(imp: Any) -> Tuple[Optional[str], bool, bool]:
    """Extrai (nome, is_wildcard, is_static) de ImportDeclaration ou tupla compatível."""
    if isinstance(imp, tuple):
        if len(imp) >= 3:
            return imp[0], bool(imp[1]), bool(imp[2])
        if len(imp) == 2:
            return imp[0], bool(imp[1]), False
        return (imp[0] if imp else None), False, False
    return (
        getattr(imp, "name", None),
        bool(getattr(imp, "is_wildcard", False)),
        bool(getattr(imp, "is_static", False)),
    )


class ExternalSymbolResolver:
    """
    Resolvedor de símbolos externos desacoplado das regras semânticas.

    Mantém índice preguiçoso sobre entradas da JDK/JRE e dependências do
    classpath (JARs, JMODs e diretórios `.class`), com cache de `ExternalTypeInfo`,
    diagnósticos estruturados e checagem de versão de bytecode.
    """

    def __init__(
        self,
        classpath: Optional[Sequence[str]] = None,
        include_stdlib: bool = True,
        max_class_major: int = DEFAULT_MAX_CLASS_MAJOR,
    ):
        self.max_class_major = max_class_major
        self.include_stdlib = include_stdlib
        self._entries: List[ClasspathEntry] = []
        self._fqn_index: Dict[str, Tuple[ClasspathEntry, str]] = {}
        self._std_fqn_index: Dict[str, Tuple[ClasspathEntry, str]] = {}
        self._std_parsed_cache: Dict[Tuple[int, str], Optional[ExternalTypeInfo]] = {}
        self._type_cache: Dict[str, Optional[ExternalTypeInfo]] = {}
        self._diagnostics: List[ClasspathDiagnostic] = []
        self._stdlib_meta: Dict[str, Any] = {
            "stdlib_available": False,
            "stdlib_kind": "none",
            "stdlib_source": None,
            "stdlib_java_version": None,
            "is_partial_jdk": True,
        }

        if include_stdlib:
            std_entries, std_meta, std_fqn_index, std_parsed_cache = _get_cached_default_jdk()
            self._stdlib_meta.update(std_meta)
            self._entries.extend(std_entries)
            self._std_fqn_index = std_fqn_index
            self._std_parsed_cache = std_parsed_cache

        for cp_item in (classpath or ()):
            self.add_classpath_path(cp_item)

        if include_stdlib and self._stdlib_meta.get("stdlib_available") and self._stdlib_meta.get("stdlib_java_version") is None:
            self._detect_stdlib_version()

    def _add_entry(self, entry: ClasspathEntry) -> None:
        self._entries.append(entry)
        try:
            fqns = entry.list_fqns()
        except zipfile.BadZipFile:
            self._diagnostics.append(
                ClasspathDiagnostic(
                    kind="corrupt_classfile",
                    message=f"Arquivo de classpath inválido ou corrompido: '{entry.path}'.",
                    target=entry.path,
                )
            )
            return
        for fqn in fqns:
            self._fqn_index.setdefault(fqn, (entry, fqn))

    def add_classpath_path(self, path_str: str) -> None:
        if not path_str:
            return
        p = Path(path_str)
        if not p.exists():
            self._diagnostics.append(
                ClasspathDiagnostic(
                    kind="missing_entry",
                    message=f"Entrada de classpath não encontrada: '{path_str}'.",
                    target=path_str,
                )
            )
            return
        if p.is_dir():
            self._add_entry(DirectoryClasspathEntry(str(p)))
        elif p.suffix.lower() == ".jmod":
            self._add_entry(JmodClasspathEntry(str(p)))
        elif p.suffix.lower() in (".jar", ".zip"):
            self._add_entry(JarClasspathEntry(str(p)))
        else:
            self._diagnostics.append(
                ClasspathDiagnostic(
                    kind="missing_entry",
                    message=f"Formato de entrada de classpath não suportado: '{path_str}'.",
                    target=path_str,
                )
            )

    def _detect_stdlib_version(self) -> None:
        if not self._stdlib_meta.get("stdlib_available"):
            return
        obj = self.get_type_info_by_fqn("java.lang.Object")
        if obj is not None:
            self._stdlib_meta["stdlib_java_version"] = obj.java_version
            # Somente JDK 26 completa (sem partição parcial) seria considerada integral para SE 26
            if obj.major_version >= DEFAULT_MAX_CLASS_MAJOR and self._stdlib_meta.get("stdlib_kind") == "jmods":
                self._stdlib_meta["is_partial_jdk"] = False
            else:
                self._stdlib_meta["is_partial_jdk"] = True

    def is_older_stdlib(self) -> bool:
        """Indica se a biblioteca padrão carregada é anterior ao Java 26 ou ausente/parcial."""
        if not self._stdlib_meta.get("stdlib_available"):
            return True
        return bool(self._stdlib_meta.get("is_partial_jdk", True))

    def coverage_report(self) -> Dict[str, Any]:
        """Retorna relatório honesto sobre cobertura da biblioteca padrão e classpath."""
        report = dict(self._stdlib_meta)
        all_count = len(self._std_fqn_index)
        if self._fqn_index:
            all_count = len(set(self._std_fqn_index) | set(self._fqn_index))
        report["indexed_class_count"] = all_count
        report["cached_parsed_count"] = len(self._type_cache) + len(self._std_parsed_cache)
        report["diagnostics"] = list(self._diagnostics)
        return report

    def get_diagnostics(self) -> List[ClasspathDiagnostic]:
        return list(self._diagnostics)

    def has_class(self, fqn: str) -> bool:
        return (fqn in self._fqn_index) or (fqn in self._std_fqn_index)

    def resolve_fqn(
        self,
        type_name: str,
        current_package: str = "",
        imports: Sequence[Any] = (),
        compat_fqns: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Resolve nome simples ou qualificado para FQN indexado no classpath conforme JLS §6.5."""
        if not type_name:
            return None
        clean = type_name.strip()
        if self.has_class(clean):
            return clean

        # 1. Imports explícitos de tipo único (ex: import java.nio.file.Path;)
        if "." not in clean:
            for imp in imports:
                imp_name, is_wild, is_stat = _unpack_import(imp)
                if is_stat or is_wild:
                    continue
                if imp_name and imp_name.split(".")[-1] == clean:
                    if self.has_class(imp_name):
                        return imp_name
                    return None
        else:
            # Nome parcialmente qualificado após import (ex: Map.Entry com import java.util.Map;)
            head, rest = clean.split(".", 1)
            for imp in imports:
                imp_name, is_wild, is_stat = _unpack_import(imp)
                if is_stat or is_wild:
                    continue
                if imp_name and imp_name.split(".")[-1] == head:
                    cand = f"{imp_name}.{rest}"
                    if self.has_class(cand):
                        return cand

        # 2. Mesmo pacote da unidade atual
        if current_package:
            same_pkg = f"{current_package}.{clean}"
            if self.has_class(same_pkg):
                return same_pkg

        # 3. Pacote implícito java.lang.* (JLS §7.3)
        jl_cand = f"java.lang.{clean}"
        if self.has_class(jl_cand):
            return jl_cand

        # 4. Imports sob demanda (wildcard: import pkg.*;)
        wildcard_matches: List[str] = []
        for imp in imports:
            pkg_prefix, is_wild, is_stat = _unpack_import(imp)
            if is_stat or not is_wild or not pkg_prefix:
                continue
            cand = f"{pkg_prefix}.{clean}"
            if self.has_class(cand) and cand not in wildcard_matches:
                wildcard_matches.append(cand)
        if wildcard_matches:
            return wildcard_matches[0]

        # 5. Fallback opcional de compatibilidade para nomes legados sem import explícito
        if compat_fqns and clean in compat_fqns:
            mapped = compat_fqns[clean]
            if self.has_class(mapped):
                return mapped

        return None

    def get_type_info_by_fqn(self, fqn: str) -> Optional[ExternalTypeInfo]:
        """Carrega preguiçosamente e armazena em cache os metadados de uma classe pelo FQN."""
        if not fqn:
            return None
        if fqn in self._type_cache:
            return self._type_cache[fqn]
        loc = self._fqn_index.get(fqn)
        is_stdlib_loc = False
        if loc is None:
            loc = self._std_fqn_index.get(fqn)
            if loc is None:
                return None
            is_stdlib_loc = True
            std_hit = self._std_parsed_cache.get((self.max_class_major, fqn))
            if std_hit is not None:
                return std_hit
        entry, real_fqn = loc
        try:
            raw_bytes = entry.read_class_bytes(real_fqn)
        except Exception as exc:
            self._diagnostics.append(
                ClasspathDiagnostic(
                    kind="corrupt_classfile",
                    message=f"Falha ao ler '{real_fqn}' em '{entry.path}': {exc}",
                    target=real_fqn,
                )
            )
            self._type_cache[fqn] = None
            return None
        if raw_bytes is None:
            return None
        try:
            info = ClassFileParser.parse_bytes(
                raw_bytes,
                source_origin=entry.path,
                max_class_major=self.max_class_major,
            )
            if is_stdlib_loc:
                self._std_parsed_cache[(self.max_class_major, fqn)] = info
                if info.fqn != fqn:
                    self._std_parsed_cache[(self.max_class_major, info.fqn)] = info
            else:
                self._type_cache[fqn] = info
                if info.fqn != fqn:
                    self._type_cache[info.fqn] = info
            return info
        except ClassVersionError as exc:
            self._diagnostics.append(
                ClasspathDiagnostic(
                    kind="unsupported_class_version",
                    message=f"Ao carregar '{fqn}': {exc}",
                    target=fqn,
                )
            )
            self._type_cache[fqn] = None
            return None
        except ClassFormatError as exc:
            self._diagnostics.append(
                ClasspathDiagnostic(
                    kind="corrupt_classfile",
                    message=f"Arquivo .class inválido para '{fqn}': {exc}",
                    target=fqn,
                )
            )
            self._type_cache[fqn] = None
            return None

    def resolve_type(
        self,
        type_name: str,
        current_package: str = "",
        imports: Sequence[Any] = (),
        compat_fqns: Optional[Dict[str, str]] = None,
    ) -> Optional[ExternalTypeInfo]:
        fqn = self.resolve_fqn(
            type_name,
            current_package=current_package,
            imports=imports,
            compat_fqns=compat_fqns,
        )
        if not fqn:
            return None
        return self.get_type_info_by_fqn(fqn)

