"""Small hypergraph-product (HGP) codes and their code-capacity error models.

M4 needs codes that are *not* matchable surface codes so the graph-aware decoder
can be compared across code families. This module builds the Tillich-Zemor
hypergraph product of two classical codes,

    H_X = [H1 (x) I_{n2} | I_{m1} (x) H2^T]     (m1 n2 checks)
    H_Z = [I_{n1} (x) H2 | H1^T (x) I_{m2}]     (n1 m2 checks)

over the qubit set ``V1 x V2`` (n1 n2 qubits) plus ``E1 x E2`` (m1 m2 qubits),
which satisfies ``H_X H_Z^T = 0`` over GF(2). It also computes a symplectically
paired logical-operator basis and emits a code-capacity detector error model, so
the existing BP / GNN machinery applies unchanged.

No Stim *circuit* is constructed: HGP codes are used at the DEM level, which is
also how they are studied in the LDPC literature (there is no standard
decomposition into a matching graph, so MWPM is not available for them).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import stim


# --------------------------------------------------------------------------- #
# GF(2) linear algebra
# --------------------------------------------------------------------------- #


def gf2_rref(matrix: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """Reduced row echelon form over GF(2) plus its pivot columns."""

    rows = np.asarray(matrix, dtype=np.uint8).copy() % 2
    if rows.ndim == 1:
        rows = rows[None, :]
    num_rows, num_cols = rows.shape
    pivots: list[int] = []
    row = 0
    for col in range(num_cols):
        if row >= num_rows:
            break
        candidates = np.flatnonzero(rows[row:, col])
        if candidates.size == 0:
            continue
        pivot = row + int(candidates[0])
        if pivot != row:
            rows[[row, pivot]] = rows[[pivot, row]]
        others = np.flatnonzero(rows[:, col])
        others = others[others != row]
        if others.size:
            rows[others] ^= rows[row]
        pivots.append(col)
        row += 1
    return rows, pivots


def gf2_rank(matrix: np.ndarray) -> int:
    """Rank of a binary matrix over GF(2)."""

    if np.asarray(matrix).size == 0:
        return 0
    return len(gf2_rref(matrix)[1])


def gf2_null_space(matrix: np.ndarray) -> np.ndarray:
    """Rows spanning the null space of ``matrix`` over GF(2)."""

    rows = np.asarray(matrix, dtype=np.uint8) % 2
    if rows.ndim == 1:
        rows = rows[None, :]
    num_cols = rows.shape[1]
    rref, pivots = gf2_rref(rows)
    if not pivots:
        return np.eye(num_cols, dtype=np.uint8)
    free = [col for col in range(num_cols) if col not in pivots]
    basis = np.zeros((len(free), num_cols), dtype=np.uint8)
    for index, free_col in enumerate(free):
        basis[index, free_col] = 1
        for row_index, pivot_col in enumerate(pivots):
            if rref[row_index, free_col]:
                basis[index, pivot_col] = 1
    return basis


def gf2_in_row_space(candidate: np.ndarray, generator: np.ndarray) -> bool:
    """Whether a single binary vector lies in the row space of ``generator``."""

    candidate = np.asarray(candidate, dtype=np.uint8) % 2
    generator = np.asarray(generator, dtype=np.uint8) % 2
    if not candidate.any():
        return True
    base = gf2_rank(generator)
    stacked = np.vstack([generator, candidate[None, :]])
    return gf2_rank(stacked) == base


def gf2_inverse(matrix: np.ndarray) -> np.ndarray:
    """Inverse of a square invertible binary matrix over GF(2)."""

    matrix = np.asarray(matrix, dtype=np.uint8) % 2
    size = matrix.shape[0]
    if matrix.shape != (size, size):
        raise ValueError("matrix must be square")
    augmented = np.concatenate([matrix, np.eye(size, dtype=np.uint8)], axis=1)
    rref, pivots = gf2_rref(augmented)
    if len(pivots) != size or any(pivot >= size for pivot in pivots):
        raise ValueError("matrix is singular over GF(2)")
    return rref[:, size:]


# --------------------------------------------------------------------------- #
# Classical seed codes
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ClassicalCode:
    """Binary linear code given by a parity-check matrix."""

    name: str
    check_matrix: np.ndarray

    def __post_init__(self) -> None:
        if self.check_matrix.ndim != 2:
            raise ValueError("check_matrix must be two-dimensional")
        if self.check_matrix.size and not set(np.unique(self.check_matrix)).issubset({0, 1}):
            raise ValueError("check_matrix must be binary")

    @property
    def num_checks(self) -> int:
        return int(self.check_matrix.shape[0])

    @property
    def num_bits(self) -> int:
        return int(self.check_matrix.shape[1])

    @property
    def rank(self) -> int:
        return gf2_rank(self.check_matrix)

    @property
    def dimension(self) -> int:
        return self.num_bits - self.rank

    def transpose_code(self) -> "ClassicalCode":
        """Code whose parity checks are the columns of this code."""

        return ClassicalCode(name=f"{self.name}^T", check_matrix=self.check_matrix.T.copy())


def repetition_classical_code(distance: int) -> ClassicalCode:
    """Classical ``[d, 1, d]`` repetition code."""

    if distance < 2:
        raise ValueError("distance must be >= 2")
    checks = np.zeros((distance - 1, distance), dtype=np.uint8)
    for index in range(distance - 1):
        checks[index, index] = 1
        checks[index, index + 1] = 1
    return ClassicalCode(name=f"rep_{distance}", check_matrix=checks)


def hamming_classical_code() -> ClassicalCode:
    """Classical ``[7, 4, 3]`` Hamming code."""

    checks = np.array(
        [
            [1, 1, 0, 1, 1, 0, 0],
            [1, 0, 1, 1, 0, 1, 0],
            [0, 1, 1, 1, 0, 0, 1],
        ],
        dtype=np.uint8,
    )
    return ClassicalCode(name="hamming_7_4_3", check_matrix=checks)


# --------------------------------------------------------------------------- #
# Hypergraph product code
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HGPCode:
    """Hypergraph product of two classical codes."""

    name: str
    hx: np.ndarray
    hz: np.ndarray
    logical_x: np.ndarray
    logical_z: np.ndarray
    base_1: ClassicalCode
    base_2: ClassicalCode

    @property
    def num_qubits(self) -> int:
        return int(self.hx.shape[1])

    @property
    def num_x_checks(self) -> int:
        return int(self.hx.shape[0])

    @property
    def num_z_checks(self) -> int:
        return int(self.hz.shape[0])

    @property
    def num_detectors(self) -> int:
        return self.num_x_checks + self.num_z_checks

    @property
    def k(self) -> int:
        return int(self.logical_x.shape[0])

    def check_orthogonality(self) -> None:
        """Raises unless ``H_X H_Z^T = 0`` over GF(2)."""

        if ((self.hx.astype(np.int64) @ self.hz.T.astype(np.int64)) % 2).any():
            raise ValueError("H_X H_Z^T must vanish over GF(2)")

    def logical_pairing(self) -> np.ndarray:
        """Pairing matrix ``L_X L_Z^T`` (the identity for a paired basis)."""

        return (self.logical_x.astype(np.int64) @ self.logical_z.T.astype(np.int64)) % 2

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "num_qubits": self.num_qubits,
            "num_x_checks": self.num_x_checks,
            "num_z_checks": self.num_z_checks,
            "num_detectors": self.num_detectors,
            "k": self.k,
            "num_mechanisms": 3 * self.num_qubits,
        }

    # ------------------------------------------------------------- error model

    def detector_error_model(self, physical_error_rate: float) -> stim.DetectorErrorModel:
        """Code-capacity DEM with independent single-qubit Pauli errors.

        Detector space is ``[X-checks | Z-checks]`` and observable space is
        ``[logical X | logical Z]``: a Z error flips X-checks and the logical-X
        observables, an X error flips Z-checks and the logical-Z observables, and
        a Y error flips both. Each Pauli happens with probability ``p / 3``.
        """

        if not 0.0 < physical_error_rate < 1.0:
            raise ValueError("physical_error_rate must be in (0, 1)")
        probability = physical_error_rate / 3.0
        lines: list[str] = []
        for qubit in range(self.num_qubits):
            x_checks = (self.num_x_checks * 0) + np.flatnonzero(self.hx[:, qubit])
            z_checks = self.num_x_checks + np.flatnonzero(self.hz[:, qubit])
            x_logicals = np.flatnonzero(self.logical_x[:, qubit])
            z_logicals = self.k + np.flatnonzero(self.logical_z[:, qubit])
            for kind in ("X", "Y", "Z"):
                detectors: list[int] = []
                observables: list[int] = []
                if kind in ("X", "Y"):  # X error: Z-checks + logical-Z observables
                    detectors.extend(z_checks.tolist())
                    observables.extend(z_logicals.tolist())
                if kind in ("Z", "Y"):  # Z error: X-checks + logical-X observables
                    detectors.extend(x_checks.tolist())
                    observables.extend(x_logicals.tolist())
                targets = [f"D{index}" for index in detectors] + [
                    f"L{index}" for index in observables
                ]
                if targets:
                    lines.append(f"error({probability}) " + " ".join(targets))
        declarations = [f"detector D{index}" for index in range(self.num_detectors)]
        declarations += [f"logical_observable L{index}" for index in range(2 * self.k)]
        return stim.DetectorErrorModel("\n".join(lines + declarations))

    def detector_coordinates(self) -> dict[int, list[float]]:
        """Centroid embedding of each check in the code's 2D qubit layout.

        ``V1 x V2`` qubits sit on integer lattice points and ``E1 x E2`` qubits in
        between; every check is placed at the centroid of the qubits it acts on.
        The second coordinate is the one the graph features read as "time".
        """

        rows_1 = [
            np.flatnonzero(self.base_1.check_matrix[row])
            for row in range(self.base_1.num_checks)
        ]
        rows_2 = [
            np.flatnonzero(self.base_2.check_matrix[row])
            for row in range(self.base_2.num_checks)
        ]
        centers_1 = [float(np.mean(row)) if row.size else 0.0 for row in rows_1]
        centers_2 = [float(np.mean(row)) if row.size else 0.0 for row in rows_2]

        coordinates: dict[int, list[float]] = {}
        index = 0
        for row in range(self.base_1.num_checks):  # X-checks: E1 x V2
            for column in range(self.base_2.num_bits):
                coordinates[index] = [centers_1[row], float(column)]
                index += 1
        for bit in range(self.base_1.num_bits):  # Z-checks: V1 x E2
            for row in range(self.base_2.num_checks):
                coordinates[index] = [float(bit), centers_2[row]]
                index += 1
        return coordinates


def build_hgp_code(
    base_1: ClassicalCode,
    base_2: ClassicalCode,
    name: str | None = None,
) -> HGPCode:
    """Builds the hypergraph product code of two classical codes."""

    n1, m1 = base_1.num_bits, base_1.num_checks
    n2, m2 = base_2.num_bits, base_2.num_checks
    hx = np.concatenate(
        [
            np.kron(base_1.check_matrix, np.eye(n2, dtype=np.uint8)),
            np.kron(np.eye(m1, dtype=np.uint8), base_2.check_matrix.T.astype(np.uint8)),
        ],
        axis=1,
    )
    hz = np.concatenate(
        [
            np.kron(np.eye(n1, dtype=np.uint8), base_2.check_matrix.astype(np.uint8)),
            np.kron(base_1.check_matrix.T.astype(np.uint8), np.eye(m2, dtype=np.uint8)),
        ],
        axis=1,
    )
    hx = np.ascontiguousarray(hx % 2, dtype=np.uint8)
    hz = np.ascontiguousarray(hz % 2, dtype=np.uint8)

    logical_x, logical_z = _logical_basis(hx, hz)
    code = HGPCode(
        name=name or f"HGP({base_1.name},{base_2.name})",
        hx=hx,
        hz=hz,
        logical_x=logical_x,
        logical_z=logical_z,
        base_1=base_1,
        base_2=base_2,
    )
    code.check_orthogonality()
    return code


def _reduce_by_row_space(vector: np.ndarray, rref: np.ndarray, pivots: list[int]) -> np.ndarray:
    """Reduces ``vector`` by the row space described by an RREF basis."""

    reduced = np.asarray(vector, dtype=np.uint8).copy() % 2
    for row_index, pivot in enumerate(pivots):
        if reduced[pivot]:
            reduced ^= rref[row_index]
    return reduced


def _quotient_basis(kernel_basis: np.ndarray, stabilizer_rows: np.ndarray) -> np.ndarray:
    """Basis of ``ker(H) / rowspan(stabilizer)`` as vectors orthogonal to the stabilizer pivots."""

    rref, pivots = gf2_rref(stabilizer_rows)
    basis: list[np.ndarray] = []
    for row in np.atleast_2d(kernel_basis):
        reduced = _reduce_by_row_space(row, rref, pivots)
        if not reduced.any():
            continue
        candidate = np.array(basis + [reduced], dtype=np.uint8) if basis else reduced[None, :]
        if gf2_rank(candidate) == len(basis) + 1:
            basis.append(reduced)
    if not basis:
        return np.zeros((0, kernel_basis.shape[1]), dtype=np.uint8)
    return np.ascontiguousarray(np.array(basis, dtype=np.uint8))


def _logical_basis(hx: np.ndarray, hz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Symplectically paired logical bases with ``L_X L_Z^T = I``.

    Every row of ``H_X`` lies in ``ker(H_Z)`` (and vice versa), so the logical X
    operators are the quotient ``ker(H_Z) / rowspan(H_X)`` and the logical Z
    operators the quotient ``ker(H_X) / rowspan(H_Z)``. Working with reduced
    representatives keeps the two bases independent modulo the stabilizer groups,
    which is what makes the pairing matrix invertible.
    """

    candidate_x = _quotient_basis(gf2_null_space(hz), np.asarray(hx, dtype=np.uint8))
    candidate_z = _quotient_basis(gf2_null_space(hx), np.asarray(hz, dtype=np.uint8))
    if candidate_x.shape[0] == 0 or candidate_z.shape[0] == 0:
        raise ValueError("no logical operators found; the construction is degenerate")
    if candidate_x.shape[0] != candidate_z.shape[0]:
        raise ValueError(
            f"logical bases disagree in size: {candidate_x.shape[0]} vs {candidate_z.shape[0]}"
        )

    pairing = (candidate_x.astype(np.int64) @ candidate_z.T.astype(np.int64)) % 2
    if gf2_rank(pairing) != pairing.shape[0]:
        raise ValueError("logical pairing is singular; cannot build a paired basis")
    # We need L_X (A L_Z)^T = P A^T = I, hence A = (P^T)^{-1}.
    inverse = gf2_inverse(pairing.T.astype(np.uint8))
    paired_z = (inverse.astype(np.int64) @ candidate_z.astype(np.int64)) % 2
    return (
        np.ascontiguousarray(candidate_x, dtype=np.uint8),
        np.ascontiguousarray(paired_z % 2, dtype=np.uint8),
    )


def small_hgp_codes() -> dict[str, HGPCode]:
    """The M4 code zoo: two small HGP codes at two different sizes."""

    repetition = repetition_classical_code(3)
    hamming = hamming_classical_code()
    return {
        "hgp_rep3x3": build_hgp_code(repetition, repetition, name="HGP(rep3,rep3)"),
        "hgp_hamming7x7": build_hgp_code(hamming, hamming, name="HGP(hamming7,hamming7)"),
    }
