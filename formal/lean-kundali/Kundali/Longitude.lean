import Mathlib.Data.Rat.Floor
import Mathlib.Algebra.Order.Floor.Ring
import Mathlib.Tactic.Linarith

/-!
Longitude normalization on `[0, 360)` using exact rationals (`ℚ`).
-/

namespace Kundali

def fullCircle : ℚ := 360

noncomputable def normalize (x : ℚ) : ℚ :=
  x - ⌊x / fullCircle⌋ * fullCircle

theorem fullCircle_pos : 0 < fullCircle := by unfold fullCircle; norm_num

theorem normalize_range (x : ℚ) : 0 ≤ normalize x ∧ normalize x < fullCircle := by
  dsimp [normalize, fullCircle]
  constructor
  · exact Int.sub_floor_div_mul_nonneg x (by norm_num)
  · exact Int.sub_floor_div_mul_lt x (by norm_num)

theorem normalize_idempotent (x : ℚ) : normalize (normalize x) = normalize x := by
  have hr := normalize_range x
  have hpos := fullCircle_pos
  have hdiv0 : 0 ≤ normalize x / fullCircle :=
    div_nonneg hr.1 (le_of_lt hpos)
  have hdiv1 : normalize x / fullCircle < 1 := by
    rw [div_lt_one hpos]
    exact hr.2
  calc normalize (normalize x)
      = normalize x - ⌊normalize x / fullCircle⌋ * fullCircle := rfl
    _ = normalize x - 0 * fullCircle := by
        rw [Int.floor_eq_zero_iff.2 ⟨hdiv0, hdiv1⟩]
        norm_cast
    _ = normalize x := by simp

end Kundali
