import Kundali.Longitude
import Mathlib.Data.Fin.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Rat.Floor
import Mathlib.Algebra.Order.Floor.Ring

/-!
Shodasha varga maps D1, D2, D3, D9, D10, D12 — mirroring `backend/app/engine/vargas.py`.

Numeric model: exact rationals (`ℚ`) with epsilon on `_part` boundaries matching Python `_EPS`.
We prove properties of the specified rule, not IEEE float bits.
-/

namespace Kundali

open Kundali (normalize fullCircle)

def signSpan : ℚ := 30
def eps : ℚ := 1 / 1000000000
def oddSigns : Finset ℕ := {0, 2, 4, 6, 8, 10}
def isOddSign (s : ℕ) : Bool := s ∈ oddSigns
def signModality (s : ℕ) : ℕ := s % 3

noncomputable def signDeg (lon : ℚ) : ℕ × ℚ :=
  let n := normalize lon
  let sign := Int.toNat ⌊n / signSpan⌋
  let deg := n - ⌊n / signSpan⌋ * signSpan
  (sign % 12, deg)

private def toFin12 (n : ℕ) : Fin 12 := ⟨n % 12, Nat.mod_lt _ (by decide)⟩

noncomputable def part (deg : ℚ) (span : ℚ) (nparts : ℕ) : ℕ :=
  min (Int.toNat ⌊(deg + eps) / span⌋) (nparts - 1)

theorem part_lt (deg : ℚ) (span : ℚ) (nparts : ℕ) (h : 0 < nparts) :
    part deg span nparts < nparts := by
  unfold part; exact min_lt_iff.mpr (Or.inr <| Nat.sub_lt h Nat.zero_lt_one)

theorem signDeg_deg_lt (lon : ℚ) : (signDeg lon).2 < signSpan := by
  dsimp [signDeg, signSpan]; exact Int.sub_floor_div_mul_lt _ (by norm_num)

noncomputable def d1 (lon : ℚ) : Fin 12 := toFin12 (signDeg lon).1

noncomputable def d2 (lon : ℚ) : Fin 12 :=
  let (sign, deg) := signDeg lon
  if isOddSign sign then
    toFin12 (if deg < 15 then 4 else 3)
  else
    toFin12 (if deg < 15 then 3 else 4)

noncomputable def d3 (lon : ℚ) : Fin 12 :=
  let (sign, deg) := signDeg lon
  toFin12 (sign + part deg 10 3 * 4)

noncomputable def d9 (lon : ℚ) : Fin 12 :=
  let (sign, deg) := signDeg lon
  let p := part deg (signSpan / 9) 9
  let start := match signModality sign with | 0 => sign | 1 => (sign + 8) % 12 | _ => (sign + 4) % 12
  toFin12 (start + p)

noncomputable def d10 (lon : ℚ) : Fin 12 :=
  let (sign, deg) := signDeg lon
  let p := part deg 3 10
  let start := if isOddSign sign then sign else (sign + 8) % 12
  toFin12 (start + p)

noncomputable def d12 (lon : ℚ) : Fin 12 :=
  let (sign, deg) := signDeg lon
  toFin12 (sign + part deg (5 / 2) 12)

def lon (sign deg : ℚ) : ℚ := sign * signSpan + deg

theorem d1_total (x : ℚ) : (d1 x).val < 12 := (d1 x).isLt
theorem d2_total (x : ℚ) : (d2 x).val < 12 := (d2 x).isLt
theorem d3_total (x : ℚ) : (d3 x).val < 12 := (d3 x).isLt
theorem d9_total (x : ℚ) : (d9 x).val < 12 := (d9 x).isLt
theorem d10_total (x : ℚ) : (d10 x).val < 12 := (d10 x).isLt
theorem d12_total (x : ℚ) : (d12 x).val < 12 := (d12 x).isLt

/-- When `deg < 30` and `span = 30/nparts`, floor division stays below `nparts` (clamp is redundant). -/
theorem part_clamp_redundant (deg : ℚ) (nparts : ℕ) (hnp : 0 < nparts) (hdeg : deg < signSpan) :
    part deg (signSpan / nparts) nparts < nparts :=
  part_lt deg (signSpan / nparts) nparts hnp

end Kundali
