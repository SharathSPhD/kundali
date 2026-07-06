import Kundali.Longitude
import Mathlib.Data.Fin.Basic
import Mathlib.Data.Rat.Floor
import Mathlib.Algebra.Order.Floor.Ring

/-!
27 nakshatras × 4 padas partition of `[0, 360)`.
-/

namespace Kundali

open Kundali (normalize fullCircle)

def nakshatraSpan : ℚ := fullCircle / 27
def padaSpan : ℚ := nakshatraSpan / 4

theorem nakshatraSpan_pos : 0 < nakshatraSpan := by unfold nakshatraSpan fullCircle; norm_num
theorem padaSpan_pos : 0 < padaSpan := by unfold padaSpan nakshatraSpan fullCircle; norm_num
theorem nakshatraSpan_nonneg : 0 ≤ nakshatraSpan := le_of_lt nakshatraSpan_pos
theorem padaSpan_nonneg : 0 ≤ padaSpan := le_of_lt padaSpan_pos
theorem nakshatra_cover : 27 * nakshatraSpan = fullCircle := by unfold nakshatraSpan fullCircle; norm_num
theorem pada_cover : 4 * padaSpan = nakshatraSpan := by unfold padaSpan nakshatraSpan; ring

private noncomputable def nakshatraIndexNat (x : ℚ) : ℕ :=
  Int.toNat ⌊(normalize x) / nakshatraSpan⌋ % 27

private noncomputable def padaIndexNat (x : ℚ) : ℕ :=
  Int.toNat ⌊(normalize x) / padaSpan⌋ % 4

private theorem nakshatraIndexNat_lt (x : ℚ) : nakshatraIndexNat x < 27 := by
  unfold nakshatraIndexNat
  exact Nat.mod_lt _ (by decide : 0 < 27)

private theorem padaIndexNat_lt (x : ℚ) : padaIndexNat x < 4 := by
  unfold padaIndexNat
  exact Nat.mod_lt _ (by decide : 0 < 4)

noncomputable def nakshatraIndex (x : ℚ) : Fin 27 :=
  ⟨nakshatraIndexNat x, nakshatraIndexNat_lt x⟩

noncomputable def padaIndex (x : ℚ) : Fin 4 :=
  ⟨padaIndexNat x, padaIndexNat_lt x⟩

noncomputable def nakPada (x : ℚ) : Fin 27 × Fin 4 :=
  (nakshatraIndex x, padaIndex x)

theorem nakshatraIndex_valid (x : ℚ) :
    0 ≤ nakshatraIndexNat x ∧ nakshatraIndexNat x < 27 :=
  ⟨Nat.zero_le _, nakshatraIndexNat_lt x⟩

theorem padaIndex_valid (x : ℚ) :
    0 ≤ padaIndexNat x ∧ padaIndexNat x < 4 :=
  ⟨Nat.zero_le _, padaIndexNat_lt x⟩

theorem nakshatra_exhaustive (x : ℚ) : ∃ i : Fin 27, i = nakshatraIndex x :=
  ⟨nakshatraIndex x, rfl⟩

theorem pada_exhaustive (x : ℚ) : ∃ j : Fin 4, j = padaIndex x :=
  ⟨padaIndex x, rfl⟩

theorem nakshatra_partition_covers (i : Fin 27) :
    ((i.val + 1 : ℕ) : ℚ) * nakshatraSpan ≤ fullCircle := by
  have hi : i.val + 1 ≤ 27 := Nat.succ_le_of_lt i.isLt
  have hle : ((i.val + 1 : ℕ) : ℚ) ≤ 27 := by exact_mod_cast hi
  calc ((i.val + 1 : ℕ) : ℚ) * nakshatraSpan
      ≤ (27 : ℚ) * nakshatraSpan := mul_le_mul_of_nonneg_right hle nakshatraSpan_nonneg
    _ = fullCircle := nakshatra_cover

theorem nakshatra_disjoint (i j : Fin 27) (h : i ≠ j) :
    ((i.val + 1 : ℕ) : ℚ) * nakshatraSpan ≤ (j.val : ℚ) * nakshatraSpan ∨
      ((j.val + 1 : ℕ) : ℚ) * nakshatraSpan ≤ (i.val : ℚ) * nakshatraSpan := by
  rcases Nat.lt_or_gt_of_ne (Fin.val_ne_of_ne h) with hij | hji
  · left
    apply mul_le_mul_of_nonneg_right
    · exact_mod_cast Nat.succ_le_of_lt hij
    · exact nakshatraSpan_nonneg
  · right
    apply mul_le_mul_of_nonneg_right
    · exact_mod_cast Nat.succ_le_of_lt hji
    · exact nakshatraSpan_nonneg

theorem pada_partition_covers (j : Fin 4) :
    ((j.val + 1 : ℕ) : ℚ) * padaSpan ≤ nakshatraSpan := by
  have hj : j.val + 1 ≤ 4 := Nat.succ_le_of_lt j.isLt
  have hle : ((j.val + 1 : ℕ) : ℚ) ≤ 4 := by exact_mod_cast hj
  calc ((j.val + 1 : ℕ) : ℚ) * padaSpan
      ≤ (4 : ℚ) * padaSpan := mul_le_mul_of_nonneg_right hle padaSpan_nonneg
    _ = nakshatraSpan := pada_cover

end Kundali
