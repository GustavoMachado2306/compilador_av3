"""
Módulo de Análise de Exceções Verificadas conforme a JLS §11.
Responsável por classificar exceções (checked vs unchecked), validar cláusulas
'throws' e sobrescrita de métodos (JLS §8.4.8.3), verificar propagação em chamadas,
construtores, lambdas, method references, inicializadores e blocos try/catch/finally.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class ExceptionAnalyzer:
    """Analisador semântico de exceções verificadas conforme JLS §11."""

    def __init__(self, host: Any):
        self.host = host
        self._frames: List[Dict[str, Any]] = []

    def reset(self) -> None:
        self._frames = []

    def snapshot_frames(self) -> List[Dict[str, Any]]:
        """Captura cópia rasa dos frames de exceção para restauração segura de contexto."""
        snap: List[Dict[str, Any]] = []
        for f in self._frames:
            cf = dict(f)
            if "thrown" in cf:
                cf["thrown"] = list(cf["thrown"])
            if "thrown_all" in cf:
                cf["thrown_all"] = list(cf["thrown_all"])
            if "allowed_throws" in cf:
                cf["allowed_throws"] = list(cf["allowed_throws"])
            snap.append(cf)
        return snap

    def restore_frames(self, snap: List[Dict[str, Any]]) -> None:
        self._frames = list(snap)

    # -------------------------------------------------------------------------
    # Classificação de Throwable e Exceções Checked vs Unchecked (JLS §11.1.1)
    # -------------------------------------------------------------------------
    @staticmethod
    def split_union_types(type_str: Optional[str]) -> List[str]:
        """Divide tipo união multicatch 'A | B' em tipos individuais."""
        if not type_str:
            return []
        if "|" not in type_str:
            s = type_str.strip()
            return [s] if s else []
        return [p.strip() for p in type_str.split("|") if p.strip()]

    def is_valid_throwable(self, exc_type: Optional[str]) -> Optional[bool]:
        """Verifica se exc_type (ou todas as alternativas de união) é subtipo de Throwable."""
        parts = self.split_union_types(exc_type)
        if not parts:
            return None
        saw_none = False
        for part in parts:
            clean = (self.host._strip_leading_type_annotations(part) or part).strip()
            if not clean or clean in ("var", "desconhecido"):
                saw_none = True
                continue
            simple = self.host._simple_base_name(clean) or clean
            base, dims = self.host._split_type_dims(simple)
            if dims > 0 or base in self.host.PRIMITIVE_TYPES or base in ("void", "null"):
                return False
            sub = self.host._is_subtype(clean, "Throwable")
            if sub is False:
                return False
            if sub is None:
                saw_none = True
        return None if saw_none else True

    def is_checked_exception(self, exc_type: Optional[str]) -> Optional[bool]:
        """
        Retorna:
          - False se for não verificada (RuntimeException, Error ou subtipos), ou não-Throwable;
          - True se for verificada (demais subtipos de Throwable, incluindo Exception e Throwable);
          - None se envolver hierarquia externa desconhecida.
        """
        parts = self.split_union_types(exc_type)
        if not parts:
            return None
        saw_none = False
        for part in parts:
            clean = (self.host._strip_leading_type_annotations(part) or part).strip()
            if not clean or clean in ("var", "desconhecido"):
                saw_none = True
                continue
            simple = self.host._simple_base_name(clean) or clean
            base, dims = self.host._split_type_dims(simple)
            if dims > 0 or base in self.host.PRIMITIVE_TYPES or base in ("void", "null"):
                return False

            # Tipo variável de método/classe genericamente limitado
            tp_bounds = self.host._lookup_type_param_bounds(base)
            if tp_bounds is not None:
                any_checked = False
                any_unknown = False
                for ub in tp_bounds:
                    ub_chk = self.is_checked_exception(ub)
                    if ub_chk is True:
                        any_checked = True
                    elif ub_chk is None:
                        any_unknown = True
                if any_checked:
                    return True
                if any_unknown:
                    saw_none = True
                continue

            if self.host._is_capture_var(base):
                cap = self.host._capture_vars.get(base, {})
                any_checked = False
                for ub in (cap.get("upper_bounds") or ["Object"]):
                    if self.is_checked_exception(ub) is True:
                        any_checked = True
                if any_checked:
                    return True
                continue

            if base in ("RuntimeException", "Error"):
                continue
            if base in ("Exception", "Throwable"):
                return True

            if self.host._is_subtype(clean, "RuntimeException") is True:
                continue
            if self.host._is_subtype(clean, "Error") is True:
                continue

            is_thr = self.host._is_subtype(clean, "Throwable")
            if is_thr is True:
                return True
            if is_thr is False:
                return False
            saw_none = True
        return None if saw_none else False

    def is_catch_exempt_from_reachability(self, exc_type: Optional[str]) -> bool:
        """
        JLS §11.2.3: catch de RuntimeException, Error, subtipos, Exception ou Throwable
        é sempre alcançável mesmo que o corpo de 'try' não lance explicitamente exceções verificadas.
        """
        if not exc_type:
            return True
        clean = (self.host._strip_leading_type_annotations(exc_type) or exc_type).strip()
        simple = self.host._simple_base_name(clean) or clean
        if simple in ("Exception", "Throwable", "RuntimeException", "Error"):
            return True
        return self.is_checked_exception(clean) is False

    def is_covered_by(self, exc_type: str, allowed_types: List[str]) -> Optional[bool]:
        """Verifica se todas as partes de exc_type são cobertas por pelo menos um tipo em allowed_types."""
        parts = self.split_union_types(exc_type)
        if not parts:
            return True
        saw_none = False
        for part in parts:
            part_clean = (self.host._strip_leading_type_annotations(part) or part).strip()
            part_simple = self.host._simple_base_name(part_clean) or part_clean
            covered = False
            unknown = False
            for allowed in allowed_types:
                if not allowed:
                    continue
                al_clean = (self.host._strip_leading_type_annotations(allowed) or allowed).strip()
                al_simple = self.host._simple_base_name(al_clean) or al_clean
                if part_simple == al_simple or al_simple == "Throwable":
                    covered = True
                    break
                sub = self.host._is_subtype(part_clean, al_clean)
                if sub is True:
                    covered = True
                    break
                if sub is None:
                    unknown = True
            if not covered:
                if unknown:
                    saw_none = True
                else:
                    return False
        return None if saw_none else True

    # -------------------------------------------------------------------------
    # Pilha de Frames de Exceção (Callable / Try)
    # -------------------------------------------------------------------------
    def push_callable_frame(
        self,
        kind: str,
        label: str,
        allowed_throws: Optional[List[str]] = None,
        enforce_unreported: bool = True,
    ) -> Dict[str, Any]:
        frame = {
            "kind": kind,
            "label": label,
            "allowed_throws": list(allowed_throws or []),
            "enforce_unreported": enforce_unreported,
            "thrown": [],
            "has_unresolved_thrower": False,
        }
        self._frames.append(frame)
        return frame

    def pop_callable_frame(self) -> Optional[Dict[str, Any]]:
        for idx in range(len(self._frames) - 1, -1, -1):
            if self._frames[idx]["kind"] != "try":
                return self._frames.pop(idx)
        return None

    def push_try_frame(self) -> Dict[str, Any]:
        frame = {
            "kind": "try",
            "thrown": [],
            "thrown_all": [],
            "has_unresolved_thrower": False,
        }
        self._frames.append(frame)
        return frame

    def pop_try_frame(self) -> Optional[Dict[str, Any]]:
        if self._frames and self._frames[-1]["kind"] == "try":
            return self._frames.pop()
        return None

    def mark_unresolved_thrower(self) -> None:
        """Marca o frame try mais interno dentro do callable atual como tendo chamada externa não resolvida."""
        if self.host._flow_suppress_errors:
            return
        for frame in reversed(self._frames):
            if frame["kind"] == "try":
                frame["has_unresolved_thrower"] = True
                return
            frame["has_unresolved_thrower"] = True
            return

    def emit_thrown(self, exc_types: List[str], line: int, source_desc: str) -> None:
        """Registra exceções lançáveis por uma instrução/chamada/construtor no escopo ativo."""
        if not exc_types or self.host._flow_suppress_errors:
            return
        flat: List[str] = []
        for et in exc_types:
            for p in self.split_union_types(et):
                if p and p not in flat:
                    flat.append(p)
        if not flat:
            return

        for frame in reversed(self._frames):
            if frame["kind"] == "try":
                for exc_t in flat:
                    frame["thrown_all"].append((exc_t, line, source_desc))
                    chk = self.is_checked_exception(exc_t)
                    if chk is True or chk is None:
                        frame["thrown"].append((exc_t, line, source_desc))
                return

            # Chegou à fronteira do callable (método / construtor / inicializador / lambda)
            for exc_t in flat:
                chk = self.is_checked_exception(exc_t)
                if chk is False:
                    continue
                if chk is None:
                    cov = self.is_covered_by(exc_t, frame["allowed_throws"])
                    if cov is not True:
                        self.host._record_unresolved(
                            f"Não foi possível verificar se a exceção externa '{exc_t}' ({source_desc}, linha {line}) é checked/unchecked sem classpath completo."
                        )
                    continue
                frame["thrown"].append((exc_t, line, source_desc))
                if frame["enforce_unreported"]:
                    cov = self.is_covered_by(exc_t, frame["allowed_throws"])
                    if cov is False:
                        self.host.errors.append(
                            self._make_error(
                                f"Exceção verificada não reportada '{exc_t}' em {source_desc}; deve ser capturada ou declarada em 'throws' ({frame['label']} — JLS §11.2).",
                                line,
                            )
                        )
            return

    def _make_error(self, msg: str, line: int) -> Any:
        from .semantic import SemanticError
        return SemanticError(msg, line)

    # -------------------------------------------------------------------------
    # Validações de Cláusulas throws, Sobrescrita e Try/Catch (JLS §8.4, §11.2, §14.20)
    # -------------------------------------------------------------------------
    def validate_throws_clause(self, throws_types: List[Any], fallback_line: int) -> List[str]:
        """Valida cada tipo declarado em 'throws' e retorna os nomes normalizados."""
        resolved: List[str] = []
        for tt in (throws_types or []):
            tname = self.host._normalize_type_str(tt)
            if not tname:
                continue
            tline = getattr(tt, "line", fallback_line)
            resolved.append(tname)

            simple = self.host._simple_base_name(tname) or tname
            base, dims = self.host._split_type_dims(simple)
            if dims > 0 or base in self.host.PRIMITIVE_TYPES or base in ("void", "var"):
                self.host.errors.append(
                    self._make_error(
                        f"Tipo inválido na cláusula 'throws': '{tname}' deve ser subtipo de 'Throwable' (JLS §8.4.6).",
                        tline,
                    )
                )
                continue

            tp_bounds = self.host._lookup_type_param_bounds(base)
            if tp_bounds is not None:
                if not any(self.host._is_subtype(ub, "Throwable") is True for ub in tp_bounds):
                    self.host.errors.append(
                        self._make_error(
                            f"Parâmetro de tipo '{tname}' na cláusula 'throws' deve possuir limite subtipo de 'Throwable' (JLS §8.4.6).",
                            tline,
                        )
                    )
                continue

            sub = self.host._is_subtype(tname, "Throwable")
            if sub is False:
                self.host.errors.append(
                    self._make_error(
                        f"Tipo incompatível na cláusula 'throws': '{tname}' não é subtipo de 'Throwable' (JLS §8.4.6).",
                        tline,
                    )
                )
            elif sub is None:
                self.host._record_unresolved(
                    f"Hierarquia da exceção externa '{tname}' na cláusula 'throws' não pôde ser verificada sem classpath."
                )
        return resolved

    def _collect_supertype_methods(
        self,
        owner_type: str,
        method_name: str,
        include_owner: bool = False,
    ) -> List[Dict[str, Any]]:
        """Coleta assinaturas de método apenas nos supertipos diretos/indiretos herdáveis de owner_type."""
        methods, _ = self.host._inheritance_analyzer._collect_hierarchy_methods(
            owner_type,
            method_name=method_name,
            include_owner=include_owner,
        )
        return [m for m in methods if not m.get("static", False)]

    def _override_params_match(self, child_sig: Dict[str, Any], parent_sig: Dict[str, Any]) -> bool:
        """Verifica se os parâmetros do método filho têm a mesma assinatura/erasão do método pai."""
        cp = child_sig.get("params", [])
        pp = parent_sig.get("params", [])
        if len(cp) != len(pp):
            return False
        if bool(child_sig.get("varargs")) != bool(parent_sig.get("varargs")):
            # Em Java varargs (T...) equivale a array (T[]) para override
            pass
        for ca, pa in zip(cp, pp):
            ca_s = (self.host._strip_leading_type_annotations(ca) or ca).strip()
            pa_s = (self.host._strip_leading_type_annotations(pa) or pa).strip()
            if ca_s == pa_s:
                continue
            ca_er = self.host._strip_generics(ca_s) or ca_s
            pa_er = self.host._strip_generics(pa_s) or pa_s
            if self.host._simple_base_name(ca_er) == self.host._simple_base_name(pa_er):
                continue
            if self.host._is_type_variable(pa_s) or self.host._is_type_variable(ca_s):
                continue
            return False
        return True

    def validate_method_override(
        self,
        owner_type: str,
        member: Any,
        sig: Dict[str, Any],
        is_anonymous: bool = False,
    ) -> None:
        """Valida compatibilidade da cláusula 'throws' de métodos sobrescritos conforme JLS §8.4.8.3."""
        mods = getattr(member, "modifiers", []) or []
        if "static" in mods or "private" in mods:
            return
        if not owner_type:
            return
        child_throws = sig.get("throws", [])
        if not child_throws:
            return

        checked_child = [t for t in child_throws if self.is_checked_exception(t) is True]
        if not checked_child:
            return

        inherited = self._collect_supertype_methods(
            owner_type,
            getattr(member, "name", ""),
            include_owner=is_anonymous,
        )
        matching_parents = [ps for ps in inherited if self._override_params_match(sig, ps)]
        if not matching_parents:
            return

        line = getattr(member, "line", 1)
        for parent_sig in matching_parents:
            parent_throws = parent_sig.get("throws", [])
            for exc_t in checked_child:
                if self.is_covered_by(exc_t, parent_throws) is False:
                    p_owner = parent_sig.get("owner") or "supertipo"
                    self.host.errors.append(
                        self._make_error(
                            f"Método sobrescrito '{member.name}(...)' não pode lançar a exceção verificada '{exc_t}': incompatível com a cláusula 'throws' de '{p_owner}.{member.name}(...)' (JLS §8.4.8.3).",
                            line,
                        )
                    )

    def _exception_subsumes(self, sub_name: str, super_name: str) -> bool:
        """Verifica se sub_name é igual ou subtipo de super_name (hierarquia padrão ou declarada)."""
        if sub_name.split(".")[-1] == super_name.split(".")[-1]:
            return True
        if self.host._is_exception_subtype(sub_name, super_name):
            return True
        return self.host._is_subtype(sub_name, super_name) is True

    def validate_catch_and_reachability(
        self,
        c_types: List[Any],
        catch_line: int,
        caught_exceptions: List[Tuple[str, int]],
        try_frame: Dict[str, Any],
    ) -> None:
        """
        Valida tipos de parâmetros do catch (JLS §14.20), incompatibilidade em multicatch,
        sombreamento de cláusula anterior e inalcançabilidade de exceção verificada não lançada (JLS §11.2.3).
        """
        validated_names: List[Tuple[str, int]] = []
        for ct in c_types:
            ct_name = self.host._normalize_type_str(ct) or getattr(ct, "full_name", "")
            ct_line = getattr(ct, "line", catch_line)
            if not ct_name:
                continue

            simple = self.host._simple_base_name(ct_name) or ct_name
            base, dims = self.host._split_type_dims(simple)
            if getattr(ct, "name", None) == "var":
                # Erro de 'var' já é reportado em TryStatement
                continue
            if dims > 0 or base in self.host.PRIMITIVE_TYPES or base == "void":
                self.host.errors.append(
                    self._make_error(
                        f"Tipo inválido em cláusula 'catch': '{ct_name}' não é subtipo de 'Throwable' (JLS §14.20).",
                        ct_line,
                    )
                )
                continue
            if self.host._lookup_type_param_bounds(base) is not None:
                self.host.errors.append(
                    self._make_error(
                        f"Não é possível capturar parâmetro de tipo '{ct_name}' em cláusula 'catch' (JLS §14.20).",
                        ct_line,
                    )
                )
                continue

            sub = self.host._is_subtype(ct_name, "Throwable")
            if sub is False:
                self.host.errors.append(
                    self._make_error(
                        f"Tipo inválido em cláusula 'catch': '{ct_name}' não é subtipo de 'Throwable' (JLS §14.20).",
                        ct_line,
                    )
                )
                continue
            if sub is None:
                self.host._record_unresolved(
                    f"Hierarquia da exceção externa '{ct_name}' em 'catch' não pôde ser verificada sem classpath."
                )

            validated_names.append((ct_name, ct_line))

        if len(c_types) > 1:
            for idx_a in range(len(c_types)):
                for idx_b in range(idx_a + 1, len(c_types)):
                    na = c_types[idx_a].full_name
                    nb = c_types[idx_b].full_name
                    if self._exception_subsumes(na, nb) or self._exception_subsumes(nb, na):
                        self.host.errors.append(
                            self._make_error(
                                f"Alternativas incompatíveis em multicatch: '{na}' e '{nb}' possuem relação de subtipo ou são idênticas (JLS §14.20).",
                                getattr(c_types[idx_b], "line", catch_line),
                            )
                        )

        for ct_name, ct_line in validated_names:
            subsumed = False
            for prev_ex, prev_line in caught_exceptions:
                if self._exception_subsumes(ct_name, prev_ex):
                    self.host.errors.append(
                        self._make_error(
                            f"Cláusula catch inalcançável para '{ct_name}': exceção já capturada anteriormente na linha {prev_line} (JLS §14.20).",
                            ct_line,
                        )
                    )
                    subsumed = True
                    break

            if (
                not subsumed
                and not try_frame.get("has_unresolved_thrower", False)
                and self.is_checked_exception(ct_name) is True
                and not self.is_catch_exempt_from_reachability(ct_name)
            ):
                can_be_thrown = False
                for t_exc, _, _ in try_frame.get("thrown_all", []):
                    for part in self.split_union_types(t_exc):
                        r1 = self.host._is_subtype(part, ct_name)
                        r2 = self.host._is_subtype(ct_name, part)
                        if r1 is True or r2 is True or r1 is None or r2 is None:
                            can_be_thrown = True
                            break
                    if can_be_thrown:
                        break
                if not can_be_thrown:
                    self.host.errors.append(
                        self._make_error(
                            f"Cláusula catch inalcançável para '{ct_name}': a exceção verificada nunca é lançada no bloco 'try' correspondente (JLS §11.2.3).",
                            ct_line,
                        )
                    )

            caught_exceptions.append((ct_name, ct_line))

    def compute_precise_rethrow_types(
        self,
        c_types: List[Any],
        try_frame: Dict[str, Any],
    ) -> Optional[List[str]]:
        """Computa o conjunto preciso de exceções para rethrow efetivamente final (JLS §11.2.2)."""
        if len(c_types) != 1 or try_frame.get("has_unresolved_thrower", False):
            return None
        ct_name = self.host._normalize_type_str(c_types[0]) or getattr(c_types[0], "full_name", "")
        if not ct_name:
            return None
        # Se a captura é checked estrita, o próprio tipo já representa o limite; se Exception/Throwable, refina pelo try
        simple = self.host._simple_base_name(ct_name) or ct_name
        if simple not in ("Exception", "Throwable"):
            return None
        precise: List[str] = []
        for t_exc, _, _ in try_frame.get("thrown", []):
            for part in self.split_union_types(t_exc):
                if self.host._is_subtype(part, ct_name) is True and part not in precise:
                    precise.append(part)
        return precise

    def propagate_try_uncaught(
        self,
        try_frame: Dict[str, Any],
        caught_types_all: List[str],
    ) -> None:
        """Propaga para o escopo externo apenas exceções lançadas em 'try' que não foram capturadas."""
        for t_exc, t_line, t_desc in try_frame.get("thrown", []):
            parts = self.split_union_types(t_exc)
            uncaught_parts = [
                p for p in parts
                if self.is_covered_by(p, caught_types_all) is not True
            ]
            if uncaught_parts:
                self.emit_thrown(uncaught_parts, t_line, t_desc)
        if try_frame.get("has_unresolved_thrower", False):
            if not any(
                (self.host._simple_base_name(c) or c) in ("Exception", "Throwable")
                for c in caught_types_all
            ):
                self.mark_unresolved_thrower()
