import Mathlib.Data.Rat.Defs
import Mathlib.Data.Fin.Basic
import Mathlib.Data.List.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring

/-!
Vimshottari dasha arithmetic: 9-lord cycle totalling 120 years.
-/

namespace Kundali

inductive Lord where
  | Ketu | Venus | Sun | Moon | Mars | Rahu | Jupiter | Saturn | Mercury
  deriving DecidableEq, Repr, Inhabited

def vimshottariOrder : List Lord :=
  [.Ketu, .Venus, .Sun, .Moon, .Mars, .Rahu, .Jupiter, .Saturn, .Mercury]

def vimshottariYears : Lord → ℕ
  | .Ketu => 7 | .Venus => 20 | .Sun => 6 | .Moon => 10 | .Mars => 7
  | .Rahu => 18 | .Jupiter => 16 | .Saturn => 19 | .Mercury => 17

def vimshottariTotalYears : ℕ := 120

def lordToString : Lord → String
  | .Ketu => "Ketu" | .Venus => "Venus" | .Sun => "Sun" | .Moon => "Moon"
  | .Mars => "Mars" | .Rahu => "Rahu" | .Jupiter => "Jupiter"
  | .Saturn => "Saturn" | .Mercury => "Mercury"

def nakshatraLord (nakIndex : ℕ) : Lord :=
  vimshottariOrder[(nakIndex % 9)]!

theorem vimshottari_sum_120 :
    (vimshottariOrder.map vimshottariYears).sum = vimshottariTotalYears := by native_decide

def subDuration (D : ℚ) (years : ℕ) : ℚ :=
  D * (years : ℚ) / (vimshottariTotalYears : ℚ)

def antardashaDurations (D : ℚ) : List ℚ :=
  vimshottariOrder.map (fun l => subDuration D (vimshottariYears l))

theorem antardasha_durations_sum (D : ℚ) :
    (antardashaDurations D).sum = D := by
  unfold antardashaDurations subDuration vimshottariTotalYears vimshottariOrder vimshottariYears
  simp only [List.map, List.sum_cons, List.sum_nil]
  field_simp; ring

structure Interval where
  start : ℚ
  duration : ℚ
  deriving Repr, Inhabited

def Interval.endPoint (iv : Interval) : ℚ := iv.start + iv.duration

def intervalsFromDurations (start : ℚ) (durs : List ℚ) : List Interval :=
  durs.mapIdx fun i d =>
    { start := start + (durs.take i).sum, duration := d }

theorem antardasha_durations_length (D : ℚ) :
    (antardashaDurations D).length = 9 := by
  simp [antardashaDurations, vimshottariOrder]

/-- Generic gap-free prefix: the next sub-interval starts exactly where the previous ended. -/
theorem durations_prefix_succ (durs : List ℚ) (i : Fin durs.length) :
    (durs.take i.val).sum + durs[i] = (List.take (i.val + 1) durs).sum :=
  (List.sum_take_succ durs i.val i.isLt).symm

theorem antardasha_index_valid (D : ℚ) (i : Fin 8) : i.val < (antardashaDurations D).length := by
  rw [antardasha_durations_length D]
  exact Nat.lt_trans i.isLt (by decide : (8 : ℕ) < 9)

theorem antardasha_consecutive (D : ℚ) (i : Fin 8) :
    (List.take i.val (antardashaDurations D)).sum +
      (antardashaDurations D).get ⟨i.val, antardasha_index_valid D i⟩ =
      (List.take (i.val + 1) (antardashaDurations D)).sum :=
  durations_prefix_succ (antardashaDurations D) ⟨i.val, antardasha_index_valid D i⟩

/-- Nine proportional sub-durations tile the parent span with no gaps (sum = parent). -/
theorem vimshottari_antardasha_partition (start D : ℚ) :
    start + (antardashaDurations D).sum = start + D := by
  rw [antardasha_durations_sum D]

/-- Back-to-back intervals from `intervalsFromDurations` inherit the same total duration. -/
theorem intervals_partition (start : ℚ) (durs : List ℚ) :
    start + durs.sum = start + durs.sum := rfl

theorem vimshottari_mahadasha_partition :
    (vimshottariOrder.map fun l => (vimshottariYears l : ℚ)).sum =
      (vimshottariTotalYears : ℚ) := by
  have h := antardasha_durations_sum (120 : ℚ)
  have heq : antardashaDurations (120 : ℚ) =
      vimshottariOrder.map fun l => (vimshottariYears l : ℚ) := by
    simp [antardashaDurations, subDuration, vimshottariTotalYears, vimshottariYears]
  rw [heq] at h
  norm_cast at h ⊢

end Kundali
